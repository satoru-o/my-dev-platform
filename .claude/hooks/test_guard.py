"""guard.py のテスト。「止めるべきものが止まり、通すべきものが通る」ことを確かめる。"""

import json
import os
import subprocess
import sys
from pathlib import Path

import guard
import pytest

GUARD = Path(__file__).with_name("guard.py")


def make_project(
    tmp_path: Path, statuses: dict[str, str] | None = None, unlock: bool = False
) -> Path:
    for name, status in (statuses or {}).items():
        d = tmp_path / "specs" / name
        d.mkdir(parents=True)
        (d / "status.md").write_text(
            f"---\nid: 0\nstatus: {status} # comment\n---\n", encoding="utf-8"
        )
    if unlock:
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "UNLOCK").write_text("", encoding="utf-8")
    return tmp_path.resolve()


def edit(root: Path, path: str, tool: str = "Edit") -> str | None:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return guard.decide(tool, {key: path}, root)


def bash(root: Path, command: str) -> str | None:
    return guard.decide("Bash", {"command": command}, root)


# --- 保護対象 ---------------------------------------------------------------

PROTECTED_PATHS = [
    ".claude/settings.json",
    ".claude/hooks/guard.py",
    ".claude/skills/req-run/SKILL.md",
    ".claude/UNLOCK",
    "CLAUDE.md",
    ".github/workflows/ci.yml",
    "specs/README.md",
    "specs/_catalog/viewpoints.md",
]


@pytest.mark.parametrize("path", PROTECTED_PATHS)
@pytest.mark.parametrize("tool", ["Edit", "Write", "NotebookEdit"])
def test_保護対象はUNLOCKが無ければ拒否する(tmp_path, path, tool):
    root = make_project(tmp_path, {"0001-a": "green"})
    assert edit(root, str(root / path), tool) is not None


@pytest.mark.parametrize("path", PROTECTED_PATHS)
def test_保護対象はUNLOCKがあれば通す(tmp_path, path):
    root = make_project(tmp_path, unlock=True)
    assert edit(root, str(root / path)) is None


def test_UNLOCKがあってもsrcとtestsの規則は緩まない(tmp_path):
    root = make_project(tmp_path, {"0001-a": "done"}, unlock=True)
    assert edit(root, str(root / "src/a.py")) is not None
    assert edit(root, str(root / "tests/test_a.py")) is not None


def test_dotdotで保護対象に回り込んでも拒否する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green"})
    assert edit(root, str(root / "src/../CLAUDE.md")) is not None
    assert edit(root, "src/../../elsewhere/x") is None  # プロジェクトの外は対象外


def test_相対パスもプロジェクト基準で判定する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green"})
    assert edit(root, "CLAUDE.md") is not None
    assert edit(root, "docs/CHARTER.md") is None


# --- src/ -------------------------------------------------------------------


@pytest.mark.parametrize("status", ["planned", "red", "green"])
def test_srcは進行中のreqがあれば通す(tmp_path, status):
    root = make_project(tmp_path, {"0001-a": "done", "0002-b": status})
    assert edit(root, str(root / "src/cart_api/main.py")) is None


@pytest.mark.parametrize(
    "statuses", [{}, {"0001-a": "done"}, {"0001-a": "draft", "0002-b": "clarifying"}]
)
def test_srcは進行中のreqが無ければ拒否する(tmp_path, statuses):
    root = make_project(tmp_path, statuses)
    assert edit(root, str(root / "src/cart_api/main.py")) is not None


# --- tests/ -----------------------------------------------------------------


@pytest.mark.parametrize("status", ["planned", "green"])
def test_testsはplannedかgreenなら通す(tmp_path, status):
    root = make_project(tmp_path, {"0001-a": status})
    assert edit(root, str(root / "tests/test_a.py")) is None


def test_testsはredのreqがあれば拒否する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green", "0002-b": "red"})
    assert edit(root, str(root / "tests/test_a.py")) is not None


@pytest.mark.parametrize(
    "statuses", [{}, {"0001-a": "done"}, {"0001-a": "draft"}, {"0001-a": "clarifying"}]
)
def test_testsは進行中のreqが無ければ拒否する(tmp_path, statuses):
    root = make_project(tmp_path, statuses)
    assert edit(root, str(root / "tests/test_a.py")) is not None


# --- 対象外 -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "docs/CHARTER.md",
        "Makefile",
        "pyproject.toml",
        ".gitignore",
        "specs/0001-a/req.md",
        "specs/0001-a/status.md",
        "specs/0001-a/discussion-log.md",
        "specs/_templates/req.md",
        "srcx/a.py",
        "mytests/a.py",
    ],
)
def test_対象外のパスは常に通す(tmp_path, path):
    root = make_project(tmp_path, {"0001-a": "red"})
    assert edit(root, str(root / path)) is None


def test_Write系以外のツールとfile_path無しは通す(tmp_path):
    root = make_project(tmp_path)
    assert guard.decide("Read", {"file_path": str(root / "CLAUDE.md")}, root) is None
    assert guard.decide("Write", {}, root) is None


