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


def test_S03_同じコードを2回収集して同じなら_そのIDの集合を返す():
    calls = []

    def collect_once():
        calls.append(1)
        return frozenset({"tests/test_a.py::test_a"})

    assert collect.stable_ids(collect_once) == frozenset({"tests/test_a.py::test_a"})
    assert len(calls) == 2
