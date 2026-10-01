"""検査の入口。CI（失敗にする）と、ローカル（警告だけ）の2つの動かし方。"""

from base_compare import core, gitio, report


def run(repo, base_ref, labels, mode, collect_ids):
    """（終了コード, 要約の文章）。mode は "ci"（赤なら 1）か "local"（常に 0）。"""
    errors: list[str] = []
    changes = []
    base_ids = head_ids = frozenset()
    try:
        changes = gitio.gather_changes(repo, base_ref)
        base_ids = collect_ids("base")
        head_ids = collect_ids("head")
    except gitio.ToolError as e:
        errors.append(str(e))
    result = core.check(
        changes=changes,
        base_ids=base_ids,
        head_ids=head_ids,
        labels=labels,
        tool_errors=errors,
    )
    text = report.render(result)
    if mode == "local":
        head = "警告（ローカルでは失敗にしない。承認の正本は CI のラベル）"
        if errors:
            head += (
                "\n⚠️ 比較できなかった（基準が取れない、など）。CI で確かめてください"
            )
        return 0, f"{head}\n{text}"
    return (0 if result.verdict == "green" else 1), text


def make_collector(repo, base_ref):
    return lambda which: frozenset()  # スタブ（Red 用。わざと誤った値）
