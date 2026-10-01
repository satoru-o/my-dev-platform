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
