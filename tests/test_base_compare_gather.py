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
