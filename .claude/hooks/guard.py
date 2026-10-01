#!/usr/bin/env python3
"""PreToolUse ガード。TDDの規律を機械で守る（ルールの正本は specs/README.md）。

1. 保護対象（.claude/**, CLAUDE.md, .github/**, specs/README.md, specs/_catalog/**）
   への書き込みは、`.claude/UNLOCK` が無い限り拒否する。UNLOCK は人間が手で置く
   （例: `! touch .claude/UNLOCK`）。編集が済んだら消す。
2. src/ への書き込みは、進行中のreq（status が planned / red / green）が無ければ拒否する。
3. tests/ への書き込みは、進行中のreqが無い、または status が red のものがあれば拒否する
   （red = 失敗するテストがあり、実装中。実装フェーズでは tests/ を触らない）。

Bash は、書き込みに見えるコマンドだけを見る「ベストエフォート」。完全な防御ではない。
本当の壁は CODEOWNERS / ブランチ保護（M2）で作る。
想定外の例外は、安全側（拒否）に倒す。
"""

import json
import os
import posixpath
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PROTECTED = (".claude", "CLAUDE.md", ".github", "specs/README.md", "specs/_catalog")
UNLOCK = ".claude/UNLOCK"
ACTIVE = {"planned", "red", "green"}
WRITE_TOOLS = {
    "Edit": "file_path",
    "Write": "file_path",
    "NotebookEdit": "notebook_path",
}

# Bash 用。パスを表す正規表現（コマンド文字列の中から探す）
PATH_RE = {
    "protected": r"(?:\.claude(?![\w-])|CLAUDE\.md|\.github(?![\w-])|specs/README\.md|specs/_catalog(?![\w-]))",
    "tests": r"(?<![\w.-])tests(?:/|(?![\w.-]))",
    "src": r"(?<![\w.-])src(?:/|(?![\w.-]))",
}
WRITE_VERB = (
    r"(?:^|[;&|(]\s*|\bxargs\s+|\bsudo\s+)"
    r"(?:sed\s[^;&|\n]*-\w*i|tee|mv|cp|rm|touch|truncate|ln|chmod|chown|install|rsync|dd|patch)\b"
)
PY_WRITE = (
    r"(?:write_text|write_bytes|\.write\(|open\([^)]*[\"'][wax+]"
    r"|shutil\.(?:copy|move|rmtree)|os\.(?:remove|rename|replace|unlink))"
)

# heredoc（`<<`）。here-string（`<<<`）は含めない。
HEREDOC_RE = re.compile(
    r"(?<!<)<<(?!<)(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|(\\?)([A-Za-z_][\w.-]*))"
)
PYTHON_WORD_RE = re.compile(r"(?<![\w./-])python[\d.]*(?![\w.-])")


def statuses(root: Path) -> list[str]:
    result = []
    for p in sorted((root / "specs").glob("[0-9][0-9][0-9][0-9]-*/status.md")):
        for line in p.read_text(encoding="utf-8").splitlines()[:30]:
            m = re.match(r"status:\s*([a-z]+)", line)
            if m:
                result.append(m.group(1))
                break
    return result


def rel_path(path: str, root: Path) -> str | None:
    """プロジェクト内の相対パス（posix）。プロジェクトの外なら None。"""
    full = os.path.normpath(os.path.join(root, path))
    try:
        return Path(full).relative_to(root).as_posix()
    except ValueError:
        return None


def kind_of(rel: str) -> str | None:
    for p in PROTECTED:
        if rel == p or rel.startswith(p + "/"):
            return "protected"
    for name in ("tests", "src"):
        if rel == name or rel.startswith(name + "/"):
            return name
    return None


def deny_reason(kind: str, root: Path) -> str | None:
    """拒否する理由。通してよければ None。"""
    if kind == "protected":
        if (root / UNLOCK).exists():
            return None
        return (
            "保護対象（.claude/**、CLAUDE.md、.github/**、specs/README.md、specs/_catalog/**）は"
            "人間の承認なしに編集できません。人間に提案してください。"
            "編集を承認する場合は、人間が `! touch .claude/UNLOCK` を実行し、編集後に削除します。"
        )
    sts = statuses(root)
    if kind == "src":
        if ACTIVE & set(sts):
            return None
        return (
            "進行中のreq（status が planned / red / green）がありません。"
            "src/ はreqなしに編集できません。`/req-new` で要望を起こすか、"
            "`/req-run` / `/req-fb` で進めてください。挙動が変わらない変更（chore）なら src/ には触れません。"
        )
    if kind == "tests":
        if "red" in sts:
            return (
                "status が red のreqがあります。実装フェーズでは tests/ を書き換えません"
                "（整形も含む）。テストを直す必要があれば、discussion-log.md で人間に聞いてください。"
            )
        if not ACTIVE & set(sts):
            return (
                "進行中のreq（status が planned / green）がありません。"
                "tests/ はreqなしに編集できません。`/req-new` / `/req-run` / `/req-fb` で進めてください。"
            )
    return None


# --- Bash: heredoc の解析 -----------------------------------------------------


@dataclass
class Heredoc:
    """heredoc 1つ分。body は本文（終了行は含まない）。"""

    receiver: str  # `<<` を含む1行。受け取るコマンドの判定に使う
    body: str


