"""パスの分類と、保護パス・req の状態による拒否の判定。"""

import os
import re
from pathlib import Path

PROTECTED = (".claude", "CLAUDE.md", ".github", "specs/README.md", "specs/_catalog")
UNLOCK = ".claude/UNLOCK"
SWITCH = (
    ".claude/ALLOW_TEST_CHANGE"  # 人間だけが置ける。既存のテストの変更を、1回だけ通す
)


ACTIVE = {"planned", "red", "green"}
WRITE_TOOLS = {
    "Edit": "file_path",
    "Write": "file_path",
    "NotebookEdit": "notebook_path",
}


def status_by_dir(root: Path) -> dict[str, str]:
    """req のディレクトリ名（`0001-a`）→ status。"""
    result = {}
    for p in sorted((root / "specs").glob("[0-9][0-9][0-9][0-9]-*/status.md")):
        for line in p.read_text(encoding="utf-8").splitlines()[:30]:
            m = re.match(r"status:\s*([a-z]+)", line)
            if m:
                result[p.parent.name] = m.group(1)
                break
    return result


def statuses(root: Path) -> list[str]:
    return list(status_by_dir(root).values())


def rel_path(path: str, root: Path) -> str | None:
    """プロジェクト内の相対パス（posix）。プロジェクトの外なら None。"""
    full = os.path.normpath(os.path.join(root, path))
    try:
        return Path(full).relative_to(root).as_posix()
    except ValueError:
        return None


def kind_of(rel: str) -> str | None:
    if rel == SWITCH:
        return "switch"
    for p in PROTECTED:
        if rel == p or rel.startswith(p + "/"):
            return "protected"
    for name in ("tests", "src"):
        if rel == name or rel.startswith(name + "/"):
            return name
    return None


def deny_reason(kind: str, root: Path) -> str | None:
    """拒否する理由。通してよければ None。"""
    if kind == "switch":
        return (
            "既存のテストの変更を承認するスイッチ（.claude/ALLOW_TEST_CHANGE）は、人間だけが置けます。"
            "AI が作る・触る・消すことは、UNLOCK があっても拒否します。"
            "承認する場合は、人間が `! touch .claude/ALLOW_TEST_CHANGE` を実行します（1回使うと消えます）。"
        )
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


def active_req_dirs(root: Path) -> set[str]:
    """実装中（planned / red / green）の req のディレクトリ名。"""
    return {d for d, s in status_by_dir(root).items() if s in ACTIVE}
