from base_compare import core


def test_AC1_差分が空なら緑():
    report = core.check(
        changes=[], base_ids=frozenset(), head_ids=frozenset(), labels=frozenset()
    )

    assert report.verdict == "green"
    assert report.findings == []


def test_AC1_既存のテストの期待値を書き換えると赤():
    change = core.FileChange(
        path="tests/test_a.py",
        base_src="def test_a():\n    assert add(2, 3) == 5\n",
        head_src="def test_a():\n    assert add(2, 3) == 6\n",
    )

    report = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset(),
    )

    assert report.verdict == "red"
    assert [f.path for f in report.findings] == ["tests/test_a.py"]


def test_AC1_テストを足しただけなら緑():
    change = core.FileChange(
        path="tests/test_a.py",
        base_src="def test_a():\n    assert add(2, 3) == 5\n",
        head_src=(
            "def test_a():\n    assert add(2, 3) == 5\n\n\n"
            "def test_b():\n    assert add(0, 0) == 0\n"
        ),
    )

    report = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset(),
    )

    assert report.verdict == "green"
    assert report.findings == []


def test_AC4_守りの仕組み自体のファイルを変えると赤():
    guarded = [
        ".github/workflows/check.yml",
        ".claude/hooks/guard.py",
        "tools/guard-equiv/run.py",
        "Makefile",
        "CLAUDE.md",
        "specs/README.md",
        "specs/_catalog/viewpoints.md",
    ]

    for path in guarded:
        change = core.FileChange(path=path, base_src="a\n", head_src="b\n")
        report = core.check(
            changes=[change],
            base_ids=frozenset(),
            head_ids=frozenset(),
            labels=frozenset(),
        )

        assert report.verdict == "red", path
        assert [f.path for f in report.findings] == [path]
        assert [f.category for f in report.findings] == ["guard"]


def test_AC5_テストの検出は承認ラベルがあれば緑で承認した内容が出る():
    change = core.FileChange(
        path="tests/test_a.py",
        base_src="def test_a():\n    assert add(2, 3) == 5\n",
        head_src="def test_a():\n    assert add(2, 3) == 6\n",
    )

    report = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved"}),
    )

    assert report.verdict == "green"
    assert report.findings == []
    assert [f.path for f in report.approved] == ["tests/test_a.py"]
    assert report.approved[0].reason


def test_AC5_テストと守りの仕組みの検出が混ざるときはラベルが両方要る():
    changes = [
        core.FileChange(
            path="tests/test_a.py",
            base_src="def test_a():\n    assert add(2, 3) == 5\n",
            head_src="def test_a():\n    assert add(2, 3) == 6\n",
        ),
        core.FileChange(path="Makefile", base_src="a\n", head_src="b\n"),
    ]

    only_test = core.check(
        changes=changes,
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved"}),
    )
    both = core.check(
        changes=changes,
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved", "guard-change-approved"}),
    )

    assert only_test.verdict == "red"
    assert [f.path for f in only_test.findings] == ["Makefile"]
    assert both.verdict == "green"
    assert sorted(f.path for f in both.approved) == ["Makefile", "tests/test_a.py"]


def test_AC5_検出が無いPRにラベルだけ付いていても緑():
    report = core.check(
        changes=[],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved", "guard-change-approved"}),
    )

    assert report.verdict == "green"
    assert report.findings == []
    assert report.approved == []


def test_AC4_テストでも守りの仕組みでもないファイルの変更は検出しない():
    change = core.FileChange(path="docs/a.md", base_src="a\n", head_src="b\n")

    report = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset(),
    )

    assert report.verdict == "green"
    assert report.findings == []


def test_AC2_ツール自身の失敗は承認ラベルがあっても赤():
    report = core.check(
        changes=[],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved", "guard-change-approved"}),
        tool_errors=["テストの収集が時間内に終わらない"],
    )

    assert report.verdict == "red"
    assert report.errors == ["テストの収集が時間内に終わらない"]


def test_AC2_比較の関数が例外を投げたら承認ラベルがあっても赤():
    change = core.FileChange(
        path="pyproject.toml",
        base_src='[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
        head_src="tool = 1\n",
    )

    report = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved", "guard-change-approved"}),
    )

    assert report.verdict == "red"
    assert len(report.errors) == 1
    assert "pyproject.toml" in report.errors[0]


def test_AC2_構文エラーのテストは検出で承認ラベルで通せる():
    change = core.FileChange(
        path="tests/test_a.py",
        base_src="def test_a():\n    assert add(2, 3) == 5\n",
        head_src="def test_a(:\n",
    )

    without = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset(),
    )
    approved = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved"}),
    )

    assert without.verdict == "red"
    assert approved.verdict == "green"
    assert [f.path for f in approved.approved] == ["tests/test_a.py"]


def test_AC2_巨大で比較できないファイルは承認ラベルがあっても赤():
    base = "x = 1\n" * 150_000
    change = core.FileChange(
        path="tests/test_big.py",
        base_src=base,
        head_src=base.replace("x = 1", "x = 2", 1),
    )

    report = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved", "guard-change-approved"}),
    )

    assert report.verdict == "red"
    assert [f.kind for f in report.findings] == ["比較できない"]


def test_AC2_知らない形の理由は比較できないとして承認ラベルがあっても赤(monkeypatch):
    monkeypatch.setattr(core, "change_reason_for", lambda *a: "未知の理由")
    change = core.FileChange(path="tests/test_a.py", base_src="a\n", head_src="b\n")

    report = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset({"test-change-approved", "guard-change-approved"}),
    )

    assert report.verdict == "red"
    assert [f.kind for f in report.findings] == ["比較できない"]


def test_AC1_pytestの設定を変えると赤():
    change = core.FileChange(
        path="pyproject.toml",
        base_src='[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
        head_src=(
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]\naddopts = "-k x"\n'
        ),
    )

    report = core.check(
        changes=[change],
        base_ids=frozenset(),
        head_ids=frozenset(),
        labels=frozenset(),
    )

    assert report.verdict == "red"
    assert [f.path for f in report.findings] == ["pyproject.toml"]


def test_AC3_基準にあったテストIDが無くなったら赤():
    report = core.check(
        changes=[],
        base_ids=frozenset({"tests/test_a.py::test_a", "tests/test_a.py::test_b"}),
        head_ids=frozenset({"tests/test_a.py::test_a"}),
        labels=frozenset(),
    )

    assert report.verdict == "red"
    assert [f.path for f in report.findings] == ["tests/test_a.py::test_b"]


def test_AC3_テストを1つ消して別を1つ足しても赤():
    report = core.check(
        changes=[],
        base_ids=frozenset({"tests/test_a.py::test_a", "tests/test_a.py::test_b"}),
        head_ids=frozenset({"tests/test_a.py::test_a", "tests/test_a.py::test_c"}),
        labels=frozenset(),
    )

    assert report.verdict == "red"
    assert [f.path for f in report.findings] == ["tests/test_a.py::test_b"]


def test_AC3_基準のテストが全部無くなったら赤():
    report = core.check(
        changes=[],
        base_ids=frozenset({"tests/test_a.py::test_a"}),
        head_ids=frozenset(),
        labels=frozenset(),
    )

    assert report.verdict == "red"


def test_AC3_テストIDが増えただけなら緑():
    report = core.check(
        changes=[],
        base_ids=frozenset(),
        head_ids=frozenset({"tests/test_a.py::test_a"}),
        labels=frozenset(),
    )

    assert report.verdict == "green"
    assert report.findings == []
