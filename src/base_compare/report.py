"""検査の結果（Report）を、要約の文章にする。"""

MAX_LISTED = 50  # 検出を、この件数までだけ並べる（残りは件数で示す）


def render(report) -> str:
    lines = []
    if any(f.category == "guard" for f in report.approved):
        lines.append(
            "⚠️ 守りの仕組み自体（.github、.claude など）の変更が、承認されています"
        )
    if report.approved:
        lines.append("## 承認した内容")
        lines += [f"- `{f.path}`: {f.reason}" for f in report.approved]
    if report.findings:
        lines.append("## 承認されていない検出")
        for f in report.findings[:MAX_LISTED]:
            mark = (
                "（比較できない。承認でも通せない）" if f.kind == "比較できない" else ""
            )
            lines.append(f"- `{f.path}`: {f.reason}{mark}")
        if len(report.findings) > MAX_LISTED:
            lines.append(f"- ほか {len(report.findings) - MAX_LISTED} 件")
    if report.errors:
        lines.append("## ツール自身の失敗（承認でも通せない）")
        lines += [f"- {e}" for e in report.errors]
    return "\n".join(lines)
