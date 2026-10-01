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

# 守りの仕組み自体（これらの変更は、テストの変更とは別に、承認が要る）
GUARD_PATHS = (
    ".github/",
    ".claude/",
    "tools/guard-equiv/",
    "Makefile",
    "CLAUDE.md",
    "specs/README.md",
    "specs/_catalog/",
)


# 検出の種類ごとの、承認ラベル
LABEL_FOR = {"test": "test-change-approved", "guard": "guard-change-approved"}


@dataclass(frozen=True)
class FileChange:
    path: str  # リポジトリの相対パス（posix）
    base_src: str | None  # 基準（origin/main）の内容。無ければ None（新規）
    head_src: str | None  # いまの内容。無ければ None（削除）


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str
    category: str = "test"  # "test"（テストの変更）か "guard"（守りの仕組み自体）
    kind: str = "検出"  # "検出"（承認できる）か "比較できない"（承認でも通さない）


@dataclass
class Report:
    verdict: str  # "green" か "red"
    findings: list[Finding] = field(default_factory=list)  # 通っていない検出
    approved: list[Finding] = field(default_factory=list)  # 承認ラベルで通した検出
    errors: list[str] = field(
        default_factory=list
    )  # ツール自身の失敗（承認でも通さない）


# 比較の関数（change_reason_for）が返す理由の形: 「<対象>を変える・弱める・消す変更です（<理由>）」
_DETECT_MARK = "を変える・弱める・消す変更です（"


def _kind_of(reason: str) -> str:
    """理由から、種別を決める。知らない形は、「比較できない」（承認でも通さない）に倒す。"""
    _, found, why = reason.partition(_DETECT_MARK)
    if not found or why.startswith("大きすぎて"):
        return "比較できない"
    return "検出"


def _is_guard_path(path: str) -> bool:
    return any(path == g or path.startswith(g) for g in GUARD_PATHS)


def check(changes, base_ids, head_ids, labels, tool_errors=()) -> Report:
    findings = []
    errors = list(tool_errors)
    for change in changes:
        if _is_guard_path(change.path):
            findings.append(
                Finding(
                    path=change.path,
                    reason="守りの仕組み自体のファイルが、変わった",
                    category="guard",
                )
            )
            continue
        if change.base_src is None or change.head_src is None:
            continue
        try:
            reason = change_reason_for(change.path, change.base_src, change.head_src)
        except Exception as e:  # 想定外の例外は、ツール自身の失敗（承認でも赤）
            errors.append(
                f"{change.path}: 比較の関数が例外を投げた（{type(e).__name__}）"
            )
            continue
        if reason:
            kind = _kind_of(reason)
            findings.append(Finding(path=change.path, reason=reason, kind=kind))
    for lost in sorted(base_ids - head_ids):
        findings.append(Finding(path=lost, reason="基準にあったテストIDが、無くなった"))
    approved = [
        f for f in findings if f.kind == "検出" and LABEL_FOR[f.category] in labels
    ]
    remaining = [f for f in findings if f not in approved]
    return Report(
        verdict="red" if remaining or errors else "green",
        findings=remaining,
        approved=approved,
        errors=errors,
    )
