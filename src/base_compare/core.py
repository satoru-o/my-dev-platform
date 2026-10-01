"""`origin/main` と比べた検査の、判定の中心（純粋関数。git・ファイル・環境には触れない）。"""

from dataclasses import dataclass, field


@dataclass
class Report:
    verdict: str  # "green" か "red"
    findings: list = field(default_factory=list)


def check(changes, base_ids, head_ids, labels) -> Report:
    return Report(verdict="red")  # スタブ（Red 用。わざと誤った値）
