import subprocess

from base_compare import core, gitio

GIT_ENV = {"PATH": "/usr/bin:/bin", "HOME": "/tmp"}


def git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        env=GIT_ENV,
        capture_output=True,
    )


def make_repo(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")


def test_AC1_作業ブランチの変更を基準との差分として集める(tmp_path):
    make_repo(
        tmp_path,
        {
            "tests/test_a.py": "def test_a():\n    assert 1 == 1\n",
            "docs/a.md": "# a\n",
        },
    )
    git(tmp_path, "checkout", "-q", "-b", "work")
    (tmp_path / "tests/test_a.py").write_text("def test_a():\n    assert 1 == 2\n")
    (tmp_path / "tests/test_new.py").write_text("def test_n():\n    assert True\n")
    (tmp_path / "docs/a.md").write_text("# b\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "work")

    changes = gitio.gather_changes(tmp_path, "main")

    assert sorted(changes, key=lambda c: c.path) == [
        core.FileChange(
            path="tests/test_a.py",
            base_src="def test_a():\n    assert 1 == 1\n",
            head_src="def test_a():\n    assert 1 == 2\n",
        ),
        core.FileChange(
            path="tests/test_new.py",
            base_src=None,
            head_src="def test_n():\n    assert True\n",
        ),
    ]


def test_S01_基準が取れなければツール自身の失敗(tmp_path):
    make_repo(tmp_path, {"tests/test_a.py": "def test_a():\n    assert True\n"})

    try:
        gitio.gather_changes(tmp_path, "origin/main")
    except gitio.ToolError:
        raised = True
    else:
        raised = False

    assert raised


def test_S01_削除されたテストは_HEADの内容が無い変更として集める(tmp_path):
    make_repo(tmp_path, {"tests/test_a.py": "def test_a():\n    assert True\n"})
    git(tmp_path, "checkout", "-q", "-b", "work")
    git(tmp_path, "rm", "-q", "tests/test_a.py")
    git(tmp_path, "commit", "-q", "-m", "rm")

    changes = gitio.gather_changes(tmp_path, "main")

    assert changes == [
        core.FileChange(
            path="tests/test_a.py",
            base_src="def test_a():\n    assert True\n",
            head_src=None,
        )
    ]


def test_X04_gitの失敗の表示に_パスやgitの出力を含めない(tmp_path):
    secret_dir = tmp_path / "秘密のディレクトリ"
    secret_dir.mkdir()

    try:
        gitio.gather_changes(secret_dir, "main")
    except gitio.ToolError as e:
        message = str(e)
    else:
        message = ""

    assert message
    assert "秘密のディレクトリ" not in message
    assert str(tmp_path) not in message
    assert "fatal" not in message


def test_V01_空のテストファイルを足しただけなら_検出しない(tmp_path):
    make_repo(tmp_path, {"docs/a.md": "# a\n"})
    git(tmp_path, "checkout", "-q", "-b", "work")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_empty.py").write_text("")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "empty")

    changes = gitio.gather_changes(tmp_path, "main")
    report = core.check(
        changes=changes,
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset(),
    )

    assert report.verdict == "green"


def test_X03_危険な文字列を含むパスも_実行されず_パスのまま扱う(tmp_path):
    make_repo(tmp_path, {"docs/a.md": "# a\n"})
    git(tmp_path, "checkout", "-q", "-b", "work")
    evil = ".github/$(touch pwned); rm -rf x.yml"
    (tmp_path / evil).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / evil).write_text("a\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "evil")

    changes = gitio.gather_changes(tmp_path, "main")

    assert [c.path for c in changes] == [evil]
    assert not (tmp_path / "pwned").exists()
