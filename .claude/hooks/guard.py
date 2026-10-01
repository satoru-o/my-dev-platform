#!/usr/bin/env python3
"""PreToolUse ガード。TDDの規律を機械で守る（ルールの正本は specs/README.md）。

1. 保護対象（.claude/**, CLAUDE.md, .github/**, specs/README.md, specs/_catalog/**）
   への書き込みは、`.claude/UNLOCK` が無い限り拒否する。UNLOCK は人間が手で置く
   （例: `! touch .claude/UNLOCK`）。編集が済んだら消す。
2. src/ への書き込みは、進行中のreq（status が planned / red / green）が無ければ拒否する。
3. tests/ への書き込みは、進行中のreqが無い、または status が red のものがあれば拒否する
   （red = 失敗するテストがあり、実装中。実装フェーズでは tests/ を触らない）。

Bash は、書き込みに見えるコマンドだけを見る「ベストエフォート」。完全な防御ではない。
  - heredoc: 受け取るのがデータだけ（cat、tee など）なら、本文は調べない（引用符なしなら、展開される
    `$(…)` とバッククォートだけ調べる。解析しきれないものは拒否）。bash や python など、実行するもの
    （知らないコマンドも含む）なら、本文を調べる。here-string（`<<<`）も同じ。
  - python: 書き込み先は、文字列リテラルか、リテラルを代入した変数から読む。代入が見えない変数は通す。
  - 巨大な入力で遅くならないこと（hook のタイムアウトは10秒。超えると素通りになる）が前提。
    入力量の2乗に比例する処理を入れない（test_guard.py の SLOW_CASES で確かめる）。
本当の壁は CODEOWNERS / ブランチ保護（M2）で作る。
想定外の例外は、安全側（拒否）に倒す。
"""

import bisect
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

# heredoc（`<<`）。here-string（`<<<`）は含めない。
HEREDOC_RE = re.compile(
    r"(?<!<)<<(?!<)(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|(\\?)([A-Za-z_][\w.-]*))"
)
HERESTRING_RE = re.compile(r"<<<[ \t]*(?:\"([^\"\n]*)\"|'([^'\n]*)'|([^\s;&|<>]*))")
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
    line_no: int  # receiver が、コマンドの何行目か
    seg: tuple[
        int, int
    ]  # receiver のうち、`<<` を含むコマンド列の範囲（`;` `&&` `||` `&` の区切りの間）
    quoted: bool  # 区切り語が引用符（`'EOF'`、`"EOF"`、`\EOF`）つき。本文は展開されない
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
        line_no = i
        shell.append(line)
        i += 1
        matches = list(HEREDOC_RE.finditer(line))
        bounds = _separator_bounds(line) if matches else ([], [])
        for m in matches:
            dash = bool(m.group(1))
            delim = m.group(2) or m.group(3) or m.group(5)
            body: list[str] = []
            while i < len(lines):
                cur = lines[i]
                i += 1
                if (cur.lstrip("\t") if dash else cur) == delim:
                    break
                body.append(cur)
            quoted = (
                m.group(2) is not None or m.group(3) is not None or bool(m.group(4))
            )
            docs.append(
                Heredoc(
                    receiver=line,
                    line_no=line_no,
                    seg=_segment_bounds(bounds, len(line), m.start()),
                    quoted=quoted,
                    body="\n".join(body),
                )
            )
    return "\n".join(shell), docs


# データとして受け取るだけのコマンド。これ以外（bash、python、不明なもの）は、本文を実行するものとして扱う。
DATA_RECEIVERS = {"cat", "tee", "head", "tail", "wc", "sort", "uniq", "grep", "diff"}
DATA_GIT_SUBCOMMANDS = {"commit", "tag"}  # `git commit -F -` のメッセージなど
_SEP_RE = re.compile(r";|&&|\|\||&")
_WRAPPERS = {"sudo", "env", "exec", "time", "nohup", "command", "builtin"}


def _separator_bounds(line: str) -> tuple[list[int], list[int]]:
    """区切り（`;` `&&` `||` `&`）の、始まりの位置の一覧と、終わりの位置の一覧。"""
    spans = [m.span() for m in _SEP_RE.finditer(line)]
    return [s for s, _ in spans], [e for _, e in spans]


def _segment_bounds(
    bounds: tuple[list[int], list[int]], length: int, pos: int
) -> tuple[int, int]:
    """pos を含む1つのコマンド列の範囲。1行に `<<` が大量にあっても、遅くならないよう二分探索する。"""
    starts, ends = bounds
    i = bisect.bisect_right(ends, pos)
    j = bisect.bisect_left(starts, pos)
    return (ends[i - 1] if i else 0), (starts[j] if j < len(starts) else length)


