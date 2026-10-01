"""`origin/main` と比べた検査の、判定の中心（git・ファイル・環境には触れない）。

比較の本体は、hook と同じ純粋関数
（`.claude/hooks/guardlib/compare.py` の `change_reason_for`）。
ここでは、それを使って、変更の一覧から、検出と、緑・赤を決める。
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

_HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from guardlib.compare import change_reason_for  # noqa: E402


@dataclass(frozen=True)
class FileChange:
    path: str  # リポジトリの相対パス（posix）
    base_src: str | None  # 基準（origin/main）の内容。無ければ None（新規）
    head_src: str | None  # いまの内容。無ければ None（削除）


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


@dataclass
class Report:
    verdict: str  # "green" か "red"
    findings: list[Finding] = field(default_factory=list)


def check(changes, base_ids, head_ids, labels) -> Report:
    findings = []
    for change in changes:
        if change.base_src is None or change.head_src is None:
            continue
        reason = change_reason_for(change.path, change.base_src, change.head_src)
        if reason:
            findings.append(Finding(path=change.path, reason=reason))
    for lost in sorted(base_ids - head_ids):
        findings.append(Finding(path=lost, reason="基準にあったテストIDが、無くなった"))
    return Report(verdict="red" if findings else "green", findings=findings)
