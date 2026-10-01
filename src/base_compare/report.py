"""検査の結果（Report）を、要約の文章にする。"""


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
        for f in report.findings:
            mark = (
                "（比較できない。承認でも通せない）" if f.kind == "比較できない" else ""
            )
            lines.append(f"- `{f.path}`: {f.reason}{mark}")
    if report.errors:
        lines.append("## ツール自身の失敗（承認でも通せない）")
        lines += [f"- {e}" for e in report.errors]
    return "\n".join(lines)
