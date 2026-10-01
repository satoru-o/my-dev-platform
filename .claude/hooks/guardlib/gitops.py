"""Bash: git の操作（HEAD を動かす・書き換える、守る対象を戻す・消す）の判定。"""

import posixpath
import re
import shlex
from pathlib import Path

from guardlib.changes import CHANGE_HINT
from guardlib.heredoc import _WRAPPERS
from guardlib.paths import active_req_dirs, rel_path

# --- Bash: git 操作（HEAD を動かす・書き換える、守る対象のファイルを戻す・消す） --------------------

GUARDED_FILES = {"conftest.py", "pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"}
_GIT_WORD_RE = re.compile(r"(?<![\w./-])git(?![\w.-])")
_GIT_GLOBAL_WITH_VALUE = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
}
_COMMAND_SEPARATORS = {";", "&&", "||", "|", "&"}
MAX_GIT_LINES = (
    500  # git が出てくる行の、調べる数の上限（超えたら、解析しきれないものとして拒否）
)
MAX_GIT_LINE_LENGTH = 100_000
GIT_HISTORY_HINT = (
    "HEAD を動かす・書き換える操作は、既存のテストの変更を洗い流せてしまうため、AI には許しません。"
    "必要なら、人間が実行してください（スイッチでは通せません）。"
)


def _shell_words(line: str) -> list[str]:
    try:
        lex = shlex.shlex(line, posix=True, punctuation_chars=";&|")
        lex.whitespace_split = True
        return list(lex)
    except ValueError:
        return line.split()


def _git_invocation(words: list[str]) -> tuple[str, list[str]] | None:
    """（サブコマンド、引数）。git のコマンドでなければ None。"""
    ws = list(words)
    while ws and (re.fullmatch(r"\w+=.*", ws[0]) or ws[0] in _WRAPPERS):
        ws.pop(0)
    if not ws or posixpath.basename(ws[0]) != "git":
        return None
    i = 1
    while i < len(ws) and ws[i].startswith("-"):
        i += 2 if ws[i] in _GIT_GLOBAL_WITH_VALUE else 1
    if i >= len(ws):
        return None
    return ws[i], ws[i + 1 :]


def _touches_guarded(path: str, root: Path) -> bool:
    """git に渡されたパス（pathspec）が、守る対象（tests/、pytest の設定、req.md）に触れるか。"""
    if path in {".", "./", ":/", ":", "*", "/", ""}:
        return True  # 「全部」を指す形は、守る対象に触れるものとして扱う
    literal = re.split(r"[*?\[]", path, maxsplit=1)[0]
    if not literal:
        return True
    rel = rel_path(literal.rstrip("/") or ".", root)
    if rel is None:
        return False
    if rel in {"", ".", "tests"} or rel.startswith("tests/") or rel in GUARDED_FILES:
        return True
    active = active_req_dirs(root)  # 実装中の req の req.md（とそれを含むディレクトリ）
    parts = rel.split("/")
    if (
        parts[0] == "specs"
        and len(parts) <= 3
        and (len(parts) < 3 or parts[2] == "req.md")
    ):
        return bool(active) if len(parts) == 1 else parts[1] in active
    return False


def _checkout_paths(args: list[str], root: Path) -> list[str]:
    """`git checkout` の引数のうち、パス（ファイルを戻す対象）。ブランチの切り替えなら空。"""
    if "--" in args:
        return args[args.index("--") + 1 :]
    positional: list[str] = []
    skip = False
    for a in args:
        if skip:
            skip = False
        elif a in {"-b", "-B", "--orphan"}:
            skip = True
        elif not a.startswith("-"):
            positional.append(a)
    if len(positional) >= 2:
        return positional[1:]  # `checkout <ref> <path>...`
    if len(positional) == 1 and (root / positional[0]).exists():
        return positional  # `checkout <path>`（`checkout .` など）
    return []


def _restore_paths(args: list[str]) -> list[str] | None:
    """`git restore` の引数のうち、パス。作業ツリーを変えない（`--staged` だけ）なら None。"""
    staged = any(a in {"--staged", "-S"} for a in args)
    worktree = any(a in {"--worktree", "-W"} for a in args)
    if staged and not worktree:
        return None
    paths: list[str] = []
    skip = False
    for a in args:
        if skip:
            skip = False
        elif a in {"--source", "-s"}:
            skip = True
        elif a == "--":
            continue
        elif not a.startswith("-"):
            paths.append(a)
    return paths


def git_reason(shell: str, root: Path) -> tuple[str | None, bool]:
    """（拒否する理由、スイッチで通せるか）。履歴を動かす操作は、スイッチで通せない。"""
    candidates = [ln for ln in shell.split("\n") if _GIT_WORD_RE.search(ln)]
    if not candidates:
        return None, False
    if len(candidates) > MAX_GIT_LINES or any(
        len(ln) > MAX_GIT_LINE_LENGTH for ln in candidates
    ):
        return (
            "git のコマンドが多すぎる・長すぎて、解析しきれないため、拒否側に倒しました。",
            False,
        )
    switchable: str | None = None
    for line in candidates:
        commands: list[list[str]] = [[]]
        for w in _shell_words(line):
            if w in _COMMAND_SEPARATORS:
                commands.append([])
            else:
                commands[-1].append(w)
        for words in commands:
            inv = _git_invocation(words)
            if inv is None:
                continue
            sub, args = inv
            if sub == "rebase" or (
                sub == "commit"
                and any(a == "--amend" or a.startswith("--amend=") for a in args)
            ):
                return (
                    f"git {sub}（履歴の書き換え）は拒否します。{GIT_HISTORY_HINT}",
                    False,
                )
            if sub == "reset":
                if "--hard" in args:
                    return f"git reset --hard は拒否します。{GIT_HISTORY_HINT}", False
                for a in args:
                    if a == "--":
                        break
                    if a.startswith("-") or a == "HEAD" or (root / a).exists():
                        continue  # オプション、HEAD、パス（add の取り消し）
                    return (
                        f"git reset <コミット>（HEAD を動かす）は拒否します。{GIT_HISTORY_HINT}",
                        False,
                    )
                continue
            if sub == "checkout":
                paths: list[str] | None = _checkout_paths(args, root)
            elif sub == "restore":
                paths = _restore_paths(args)
            elif sub in {"rm", "mv"}:
                paths = [a for a in args if not a.startswith("-")]
            else:
                continue
            for p in paths or []:
                if _touches_guarded(p, root):
                    switchable = f"git {sub} が、守る対象（{p}）を、別の内容に戻す・消す・動かす操作です。{CHANGE_HINT}"
    return switchable, True
