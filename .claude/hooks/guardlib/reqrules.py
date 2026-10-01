"""req.md の AC の表の比較。入力は旧・新の文字列だけ（純粋関数）。"""

import re
from collections import Counter

_REQ_RE = re.compile(r"specs/([^/]+)/req\.md")
_AC_HEAD_RE = re.compile(r"^###\s+AC-(\d+)\b")
_TABLE_SEPARATOR_RE = re.compile(r"\|[\s:|-]+\|")


def ac_rows(src: str) -> dict[str, Counter]:
    """AC 番号 → その AC の表の行（空白をそろえたもの）。"""
    rows: dict[str, Counter] = {}
    current: str | None = None
    for line in src.split("\n"):
        m = _AC_HEAD_RE.match(line)
        if m:
            current = m.group(1)
            rows.setdefault(current, Counter())
        elif line.startswith("#"):
            current = None
        elif current and line.lstrip().startswith("|"):
            norm = re.sub(r"\s+", " ", line.strip())
            if not _TABLE_SEPARATOR_RE.fullmatch(norm):
                rows[current][norm] += 1
    return rows


def req_change_reason(base_src: str | None, new_src: str) -> str | None:
    """req.md の AC の表の、既存の行を、変えた・消した・番号を書き換えた変更なら、その理由。"""
    if base_src is None or base_src == new_src:
        return None
    new = ac_rows(new_src)
    for number, base_rows in ac_rows(base_src).items():
        if base_rows - new.get(number, Counter()):
            return f"AC-{number} の表の既存の行が、変わった・消えた（番号の書き換えは、削除と追加として扱う）"
    return None
