from base_compare import core, report


def test_AC5_承認した内容を要約に出す():
    result = core.Report(
        verdict="green",
        approved=[
            core.Finding(
                path="tests/test_a.py",
                reason="既存のテストを変える・弱める・消す変更です（本文が変わった）",
            )
        ],
    )

    text = report.render(result)

    assert "承認した内容" in text
    assert "tests/test_a.py" in text
    assert "本文が変わった" in text


def test_AC5_守りの仕組み自体の承認が混ざるときは_要約の先頭に目立つ印を付ける():
    result = core.Report(
        verdict="green",
        approved=[
            core.Finding(path="tests/test_a.py", reason="r1"),
            core.Finding(
                path=".github/workflows/check.yml", reason="r2", category="guard"
            ),
        ],
    )

    first_line = report.render(result).split("\n")[0]

    assert "⚠️" in first_line
    assert "守りの仕組み自体" in first_line


def test_V04_検出が非常に多いときは_50件までを出して_残りの件数を示す():
    result = core.Report(
        verdict="red",
        findings=[
            core.Finding(path=f"tests/t.py::test_{i}", reason="無くなった")
            for i in range(120)
        ],
    )

    lines = report.render(result).split("\n")

    assert len([x for x in lines if x.startswith("- `tests/t.py::test_")]) == 50
    assert any("ほか 70 件" in x for x in lines)


def test_O01_赤の理由を_検出_比較できない_ツール自身の失敗に分けて出す():
    result = core.Report(
        verdict="red",
        findings=[
            core.Finding(path="tests/test_a.py", reason="期待値が変わった"),
            core.Finding(path="tests/big.py", reason="大きすぎる", kind="比較できない"),
        ],
        errors=["テストの収集が時間内に終わらない"],
    )

    text = report.render(result)

    assert "承認されていない検出" in text
    assert "`tests/test_a.py`: 期待値が変わった" in text
    assert "比較できない" in text
    assert "`tests/big.py`: 大きすぎる" in text
    assert "ツール自身の失敗" in text
    assert "テストの収集が時間内に終わらない" in text
