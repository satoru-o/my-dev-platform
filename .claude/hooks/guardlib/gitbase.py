"""「既存」の基準（HEAD）を git から取る。"""

import os
import subprocess
from pathlib import Path


class GitError(Exception):
    """「既存」の基準（HEAD）が取れない。呼び出し側は、拒否側に倒す。"""


def _git(root: Path, timeout: float, *args: str) -> subprocess.CompletedProcess:
    # 作業フォルダを固定し、GIT_ で始まる環境変数（GIT_DIR など）を掃除して呼ぶ。
    # 別のリポジトリを「基準」にされて、すべて新規として通ってしまうのを防ぐ。
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "--no-pager", *args],  # noqa: S607
            capture_output=True,
            cwd=root,
            env=env,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise GitError("git が時間内に答えない") from e
    except OSError as e:
        raise GitError(f"git を実行できない（{type(e).__name__}）") from e


def head_content(root: Path, rel: str, timeout: float) -> str | None:
    """HEAD にあるファイルの内容。HEAD に無い（新規）、コミットが0件なら None。

    基準が取れなければ GitError。「コミット0件」と「git の失敗」は、別に判定する。
    """
    has_head = _git(root, timeout, "rev-parse", "--verify", "--quiet", "HEAD")
    if has_head.returncode == 1 and not has_head.stdout.strip():
        return None  # コミットが0件: すべて新規として扱う
    if has_head.returncode != 0:
        raise GitError("git rev-parse が失敗した（リポジトリではない、など）")
    tree = _git(root, timeout, "ls-tree", "-z", "HEAD", "--", rel)
    if tree.returncode != 0:
        raise GitError("git ls-tree が失敗した")
    if not tree.stdout:
        return None  # HEAD に無い: 新規
    meta = tree.stdout.split(b"\t", 1)[0].decode("utf-8", "replace").split()
    if len(meta) < 3 or meta[1] != "blob":
        return None
    blob = _git(root, timeout, "cat-file", "blob", meta[2])
    if blob.returncode != 0:
        raise GitError("git cat-file が失敗した")
    return blob.stdout.decode("utf-8", "replace")


_head_paths_cache: dict[Path, frozenset[str] | None] = {}


def head_paths(root: Path, timeout: float) -> frozenset[str] | None:
    """HEAD にあるファイルの一覧。コミットが0件なら None。git の失敗は GitError。

    1回の判定（decide）の中では、1回だけ取る（書き込み先が多くても、git を何度も呼ばない）。
    """
    if root in _head_paths_cache:
        return _head_paths_cache[root]
    has_head = _git(root, timeout, "rev-parse", "--verify", "--quiet", "HEAD")
    if has_head.returncode == 1 and not has_head.stdout.strip():
        _head_paths_cache[root] = None
        return None
    if has_head.returncode != 0:
        raise GitError("git rev-parse が失敗した（リポジトリではない、など）")
    listing = _git(root, timeout, "ls-tree", "-r", "-z", "--name-only", "HEAD")
    if listing.returncode != 0:
        raise GitError("git ls-tree が失敗した")
    paths = frozenset(
        p.decode("utf-8", "replace") for p in listing.stdout.split(b"\0") if p
    )
    _head_paths_cache[root] = paths
    return paths
