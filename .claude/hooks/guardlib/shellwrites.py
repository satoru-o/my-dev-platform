"""Bash: シェルのコマンドの書き込み先（リダイレクト、書き込み系コマンド）の判定。"""

import re
import shlex
from pathlib import Path

from guardlib.changes import CHANGE_HINT, _guarded_kind
from guardlib.gitbase import GitError, head_paths
from guardlib.paths import rel_path

# Bash 用。パスを表す正規表現（コマンド文字列の中から探す）
PATH_RE = {
    "protected": r"(?:\.claude(?![\w-])|CLAUDE\.md|\.github(?![\w-])|specs/README\.md|specs/_catalog(?![\w-]))",
    "tests": r"(?<![\w.-])tests(?:/|(?![\w.-]))",
    "src": r"(?<![\w.-])src(?:/|(?![\w.-]))",
    "switch": r"ALLOW_TEST_CHANGE",
}
WRITE_VERB = (
    r"(?:^|[;&|(`]\s*|\bxargs\s+|\bsudo\s+)"
    r"(?:sed\s[^;&|\n]*-\w*i|tee|mv|cp|rm|touch|truncate|ln|chmod|chown|install|rsync|dd|patch)\b"
)


# --- Bash: 書き込み先のパス（既存のテストへの書き込みを調べる） -----------------------------

_GUARDED_WORDS = (
    "tests",
    "conftest",
    "pyproject",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "req.md",
)
_REDIRECT_RE = re.compile(r"""(?<![<&])>{1,2}[ \t]*["']?([^\s"';&|<>]+)""")
_VERB_ARGS_RE = re.compile(rf"{WRITE_VERB}([^;&|\n]*)", re.MULTILINE)


MAX_SHELL_TARGET_TEXT = 200_000
MAX_TARGETS = 100
# 書き込み先を決められないときの印（`*` を含むので、決められない書き込み先として、拒否側に倒される）
UNRESOLVED_TARGET = "tests/*（大きすぎる・多すぎる・cd のあとの相対パス）"
_CD_TESTS_RE = re.compile(r"\b(?:cd|pushd)[ \t]+[\"']?(?:\./)?tests\b")


def _shell_targets(text: str) -> list[str]:
    """シェルのコマンドが書き込む（と判断できる）パスの文字列。リダイレクトの先、書き込み系のコマンドの引数。"""
    if not any(w in text for w in _GUARDED_WORDS):
        return []  # 守る対象に関係しない（巨大な入力で、無駄に調べない）
    if len(text) > MAX_SHELL_TARGET_TEXT:
        return [UNRESOLVED_TARGET]  # 大きすぎて、書き込み先を数えきれない
    found = [m.group(1) for m in _REDIRECT_RE.finditer(text)]
    for m in _VERB_ARGS_RE.finditer(text):
        try:
            words = shlex.split(m.group(1))
        except ValueError:
            words = m.group(1).split()
        for w in words:
            if not w.startswith("-"):
                found.append(w[3:] if w.startswith("of=") else w)
    # `$(sed -i … file)` や バッククォートの終わりの `)` ` を除き、重複を除く
    targets = list(dict.fromkeys(t.strip().strip("\"'").rstrip(")`;") for t in found))
    if len(targets) > MAX_TARGETS:
        return [UNRESOLVED_TARGET]
    if targets and _CD_TESTS_RE.search(text):
        targets.append(UNRESOLVED_TARGET)  # `cd tests` のあとの相対パスは、決められない
    return targets


def _exists_in_baseline(root: Path, rel: str, timeout: float) -> bool:
    """「既存」か。HEAD にあれば既存。git が使えないときは、ディスクにあれば既存とみなす（安全側）。"""
    try:
        paths = head_paths(root, timeout)
    except GitError:
        return (root / rel).exists()
    return paths is not None and rel in paths


_UNRESOLVED_TEST_RE = re.compile(
    r"(?:^|/)(?:tests(?:/|$)|conftest|pyproject\.toml|pytest\.ini|tox\.ini|setup\.cfg)|specs/\S*req\.md"
)


def bash_change_reason(targets: list[str], root: Path, timeout: float) -> str | None:
    """Bash 経由で、既存のテストファイルに書き込むコマンドなら、拒否する理由（まだ無いファイルは通す）。"""
    for raw in targets:
        t = raw.strip().strip("\"'")
        if not t:
            continue
        if any(c in t for c in "*?[${`"):
            if _UNRESOLVED_TEST_RE.search(t):  # glob や変数で、書き込み先を決められない
                return f"Bash 経由で、テストの書き込み先を決められないコマンドです（{t}）。追記は Edit ツールを使ってください。{CHANGE_HINT}"
            continue
        rel = rel_path(t, root)
        if rel is None:
            continue
        if rel == "tests" or (
            _guarded_kind(rel, root) is not None
            and _exists_in_baseline(root, rel, timeout)
        ):
            return f"Bash 経由で、既存のテスト・pytest の設定・実装中の req.md（{rel}）を書き換えるコマンドです。追記は Edit ツールを使ってください。{CHANGE_HINT}"
    return None
