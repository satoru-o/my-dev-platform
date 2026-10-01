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
