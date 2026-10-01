"""git からの読み取り（`git diff` の出力の解釈、ファイルの内容の取得）。"""

import os
import subprocess

from base_compare.core import FileChange, compare_kind, is_guard_path

GIT_TIMEOUT_SECONDS = 60.0


class ToolError(Exception):
    """ツール自身の失敗（比較ができない）。承認ラベルがあっても、赤にする。"""


def run_git(repo, *args: str, timeout: float = GIT_TIMEOUT_SECONDS) -> bytes:
    """git を、作業フォルダを固定し、GIT_ で始まる環境変数を掃除して呼ぶ。"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        done = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo), "--no-pager", *args],  # noqa: S607
            capture_output=True,
            env=env,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ToolError("git が時間内に答えない") from e
    except OSError as e:
        raise ToolError(f"git を実行できない（{type(e).__name__}）") from e
    if done.returncode != 0:
        raise ToolError(f"git {args[0]} が失敗した")
    return done.stdout


def parse_name_status(out: bytes) -> list[tuple[str, str]]:
    """`git diff --name-status -z` の出力を、（状態, パス）の一覧にする。"""
    tokens = [t.decode("utf-8", "replace") for t in out.split(b"\0") if t != b""]
    if len(tokens) % 2:
        raise ToolError("git diff の出力が、（状態, パス）の組になっていない")
    return list(zip(tokens[0::2], tokens[1::2], strict=True))


def _blob(repo, ref: str, path: str) -> str:
    return run_git(repo, "show", f"{ref}:{path}").decode("utf-8", "replace")


def gather_changes(repo, base_ref: str) -> list[FileChange]:
    """基準（base_ref との merge-base）と HEAD の差分のうち、検査の対象だけを集める。"""
    base = run_git(repo, "merge-base", base_ref, "HEAD").decode().strip()
    diff = run_git(repo, "diff", "--name-status", "-z", "--no-renames", base, "HEAD")
    changes = []
    for status, path in parse_name_status(diff):
        if is_guard_path(path):
            changes.append(FileChange(path=path, base_src=None, head_src=None))
        elif compare_kind(path) is not None:
            changes.append(
                FileChange(
                    path=path,
                    base_src=None if status == "A" else _blob(repo, base, path),
                    head_src=None if status == "D" else _blob(repo, "HEAD", path),
                )
            )
    return changes
