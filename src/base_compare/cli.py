"""検査の入口。CI（失敗にする）と、ローカル（警告だけ）の2つの動かし方。"""

from base_compare import core, gitio, report


def run(repo, base_ref, labels, mode, collect_ids):
    """（終了コード, 要約の文章）。mode は "ci"（赤なら 1）か "local"（常に 0）。"""
    changes = gitio.gather_changes(repo, base_ref)
    result = core.check(
        changes=changes,
        base_ids=collect_ids("base"),
        head_ids=collect_ids("head"),
        labels=labels,
    )
    return (0 if result.verdict == "green" else 1), report.render(result)
