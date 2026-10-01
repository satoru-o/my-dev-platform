from base_compare import collect


def test_S02_収集の出力からIDの集合を読む_重複は1つ_要約の行は除く():
    out = (
        "tests/test_a.py::test_a\n"
        "tests/テスト_🍎.py::test_x[１２３]\n"
        "tests/test_a.py::test_a\n"
        "\n"
        "3 tests collected in 0.01s\n"
    )

    assert collect.parse_ids(out) == frozenset(
        {"tests/test_a.py::test_a", "tests/テスト_🍎.py::test_x[１２３]"}
    )
