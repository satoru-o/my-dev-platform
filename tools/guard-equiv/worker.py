# ruff: noqa: E501, S603, S607
"""同じ入力の一覧を、guard（旧・新）の decide に通して、判定（理由まで）を JSON に書く（1つの guard 用）。

使い方: python3 worker.py <guard.py のあるディレクトリ> <出力.json>
普通は、run.py から呼ぶ。入力は、乱数や時刻を使わず、毎回同じ。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True


guard = None  # 実行時に、引数のディレクトリから読み込む（下の __main__）


def _load_guard_from(directory: str):
    sys.path.insert(0, directory)
    import guard as module

    return module


TEST = "from m import add\n\n\ndef test_a():\n    assert add(2, 3) == 5\n\n\ndef test_b():\n    assert add(0, 0) == 0\n"
REQ = "# 0001 x\n\n## 受け入れ条件\n\n### AC-1 足す\n\n| 入力 | 期待 |\n| --- | --- |\n| 2, 3 | 5 |\n| 0, 0 | 0 |\n"
BASE = {
    "tests/test_a.py": TEST,
    "tests/conftest.py": "import pytest\n",
    "src/m.py": "def add(a, b):\n    return a + b\n",
    "pyproject.toml": '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
    "Makefile": "test:\n\tpytest tests\n",
    "CLAUDE.md": "# x\n",
    "specs/README.md": "# r\n",
    "specs/_catalog/v.md": "# v\n",
    ".claude/settings.json": "{}\n",
    ".github/workflows/c.yml": "name: c\n",
    "docs/a.md": "# a\n",
}
BIG = "def test_big_0():\n    assert 1 == 1\n" * 1
GIT_ENV = {"PATH": "/usr/bin:/bin", "HOME": tempfile.gettempdir()}


def make_root(status: str | None, commit: bool = True) -> Path:
    root = Path(tempfile.mkdtemp(prefix="equiv_")).resolve()
    files = dict(BASE)
    if status:
        files["specs/0001-x/status.md"] = f"---\nid: 1\nstatus: {status}\n---\n"
        files["specs/0001-x/req.md"] = REQ
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode())
    if commit:
        for args in (
            ["init", "-q"],
            ["config", "user.email", "t@e"],
            ["config", "user.name", "t"],
            ["add", "-A"],
            ["commit", "-q", "-m", "b"],
        ):
            subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                env=GIT_ENV,
                capture_output=True,
            )  # noqa: S603, S607
    return root


def edit(rel, old, new, **kw):
    return lambda root: (
        "Edit",
        {"file_path": str(root / rel), "old_string": old, "new_string": new, **kw},
    )


def write(rel, content):
    return lambda root: ("Write", {"file_path": str(root / rel), "content": content})


def bash(cmd):
    return lambda root: ("Bash", {"command": cmd.replace("<R>", str(root))})


T = "tests/test_a.py"
EDITS = {
    "edit_add_test": edit(
        T,
        "    assert add(0, 0) == 0\n",
        "    assert add(0, 0) == 0\n\n\ndef test_c():\n    assert add(1, 1) == 2\n",
    ),
    "edit_change_expect": edit(T, "== 5", "== 6"),
    "edit_rename_var": edit(
        T, "    assert add(2, 3) == 5\n", "    r = add(2, 3)\n    assert r == 5\n"
    ),
    "edit_delete_test": edit(T, "\n\ndef test_b():\n    assert add(0, 0) == 0\n", ""),
    "edit_skip": edit(T, "def test_b():", "@pytest.mark.skip\ndef test_b():"),
    "edit_import": edit(T, "from m import add\n", "from m import add, sub\n"),
    "edit_dup_name": edit(
        T,
        "    assert add(0, 0) == 0\n",
        "    assert add(0, 0) == 0\n\n\ndef test_a():\n    assert True\n",
    ),
    "edit_syntax_error": edit(T, "def test_b():", "def test_b(:"),
    "edit_replace_all": edit(T, "add", "plus", replace_all=True),
    "edit_nonexistent_old": edit(T, "ZZZ", "YYY"),
    "write_new_test": write("tests/test_new.py", "def test_x():\n    assert 1\n"),
    "write_overwrite_test": write(T, "def test_a():\n    assert True\n"),
    "write_conftest_ignore": write(
        "tests/conftest.py", 'import pytest\ncollect_ignore = ["x"]\n'
    ),
    "write_pyproject_same": write(
        "pyproject.toml", '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n# c\n'
    ),
    "write_pyproject_addopts": write(
        "pyproject.toml",
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\naddopts = "-k x"\n',
    ),
    "write_pyproject_broken": write("pyproject.toml", "[tool.pytest\n"),
    "write_pyproject_tool_scalar": write("pyproject.toml", "tool = 1\n"),
    "write_test_null_byte": write(T, "def test_a():\n    assert 1\x00\n"),
    "write_test_deep_nesting": write(T, "x = " + "(" * 5000 + ")" * 5000 + "\n"),
    "write_conftest_broken": write("tests/conftest.py", "def (:\n"),
    "write_pytest_ini_new": write("pytest.ini", "[pytest]\naddopts = -k x\n"),
    "edit_src": edit("src/m.py", "a + b", "a - b"),
    "edit_req_row": edit("specs/0001-x/req.md", "| 2, 3 | 5 |", "| 2, 3 | 6 |"),
    "edit_req_add_row": edit(
        "specs/0001-x/req.md", "| 0, 0 | 0 |\n", "| 0, 0 | 0 |\n| 1, 1 | 2 |\n"
    ),
    "edit_claude_md": edit("CLAUDE.md", "# x", "# y"),
    "edit_readme": edit("specs/README.md", "# r", "# s"),
    "edit_catalog": edit("specs/_catalog/v.md", "# v", "# w"),
    "edit_settings": edit(".claude/settings.json", "{}", '{"a":1}'),
    "edit_workflow": edit(".github/workflows/c.yml", "c", "d"),
    "edit_switch": write(".claude/ALLOW_TEST_CHANGE", ""),
    "edit_unlock": write(".claude/UNLOCK", ""),
    "edit_docs": edit("docs/a.md", "# a", "# b"),
    "edit_outside": lambda root: (
        "Edit",
        {"file_path": "/etc/hostname", "old_string": "a", "new_string": "b"},
    ),
    "edit_no_path": lambda root: ("Edit", {}),
    "edit_makefile": edit("Makefile", "pytest tests", "pytest"),
    "notebook": lambda root: (
        "NotebookEdit",
        {"notebook_path": str(root / "tests/n.ipynb")},
    ),
    "read_tool": lambda root: ("Read", {"file_path": str(root / T)}),
}
CMDS = [
    "ls",
    "echo hi > tests/test_a.py",
    "echo hi >> tests/test_a.py",
    "echo hi > tests/test_new_file.py",
    "sed -i 's/5/6/' tests/test_a.py",
    "sed -i 's/a/b/' src/m.py",
    "tee tests/test_a.py < /dev/null",
    "tee tests/test_new2.py < /dev/null",
    "rm tests/test_a.py",
    "rm -rf tests",
    "mv tests/test_a.py /tmp/x",
    "cp /tmp/x tests/test_a.py",
    "touch tests/test_t.py",
    "echo hi > src/new.py",
    "echo hi > CLAUDE.md",
    "echo hi > .claude/x",
    "echo hi > .github/x",
    "echo hi > specs/README.md",
    "echo hi > docs/a.md",
    "echo hi > .claude/ALLOW_TEST_CHANGE",
    "touch .claude/ALLOW_TEST_CHANGE",
    "rm .claude/ALLOW_TEST_CHANGE",
    "echo x > pyproject.toml",
    "echo x > tests/conftest.py",
    "echo x > specs/0001-x/req.md",
    "echo x > Makefile",
    "cd tests && echo x > test_a.py",
    "cd tests; sed -i s/a/b/ test_a.py",
    "echo x > tests/*",
    "echo x > $F",
    "echo x > tests/$NAME.py",
    "cat <<EOF > tests/test_a.py\nx\nEOF",
    "cat <<'EOF' > tests/test_new3.py\nx\nEOF",
    "cat <<EOF\n$(echo hi > tests/test_a.py)\nEOF",
    "cat <<EOF\n`sed -i s/a/b/ tests/test_a.py`\nEOF",
    "cat <<'EOF'\n$(echo hi > tests/test_a.py)\nEOF",
    "cat <<EOF\n$(unterminated\nEOF",
    "bash <<EOF\necho hi > tests/test_a.py\nEOF",
    "bash <<'EOF'\necho hi > tests/test_a.py\nEOF",
    "python3 <<EOF\nopen('tests/test_a.py','w').write('x')\nEOF",
    "python3 <<'EOF'\nfrom pathlib import Path\nPath('tests/test_a.py').write_text('x')\nEOF",
    "python3 <<'EOF'\np='tests/test_a.py'\nopen(p,'w').write('x')\nEOF",
    "python3 <<'EOF'\nimport sys\nopen(sys.argv[1],'w').write('x')\nEOF",
    "python3 <<'EOF'\nimport os\nos.remove('tests/test_a.py')\nEOF",
    "python3 <<'EOF'\nimport shutil\nshutil.copy('a','src/m.py')\nEOF",
    "python3 <<'EOF'\nopen('.claude/x','w').write('x')\nEOF",
    "python3 <<'EOF'\nopen('docs/x','w').write('x')\nEOF",
    "python3 -c \"open('tests/test_a.py','w').write('x')\"",
    'python3 -c "print(1)"',
    "python3 <<< \"open('tests/test_a.py','w').write('x')\"",
    "cat <<< \"open('tests/test_a.py','w').write('x')\"",
    "grep x <<< 'echo > tests/a'",
    "ruby -e \"File.write('tests/test_a.py','x')\"",
    "node -e \"require('fs').writeFileSync('tests/test_a.py','x')\"",
    "perl -e 'open(F,\">tests/a\")'",
    "echo ok && echo hi > tests/test_a.py",
    "xargs rm < list; echo tests",
    "sudo tee tests/test_a.py",
    "git status",
    "git log --oneline",
    "git commit -m x",
    "git commit --amend -m x",
    "git commit --amend=x",
    "git rebase main",
    "git reset --hard",
    "git reset --hard HEAD~1",
    "git reset HEAD~1",
    "git reset HEAD tests/test_a.py",
    "git reset --soft HEAD",
    "git checkout -- tests/test_a.py",
    "git checkout tests/test_a.py",
    "git checkout -b newbranch",
    "git checkout main",
    "git checkout HEAD -- .",
    "git checkout HEAD src/m.py",
    "git restore tests/test_a.py",
    "git restore --staged tests/test_a.py",
    "git restore --source=HEAD~1 tests",
    "git restore .",
    "git restore src/m.py",
    "git rm tests/test_a.py",
    "git rm -r --cached tests",
    "git mv tests/test_a.py tests/b.py",
    "git mv src/m.py src/n.py",
    "git -C . reset --hard",
    "git -c core.x=1 restore tests",
    "env GIT_DIR=x git reset --hard",
    "git stash",
    "git stash pop",
    "git merge main",
    "git cherry-pick abc",
    "git apply p.diff",
    "git add -A && git commit -m x",
    "git add tests && git restore tests",
    "git restore 'tests/*'",
    "git restore specs/0001-x/req.md",
    "git restore specs",
    "git checkout -- specs/0001-x/req.md",
    "echo " + "x" * 300000 + " tests > tests/test_a.py",
    "echo hi > tests/test_a.py\n" * 150,
    "git status\n" * 600,
    ("echo a > tests/f%d.py; " * 150) % tuple(range(150)),
    "x" * 500000 + " > tests/test_a.py",
    ">" * 50000,
    "<<" * 20000,
    "cat <<EOF\n" + "a\n" * 20000 + "EOF",
    "(" * 300 + "echo hi > tests/test_a.py" + ")" * 300,
    "printf '%s' \"$(cat <<EOF\ntests\nEOF\n)\" > tests/test_a.py",
]
# 巨大なテストファイルの追記と書き換え（60万文字を超える）
BIGBODY = "".join(
    f"def test_n{i}():\n    assert {i} == {i}\n\n\n" for i in range(30000)
)


def run_all() -> dict:
    out: dict = {}

    def record(
        name: str, status: str | None, unlock: bool, switch: bool, build
    ) -> None:
        root = make_root(status)
        if unlock:
            (root / ".claude").mkdir(exist_ok=True)
            (root / ".claude/UNLOCK").write_text("")
        if switch:
            (root / ".claude").mkdir(exist_ok=True)
            (root / ".claude/ALLOW_TEST_CHANGE").write_text("")
        tool, tool_input = build(root)
        try:
            reason = guard.decide(tool, tool_input, root)
        except BaseException as e:
            reason = f"EXC {type(e).__name__}: {e}"
        left = (root / ".claude/ALLOW_TEST_CHANGE").exists()
        out[name] = {
            "reason": None
            if reason is None
            else str(reason).replace(str(root), "<ROOT>"),
            "switch_left": left,
        }

    for status in (None, "planned", "red", "green", "done"):
        for unlock in (False, True):
            for switch in (False, True):
                for name, build in EDITS.items():
                    record(
                        f"edit/{name}/{status}/u{int(unlock)}/s{int(switch)}",
                        status,
                        unlock,
                        switch,
                        build,
                    )
    for status in (None, "planned", "red", "done"):
        for switch in (False, True):
            for i, cmd in enumerate(CMDS):
                record(
                    f"bash/{i}/{status}/s{int(switch)}",
                    status,
                    False,
                    switch,
                    bash(cmd),
                )
        for i, cmd in enumerate(CMDS[:60]):
            record(f"bashU/{i}/{status}", status, True, False, bash(cmd))
    # 巨大なファイル
    for status in ("planned",):
        for label, new in (
            ("append", lambda base: base + "def test_zz():\n    assert 1\n"),
            (
                "append_skip",
                lambda base: base + "@pytest.mark.skip\ndef test_zz():\n    assert 1\n",
            ),
            ("append_dup", lambda base: base + "def test_n5():\n    assert 1\n"),
            ("rewrite", lambda base: base.replace("== 5", "== 6", 1)),
            ("indent_append", lambda base: base + "    x = 1\n"),
        ):
            root = make_root(status, commit=False)
            (root / T).write_text(TEST + BIGBODY)
            for args in (
                ["init", "-q"],
                ["config", "user.email", "t@e"],
                ["config", "user.name", "t"],
                ["add", "-A"],
                ["commit", "-q", "-m", "b"],
            ):
                subprocess.run(
                    ["git", "-C", str(root), *args],
                    check=True,
                    env=GIT_ENV,
                    capture_output=True,
                )  # noqa: S603, S607
            base = (root / T).read_text()
            (root / T).write_text(new(base))
            r = guard.decide(
                "Write", {"file_path": str(root / T), "content": new(base)}, root
            )
            out[f"big/{label}"] = {
                "reason": None if r is None else r.replace(str(root), "<ROOT>")
            }
    # CRLF
    root = make_root("planned", commit=False)
    (root / T).write_bytes(TEST.replace("\n", "\r\n").encode())
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@e"],
        ["config", "user.name", "t"],
        ["add", "-A"],
        ["commit", "-q", "-m", "b"],
    ):
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            env=GIT_ENV,
            capture_output=True,
        )  # noqa: S603, S607
    for label, old, new in (
        ("crlf_edit", "== 5", "== 6"),
        ("crlf_add", "== 0\r\n", "== 0\r\n\r\ndef test_c():\r\n    assert 1\r\n"),
    ):
        r = guard.decide(
            "Edit",
            {"file_path": str(root / T), "old_string": old, "new_string": new},
            root,
        )
        out[f"crlf/{label}"] = {
            "reason": None if r is None else r.replace(str(root), "<ROOT>")
        }
    # git が無い・リポジトリでない・コミット0件
    root = make_root("planned", commit=False)
    r = guard.decide(
        "Edit",
        {"file_path": str(root / T), "old_string": "== 5", "new_string": "== 6"},
        root,
    )
    out["nogit/not_a_repo"] = {
        "reason": None if r is None else r.replace(str(root), "<ROOT>")
    }
    root = make_root("planned", commit=False)
    subprocess.run(
        ["git", "-C", str(root), "init", "-q"],
        check=True,
        env=GIT_ENV,
        capture_output=True,
    )  # noqa: S603, S607
    r = guard.decide(
        "Edit",
        {"file_path": str(root / T), "old_string": "== 5", "new_string": "== 6"},
        root,
    )
    out["nogit/no_commits"] = {
        "reason": None if r is None else r.replace(str(root), "<ROOT>")
    }
    return out


def required_keys() -> dict[str, list[str]]:
    """req.md（0012）が、含まれていることの確認を求めている入力。"""
    bash = {c: f"bash/{i}/planned/s0" for i, c in enumerate(CMDS)}
    return {
        "新規": [
            "edit/write_new_test/planned/u0/s0",
            "edit/write_pytest_ini_new/planned/u0/s0",
            bash["echo hi > tests/test_new_file.py"],
            "nogit/no_commits",
        ],
        "削除": [
            "edit/edit_delete_test/planned/u0/s0",
            bash["rm tests/test_a.py"],
            bash["git rm tests/test_a.py"],
        ],
        "内容不明": [
            "edit/edit_nonexistent_old/planned/u0/s0",
            "edit/edit_no_path/planned/u0/s0",
        ],
        "解析しきれない": [
            "edit/edit_syntax_error/planned/u0/s0",
            "edit/write_pyproject_broken/planned/u0/s0",
            "edit/write_pyproject_tool_scalar/planned/u0/s0",
            "edit/write_test_null_byte/planned/u0/s0",
            "edit/write_test_deep_nesting/planned/u0/s0",
            "edit/write_conftest_broken/planned/u0/s0",
            "big/rewrite",
            "big/indent_append",
        ],
    }


if __name__ == "__main__":
    guard = _load_guard_from(sys.argv[1])
    result = run_all()
    Path(sys.argv[2]).write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=0),
        encoding="utf-8",
    )
    denies = sum(1 for v in result.values() if v["reason"])
    print(f"{len(result)} 入力、拒否 {denies}、許可 {len(result) - denies}")
