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


def test_S03_同じコードで2回の収集が食い違ったらツール自身の失敗():
    from base_compare import gitio

    results = iter(
        [
            frozenset({"tests/test_a.py::test_a"}),
            frozenset({"tests/test_a.py::test_a", "tests/test_a.py::test_b"}),
        ]
    )

    try:
        collect.stable_ids(lambda: next(results))
    except gitio.ToolError:
        raised = True
    else:
        raised = False

    assert raised