def split_heredocs(command: str) -> tuple[str, list[Heredoc]]:
    """コマンドを、本文を除いたシェルの文と、heredoc の一覧に分ける。

    終了行は、`<<` なら行全体が区切り語と等しいとき、`<<-` なら行頭のタブを除いて等しいとき。
    空白つきの `EOF` などは終了行にならない（シェルの規則どおり）。閉じていなければ末尾まで本文。
    """
    lines = command.split("\n")
    shell: list[str] = []
    docs: list[Heredoc] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        shell.append(line)
        i += 1
        for m in HEREDOC_RE.finditer(line):
            dash = bool(m.group(1))
            delim = m.group(2) or m.group(3) or m.group(5)
            body: list[str] = []
            while i < len(lines):
                cur = lines[i]
                i += 1
                if (cur.lstrip("\t") if dash else cur) == delim:
                    break
                body.append(cur)
            docs.append(Heredoc(receiver=line, body="\n".join(body)))
    return "\n".join(shell), docs


# --- Bash: python の書き込み先の判定 -------------------------------------------

_STR = r"""(?:'([^'\n]*)'|"([^"\n]*)")"""
_ARG = rf"""\s*(?:{_STR}|([A-Za-z_]\w*))"""
_ASSIGN_RE = re.compile(rf"""\b([A-Za-z_]\w*)\s*=\s*(?:Path\(\s*)?{_STR}""")
_OPEN_RE = re.compile(
    rf"""\bopen\({_ARG}\s*(?:,\s*(?:mode\s*=\s*)?['"]([^'"\n]*)['"])?"""
)
_PATH_WRITE_RE = re.compile(
    rf"""\bPath\({_ARG}\s*\)\s*\.\s*(?:write_text|write_bytes)\b"""
)
_VAR_WRITE_RE = re.compile(r"""\b([A-Za-z_]\w*)\s*\.\s*(?:write_text|write_bytes)\b""")
_FUNC_RE = re.compile(
    rf"""\b(?:shutil\.(?:copy|copy2|copyfile|move|rmtree)|os\.(?:remove|rename|replace|unlink))\({_ARG}(?:\s*,{_ARG})?"""
)


def _path_kind(path: str, root: Path) -> str | None:
    if posixpath.isabs(path):
        rel = rel_path(path, root)
    else:
        rel = rel_path(path, root)
    return kind_of(rel) if rel is not None else None


def python_kinds(code: str, root: Path) -> set[str]:
    """python のコードが書き込む（と判断できる）パスの種類。

    書き込み先は、文字列リテラルか、リテラルを代入した変数から読む。
    代入が見えない変数（`p=sys.argv[1]` など）は、判断できないので通す（ベストエフォート）。
    """
    assigns: dict[str, str] = {}
    for m in _ASSIGN_RE.finditer(code):
        assigns[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)

    def resolve(single: str | None, double: str | None, ident: str | None):
        if single is not None:
            return single
        if double is not None:
            return double
        return assigns.get(ident or "")

    targets: list[str | None] = []
    for m in _OPEN_RE.finditer(code):
        mode = m.group(4)
        if mode and set(mode) & set("wax+"):
            targets.append(resolve(m.group(1), m.group(2), m.group(3)))
    for m in _PATH_WRITE_RE.finditer(code):
        targets.append(resolve(m.group(1), m.group(2), m.group(3)))
    for m in _VAR_WRITE_RE.finditer(code):
        targets.append(assigns.get(m.group(1)))
    for m in _FUNC_RE.finditer(code):
        targets.append(resolve(m.group(1), m.group(2), m.group(3)))
        targets.append(resolve(m.group(4), m.group(5), m.group(6)))

    kinds: set[str] = set()
    for t in targets:
        if t:
            kind = _path_kind(t, root)
            if kind:
                kinds.add(kind)
    return kinds


# --- Bash: 判定 -------------------------------------------------------------------


def _legacy_kinds(text: str) -> list[str]:
    """書き込みに見えるシェルのコマンドが触れるパスの種類（ベストエフォート）。"""
    kinds = []
    for kind, path in PATH_RE.items():
        redirect = rf">>?\s*[\"']?(?:[^\s\"';&|]*/)?{path}"
        verb = rf"{WRITE_VERB}[^;&|\n]*{path}"
        py = bool(re.search(PY_WRITE, text)) and bool(re.search(path, text))
        if re.search(redirect, text) or re.search(verb, text, re.MULTILINE) or py:
            kinds.append(kind)
    return kinds


def bash_kinds(command: str, root: Path) -> list[str]:
    """書き込みに見えるコマンドが触れるパスの種類（ベストエフォート）。"""
    shell, docs = split_heredocs(command)
    kinds: set[str] = set()
    for d in docs:
        if PYTHON_WORD_RE.search(d.receiver):
            kinds |= python_kinds(d.body, root)  # python の本文は、書き込み先で判定する
        else:
            shell += "\n" + d.body  # 今までどおり、本文も調べる
    kinds |= set(_legacy_kinds(shell))
    return [k for k in PATH_RE if k in kinds]


def decide(tool_name: str, tool_input: dict, root: Path) -> str | None:
    """拒否する理由。通してよければ None。"""
    if tool_name in WRITE_TOOLS:
        path = tool_input.get(WRITE_TOOLS[tool_name])
        if not path:
            return None
        rel = rel_path(str(path), root)
        kind = kind_of(rel) if rel is not None else None
        return deny_reason(kind, root) if kind else None
    if tool_name == "Bash":
        for kind in bash_kinds(str(tool_input.get("command", "")), root):
            reason = deny_reason(kind, root)
            if reason:
                return reason
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        )
        reason = decide(
            payload.get("tool_name", ""),
            payload.get("tool_input") or {},
            root.resolve(),
        )
    except Exception as e:  # 安全側（拒否）に倒す
        reason = f"ガードの内部エラーのため拒否しました: {type(e).__name__}: {e}"
    if reason:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
