"""pytest の収集結果（テストID の一覧）を読む。"""

import subprocess
import sys

from base_compare.gitio import ToolError


def parse_ids(out: str) -> frozenset[str]:
    """`pytest --collect-only -q` の出力から、テストID の集合を作る（重複は1つ）。"""
    return frozenset(
        line for line in out.split("\n") if "::" in line and not line.startswith(" ")
    )


def stable_ids(collect_once) -> frozenset[str]:
    """同じコードを2回収集し、同じ集合になったときだけ、それを返す。"""
    first = collect_once()
    if collect_once() != first:
        raise ToolError("同じコードを2回収集したら、テストIDの一覧が食い違った")
    return first


def collect_in(directory, timeout: float = 300.0) -> frozenset[str]:
    """ディレクトリで `pytest --collect-only` を実行し、テストID の集合を返す（テストは実行しない）。"""
    done = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=directory,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return parse_ids(done.stdout.decode("utf-8", "replace"))
