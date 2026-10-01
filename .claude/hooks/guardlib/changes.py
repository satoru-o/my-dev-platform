"""Edit・Write が、既存のテスト・pytest の設定・req.md の AC を、黙って変えないか。スイッチの扱い。"""

from pathlib import Path

from guardlib.gitbase import GitError, head_content
from guardlib.paths import SWITCH, active_req_dirs
from guardlib.pyrules import (
    PYTEST_CONFIG_FILES,
    conftest_config_reason,
    pytest_config_reason,
    python_change_reason,
)
from guardlib.reqrules import _REQ_RE, req_change_reason

CHANGE_HINT = (
    "足すのは自由です。承認する場合は、人間が `! touch .claude/ALLOW_TEST_CHANGE` を実行します"
    "（1回使うと消えます。承認した変更は、すぐコミットしてください）。"
)


def _is_test_py(rel: str) -> bool:
    return (rel.startswith("tests/") and rel.endswith(".py")) or rel == "conftest.py"


def _new_content(tool_name: str, tool_input: dict, path: Path) -> str | None:
    """Edit・Write が成功したときの、ファイルの内容。内容の情報が無ければ None。"""
    if tool_name == "Write":
        content = tool_input.get("content")
        return content if isinstance(content, str) else None
    old, new = tool_input.get("old_string"), tool_input.get("new_string")
    if not isinstance(old, str) or not isinstance(new, str) or not old:
        return None
    try:
        with path.open(
            encoding="utf-8", newline=""
        ) as f:  # 改行（CRLF など）を、そのまま読む
            current = f.read()
    except (OSError, UnicodeDecodeError):
        return None
    if old not in current:
        return None  # Edit 自体が失敗する
    return (
        current.replace(old, new)
        if tool_input.get("replace_all")
        else current.replace(old, new, 1)
    )


def _guarded_kind(rel: str, root: Path) -> str | None:
    if _is_test_py(rel) or rel.endswith("/conftest.py"):
        return "test"
    if rel in PYTEST_CONFIG_FILES:
        return "pytest_config"
    m = _REQ_RE.fullmatch(rel)
    if m and m.group(1) in active_req_dirs(root):
        return "req"
    return None


def change_reason(
    tool_name: str, tool_input: dict, root: Path, rel: str, timeout: float
) -> str | None:
    """Edit・Write が、既存のテスト・pytest の設定・req.md の AC を、黙って変えるものなら、拒否する理由。"""
    kind = _guarded_kind(rel, root)
    if kind is None:
        return None
    new_src = _new_content(tool_name, tool_input, root / rel)
    if new_src is None:
        return None
    try:
        base_src = head_content(root, rel, timeout)
    except GitError as e:
        return (
            f"「既存」の基準（HEAD）が取れないため、拒否しました（{e}）。{CHANGE_HINT}"
        )
    if kind == "test":
        why = python_change_reason(base_src, new_src)
        if why is None and rel.endswith("conftest.py"):
            why = conftest_config_reason(base_src, new_src)
        label = "既存のテスト"
    elif kind == "pytest_config":
        why, label = pytest_config_reason(rel, base_src, new_src), "pytest の設定"
    else:
        why, label = (
            req_change_reason(base_src, new_src),
            "実装中の req.md の受け入れ条件",
        )
    if why is None:
        return None
    return f"{label}を変える・弱める・消す変更です（{why}）。{CHANGE_HINT}"


def _use_switch(root: Path) -> bool:
    """スイッチ（人間が置く）があれば、消して True。1回で消える。消せなければ、通さない。"""
    try:
        (root / SWITCH).unlink()
    except OSError:
        return False
    return True


def _with_switch(reason: str | None, root: Path) -> str | None:
    """拒否する理由が、スイッチで通せるもの（既存のテストの変更）なら、スイッチを使って通す。"""
    if reason and _use_switch(root):
        return None
    return reason
