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
import re
import sys
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


def bash_kinds(command: str) -> list[str]:
    """書き込みに見えるコマンドが触れるパスの種類（ベストエフォート）。"""
    kinds = []
    for kind, path in PATH_RE.items():
        redirect = rf">>?\s*[\"']?(?:[^\s\"';&|]*/)?{path}"
        verb = rf"{WRITE_VERB}[^;&|\n]*{path}"
        py = bool(re.search(PY_WRITE, command)) and bool(re.search(path, command))
        if re.search(redirect, command) or re.search(verb, command, re.MULTILINE) or py:
            kinds.append(kind)
    return kinds


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
        for kind in bash_kinds(str(tool_input.get("command", ""))):
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
