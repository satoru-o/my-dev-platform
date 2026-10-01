"""検査の入口。CI（失敗にする）と、ローカル（警告だけ）の2つの動かし方。"""

import argparse
import tempfile
from pathlib import Path

from base_compare import collect, core, gitio, report


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
    """IDの収集の関数（which は "base" か "head"）。基準は worktree で集める。"""

    def collector(which):
        if which == "head":
            return collect.collect_in(repo)
        base = gitio.run_git(repo, "merge-base", base_ref, "HEAD").decode().strip()
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "base"
            gitio.run_git(repo, "worktree", "add", "--detach", str(work), base)
            try:
                return collect.stable_ids(lambda: collect.collect_in(work))
            finally:
                gitio.run_git(repo, "worktree", "remove", "--force", str(work))

    return collector


def main(argv=None):
    parser = argparse.ArgumentParser(description="origin/main と比べた検査")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--mode", choices=["ci", "local"], default="local")
    parser.add_argument("--labels", default="", help="承認ラベル（カンマ区切り）")
    args = parser.parse_args(argv)
    labels = frozenset(x for x in args.labels.split(",") if x)
    code, text = run(
        args.repo, args.base, labels, args.mode, make_collector(args.repo, args.base)
    )
    print(text)
    return code
