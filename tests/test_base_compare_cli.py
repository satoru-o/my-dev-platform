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


def test_AC3_基準のコードと今のコードを実際に収集してIDの集合を作る(tmp_path):
    make_repo(
        tmp_path,
        {
            "tests/test_a.py": (
                "def test_a():\n    assert True\n\n\ndef test_b():\n    assert True\n"
            )
        },
    )
    git(tmp_path, "checkout", "-q", "-b", "work")
    (tmp_path / "tests/test_a.py").write_text("def test_a():\n    assert True\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "work")

    collector = cli.make_collector(tmp_path, "main")

    assert collector("base") == frozenset(
        {"tests/test_a.py::test_a", "tests/test_a.py::test_b"}
    )
    assert collector("head") == frozenset({"tests/test_a.py::test_a"})


def test_AC2_CIでは基準が取れなければツール自身の失敗で失敗の終了コード(tmp_path):
    red_repo(tmp_path)

    code, text = cli.run(tmp_path, "origin/main", frozenset(), "ci", no_ids)

    assert code == 1
    assert "ツール自身の失敗" in text


def test_AC6_ローカルで基準が取れなくても警告だけで成功_比較できなかったと表示(
    tmp_path,
):
    red_repo(tmp_path)

    code, text = cli.run(tmp_path, "origin/main", frozenset(), "local", no_ids)

    assert code == 0
    assert "比較できなかった" in text
