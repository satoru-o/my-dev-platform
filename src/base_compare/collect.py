"""pytest の収集結果（テストID の一覧）を読む。"""


def parse_ids(out: str) -> frozenset[str]:
    """`pytest --collect-only -q` の出力から、テストID の集合を作る（重複は1つ）。"""
    return frozenset(
        line for line in out.split("\n") if "::" in line and not line.startswith(" ")
    )


def stable_ids(collect_once) -> frozenset[str]:
    return frozenset()  # スタブ（Red 用。わざと誤った値）
