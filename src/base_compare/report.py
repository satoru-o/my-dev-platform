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
    return "\n".join(lines)
