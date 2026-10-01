from test_base_compare_gather import git, make_repo

from base_compare import cli


def red_repo(tmp_path):
    make_repo(tmp_path, {"tests/test_a.py": "def test_a():\n    assert 1 == 1\n"})
    git(tmp_path, "checkout", "-q", "-b", "work")
    (tmp_path / "tests/test_a.py").write_text("def test_a():\n    assert 1 == 2\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "work")


def no_ids(which):
    return frozenset()


def test_AC6_CIでは検出があれば失敗の終了コードになる(tmp_path):
    red_repo(tmp_path)

    code, text = cli.run(tmp_path, "main", frozenset(), "ci", no_ids)

    assert code == 1
    assert "tests/test_a.py" in text


def test_AC6_ローカルでは検出があっても警告だけで成功の終了コード(tmp_path):
    red_repo(tmp_path)

    code, text = cli.run(tmp_path, "main", frozenset(), "local", no_ids)

    assert code == 0
    assert "警告" in text
    assert "tests/test_a.py" in text