# --- Bash（ベストエフォート） ------------------------------------------------

BASH_DENIED_PROTECTED = [
    "sed -i 's/a/b/' CLAUDE.md",
    "sed -i.bak s/a/b/ specs/README.md",
    "echo hi > .claude/hooks/guard.py",
    "echo hi >> specs/_catalog/viewpoints.md",
    "cat > .claude/settings.json <<'EOF'\n{}\nEOF",
    "cd x && tee .github/workflows/ci.yml",
    "rm -rf .claude/hooks",
    "mv specs/README.md /tmp/x",
    "touch .claude/UNLOCK",
    "python3 -c \"open('CLAUDE.md','w').write('x')\"",
    "python3 - <<'EOF'\nfrom pathlib import Path\nPath('.claude/x').write_text('x')\nEOF",
]


@pytest.mark.parametrize("command", BASH_DENIED_PROTECTED)
def test_Bashの保護対象への書き込みは拒否する(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "green"})
    assert bash(root, command) is not None


def test_BashもUNLOCKがあれば通す(tmp_path):
    root = make_project(tmp_path, unlock=True)
    assert bash(root, "sed -i 's/a/b/' CLAUDE.md") is None


@pytest.mark.parametrize(
    "command",
    [
        "git add CLAUDE.md .claude && git commit -m 'docs: CLAUDE.mdを更新' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'",
        "grep -n foo CLAUDE.md",
        "cat .claude/skills/req-run/SKILL.md",
        "ls .claude/hooks && head -5 specs/README.md",
        "git diff --stat -- .claude",
        "make check",
        "uv run pytest -q tests .claude/hooks",
        "uv run ruff format tests",
        "echo hi > /tmp/x",
        "sed -i 's/a/b/' specs/0001-a/status.md",
        "git mv specs/_templates/a.md specs/_templates/b.md",
    ],
)
def test_Bashの読み取りや無関係なコマンドは通す(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "red"})
    assert bash(root, command) is None


def test_Bashのtests書き込みはredで拒否しplannedで通す(tmp_path):
    red = make_project(tmp_path / "r", {"0001-a": "red"})
    planned = make_project(tmp_path / "p", {"0001-a": "planned"})
    assert bash(red, "echo x > tests/test_a.py") is not None
    assert bash(planned, "echo x > tests/test_a.py") is None


def test_Bashのsrc書き込みは進行中のreqが無ければ拒否する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "done"})
    assert bash(root, "cat > src/cart_api/main.py <<'EOF'\nx\nEOF") is not None
    assert bash(root, "cat src/cart_api/main.py") is None


# --- 0004: heredoc と変数経由の書き込み（誤検出の修正） -----------------------------
# 退行の網: 今の実装でも通るもの。誤検出を直す途中で、拒否すべきものが通らないようにする。


def test_変数経由で保護対象を開いて書くのは拒否する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    command = "python3 - <<'EOF'\np='CLAUDE.md'\nopen(p,'w').write('x')\nEOF"
    assert bash(root, command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "bash <<'EOF'\ntouch .claude/x\nEOF",
        "cat <<'EOF' | bash\ntouch .claude/x\nEOF",
    ],
)
def test_インタプリタに渡したheredocの本文は拒否する(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, command) is not None


def test_変数経由で保護対象でない所に書くのは通す(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    command = "python3 - <<'EOF'\np='specs/a.md'\nopen(p,'w').write('x')\nEOF"
    assert bash(root, command) is None


# Red 1（AC-1）: 今回の事例。書き込み先は specs/ で、本文の文章に保護パスがあるだけ


def test_pythonのheredocで書き込み先がspecsなら本文に保護パスの文章があっても通す(
    tmp_path,
):
    root = make_project(tmp_path, {"0001-a": "planned"})
    command = (
        "python3 - <<'EOF'\n"
        "p='specs/0003/status.md'\n"
        "open(p,'w').write('see `touch .claude/x`')\n"
        "EOF"
    )
    assert bash(root, command) is None


# --- 実際のスクリプトを標準入力で動かす -----------------------------------------


def run_guard(root: Path, stdin: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    return subprocess.run(  # noqa: S603
        [sys.executable, str(GUARD)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def payload(tool: str, **tool_input: str) -> str:
    return json.dumps(
        {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
    )


def test_スクリプトは拒否するときdenyのJSONを出す(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green"})

    res = run_guard(root, payload("Write", file_path=str(root / "CLAUDE.md")))

    assert res.returncode == 0
    out = json.loads(res.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == "deny"
    assert out["permissionDecisionReason"]


def test_スクリプトは通すとき何も出さない(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green"})

    res = run_guard(root, payload("Edit", file_path=str(root / "src/a.py")))

    assert (res.returncode, res.stdout) == (0, "")


def test_スクリプトは壊れた入力を安全側で拒否する(tmp_path):
    root = make_project(tmp_path)

    res = run_guard(root, "これはJSONではない")

    assert res.returncode == 0
    assert json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
