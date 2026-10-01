from base_compare import core


def test_AC1_差分が空なら緑():
    report = core.check(
        changes=[], base_ids=frozenset(), head_ids=frozenset(), labels=frozenset()
    )

    assert report.verdict == "green"
    assert report.findings == []
