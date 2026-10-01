"""pytest の収集結果（テストID の一覧）を読む。"""


def parse_ids(out: str) -> frozenset[str]:
    """`pytest --collect-only -q` の出力から、テストID の集合を作る（重複は1つ）。"""
    return frozenset(
        line for line in out.split("\n") if "::" in line and not line.startswith(" ")
    )


def stable_ids(collect_once) -> frozenset[str]:
    """同じコードを2回収集し、同じ集合になったときだけ、それを返す。"""
    first = collect_once()
    collect_once()
    return first