def _is_data_command(command: str) -> bool:
    words = command.split()
    while words and (re.fullmatch(r"\w+=\S*", words[0]) or words[0] in _WRAPPERS):
        words.pop(0)
    if not words:
        return False
    name = posixpath.basename(words[0])
    if name == "git":
        rest = [w for w in words[1:] if not w.startswith("-")]
        return bool(rest) and rest[0] in DATA_GIT_SUBCOMMANDS
    return name in DATA_RECEIVERS


def segment_is_data_only(segment: str) -> bool:
    """heredoc の本文が、実行されず、データとして書かれるだけか（`<<` を含むコマンド列で判定する）。

    パイプでつながったすべてのコマンドが、データを受けるだけのものであること。
    判定できなければ（知らないコマンドがあれば）、実行されるものとして扱う（安全側）。
    """
    return all(_is_data_command(c) for c in segment.split("|"))


MAX_SUBSTITUTION_DEPTH = 10


def expansions(body: str) -> tuple[list[str], bool]:
    """引用符なしの heredoc の本文のうち、展開されて実行される部分（`$(…)` とバッククォート）。

    戻り値は、その中身の一覧と、解析しきれたかどうか。閉じていない、入れ子が深すぎるものは、
    解析しきれなかったものとして扱う（呼び出し側が、拒否側に倒す）。
    """
    units: list[str] = []
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == "\\":
            i += 2
        elif body.startswith("$(", i):
            arithmetic = body.startswith("$((", i)
            depth, j = 1, i + 2
            while j < n and depth > 0:
                ch = body[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "(":
                    depth += 1
                    if depth > MAX_SUBSTITUTION_DEPTH:
                        return units, False
                elif ch == ")":
                    depth -= 1
                j += 1
            if depth != 0:
                return units, False
            if not arithmetic:
                units.append(body[i + 2 : j - 1])
            i = j
        elif c == "`":
            j = i + 1
            while j < n and body[j] != "`":
                j += 2 if body[j] == "\\" else 1
            if j >= n:
                return units, False
            units.append(body[i + 1 : j])
            i = j + 1
        else:
            i += 1
    return units, True


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
        # `>` を語に含めない（`>>>>…` のような入力で、各 `>` から末尾まで読んで、遅くならないように）
        redirect = rf">>?\s*[\"']?(?:[^\s\"';&|>]*/)?{path}"
        verb = rf"{WRITE_VERB}[^;&|\n]*{path}"
        if re.search(redirect, text) or re.search(verb, text, re.MULTILINE):
            kinds.append(kind)
    return kinds


def bash_kinds(command: str, root: Path) -> list[str]:
    """書き込みに見えるコマンドが触れるパスの種類（ベストエフォート）。"""
    shell, docs = split_heredocs(command)
    shell_parts = [shell]
    kinds: set[str] = set()
    # 受け取るコマンドの判定は、1行に `<<` が大量にあっても、同じコマンド列につき1回だけ行う
    receivers: dict[tuple, tuple[bool, bool]] = {}

    def receiver(key: tuple, line: str, seg: tuple[int, int]) -> tuple[bool, bool]:
        """（python か、データを受けるだけか）"""
        if key not in receivers:
            segment = line[seg[0] : seg[1]]
            receivers[key] = (
                bool(PYTHON_WORD_RE.search(segment)),
                segment_is_data_only(segment),
            )
        return receivers[key]

    for d in docs:
        is_python, data_only = receiver(("doc", d.line_no, d.seg), d.receiver, d.seg)
        if is_python:
            # python の本文は、書き込み先で判定する
            kinds |= python_kinds(d.body, root)
        elif not data_only:
            # 実行されうる本文は、シェルのコマンドとして調べる
            shell_parts.append(d.body)
        elif not d.quoted:
            # データでも、引用符なしなら、展開される部分は実行される
            units, parsed = expansions(d.body)
            for unit in units:
                kinds |= set(_legacy_kinds(unit))
            if not parsed:
                # 解析しきれないものは、拒否側に倒す
                kinds.add("protected")
    shell = "\n".join(shell_parts)

    # here-string（`<<<`）も、受け取るのがデータだけでなければ、中身が実行される
    for line_no, line in enumerate(shell.split("\n")):
        if "<<<" not in line:
            continue
        bounds = _separator_bounds(line)
        for m in HERESTRING_RE.finditer(line):
            seg = _segment_bounds(bounds, len(line), m.start())
            is_python, data_only = receiver(("hs", line_no, seg), line, seg)
            if data_only:
                continue
            content = next(g for g in m.groups() if g is not None)
            if is_python or PYTHON_WORD_RE.search(content):
                kinds |= python_kinds(content, root)
            kinds |= set(_legacy_kinds(content))

    if PYTHON_WORD_RE.search(shell):
        # `python3 -c "…"` など。書き込み先で判定する
        kinds |= python_kinds(shell, root)
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
