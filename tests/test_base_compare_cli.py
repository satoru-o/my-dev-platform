from base_compare import cli
from test_base_compare_gather import git, make_repo


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


def test_AC5_入口_ラベルが無ければ失敗_あれば成功で承認した内容を表示(tmp_path, capsys):
    red_repo(tmp_path)
    base = ["--repo", str(tmp_path), "--base", "main", "--mode", "ci"]

    without = cli.main(base)
    out_without = capsys.readouterr().out
    approved = cli.main([*base, "--labels", "test-change-approved"])
    out_approved = capsys.readouterr().out

    assert without == 1
    assert "承認されていない検出" in out_without
    assert approved == 0
    assert "承認した内容" in out_approved


def test_X04_想定外の例外でも_CIでは失敗_ローカルでは警告_内部情報は出さない(
    tmp_path, capsys, monkeypatch
):
    def boom(*args, **kwargs):
        raise RuntimeError("秘密のトークン ghp_xxx /home/someone/.ssh")

    monkeypatch.setattr(cli, "run", boom)

    ci = cli.main(["--repo", str(tmp_path), "--mode", "ci"])
    out_ci = capsys.readouterr().out
    local = cli.main(["--repo", str(tmp_path), "--mode", "local"])
    out_local = capsys.readouterr().out

    assert ci == 1
    assert local == 0
    for out in (out_ci, out_local):
        assert "RuntimeError" in out
        assert "ghp_xxx" not in out
        assert "/home/someone" not in out


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
