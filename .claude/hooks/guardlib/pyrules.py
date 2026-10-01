"""テスト（Python）と pytest の設定の、AST による比較。入力は旧・新の文字列だけ（純粋関数）。"""

import ast
import configparser
import posixpath
import re
import tomllib

SKIP_NAMES = {"skip", "skipif", "xfail"}


def _assigned_names(node: ast.stmt) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]  # type: ignore[attr-defined]
    return [t.id for t in targets if isinstance(t, ast.Name)]


def _is_skip(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr in SKIP_NAMES
    return isinstance(node, ast.Name) and node.id in SKIP_NAMES


class _Model:
    """テストファイルの、比べるための見取り図。"""

    def __init__(self, src: str) -> None:
        tree = ast.parse(src)
        self.defs: dict[
            str, list[ast.stmt]
        ] = {}  # 修飾名（`Class::method`）→ 定義の一覧
        self.top: list[str] = []  # モジュール直下の、定義でない文（import、定数など）
        self.skips = sum(1 for n in ast.walk(tree) if _is_skip(n))
        self._walk(tree.body, "")

    def _walk(self, body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.defs.setdefault(prefix + node.name, []).append(node)
                if isinstance(node, ast.ClassDef):
                    self._walk(node.body, prefix + node.name + "::")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for name in _assigned_names(node):
                    self.defs.setdefault(prefix + name, []).append(
                        node
                    )  # 代入での上書きも「定義」
                if not prefix:
                    self.top.append(ast.dump(node))
            elif not prefix:
                self.top.append(ast.dump(node))


def _is_subsequence(small: list[str], big: list[str]) -> bool:
    it = iter(big)
    return all(x in it for x in small)


def _is_parametrize(d: ast.expr) -> bool:
    return isinstance(d, ast.Call) and getattr(d.func, "attr", None) == "parametrize"


def _param_extends(b: ast.Call, n: ast.Call) -> bool:
    """parametrize の値のリストに、値を足すだけ（元の値は、順序も含めて残る）なら True。"""
    if len(b.args) != len(n.args) or len(b.args) < 2:
        return ast.dump(b) == ast.dump(n)
    for i, (x, y) in enumerate(zip(b.args, n.args, strict=True)):
        if (
            i == 1
            and isinstance(x, (ast.List, ast.Tuple))
            and isinstance(y, (ast.List, ast.Tuple))
        ):
            if not _is_subsequence(
                [ast.dump(e) for e in x.elts], [ast.dump(e) for e in y.elts]
            ):
                return False
        elif ast.dump(x) != ast.dump(y):
            return False
    return [ast.dump(k) for k in b.keywords] == [ast.dump(k) for k in n.keywords]


def _compare_def(base: ast.stmt, new: ast.stmt) -> str | None:
    if type(base) is not type(new):
        return "別の種類の定義に置き換わった"
    if isinstance(base, (ast.Assign, ast.AnnAssign)):
        return None if ast.dump(base) == ast.dump(new) else "代入の内容が変わった"
    assert isinstance(base, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    assert isinstance(new, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    base_params = [d for d in base.decorator_list if _is_parametrize(d)]
    new_params = [d for d in new.decorator_list if _is_parametrize(d)]
    base_others = [ast.dump(d) for d in base.decorator_list if not _is_parametrize(d)]
    new_others = [ast.dump(d) for d in new.decorator_list if not _is_parametrize(d)]
    if not _is_subsequence(base_others, new_others):
        return "デコレータが変わった・消えた"
    if len(new_params) < len(base_params):
        return "parametrize が消えた"
    for b, n in zip(base_params, new_params, strict=False):
        if not _param_extends(b, n):  # type: ignore[arg-type]
            return "parametrize の値が変わった・消えた"
    if isinstance(base, ast.ClassDef) and isinstance(new, ast.ClassDef):
        bases = [ast.dump(x) for x in (*base.bases, *base.keywords)]
        if bases != [ast.dump(x) for x in (*new.bases, *new.keywords)]:
            return "基底クラスが変わった"
        return None
    if isinstance(base, ast.ClassDef) or isinstance(new, ast.ClassDef):
        return "別の種類の定義に置き換わった"
    if ast.dump(base.args) != ast.dump(new.args):
        return "引数が変わった"
    if not _is_subsequence(
        [ast.dump(s) for s in base.body], [ast.dump(s) for s in new.body]
    ):
        return "本文の assert や文が、変わった・消えた"
    return None


# 大きなファイルは、AST の解析だけで数秒かかる（2.7MB で、parse だけで1.7秒。hook のタイムアウトは10秒）。
# 合計がこの文字数を超えるものは、足すだけの追記（元の内容で始まり、末尾に足す）に限って、AST を使わず、
# 正規表現で調べる（skip / xfail の語、HEAD と同名の定義）。それ以外は、解析しきれないものとして拒否する。
BIG_FILE_LIMIT = 600_000
_TOP_NAME_RE = re.compile(
    r"^(?:async[ \t]+def|def|class)[ \t]+(\w+)|^(\w+)[ \t]*(?::[^=\n]*)?=(?!=)",
    re.MULTILINE,
)
_SKIP_WORD_RE = re.compile(r"\b(?:skip|skipif|xfail)\b")
_FIRST_LINE_INDENT_RE = re.compile(r"^([ \t]*)\S", re.MULTILINE)


def _big_file_reason(base_src: str, new_src: str) -> str | None:
    why_big = "大きすぎて、AST では解析しきれない"
    if not new_src.startswith(base_src) or not base_src.endswith("\n"):
        return f"{why_big}（足すだけの追記ではない）ため、拒否側に倒した"
    tail = new_src[len(base_src) :]
    first = _FIRST_LINE_INDENT_RE.search(tail)
    if first and first.group(1):
        return f"{why_big}（既存のブロックの中への追記）ため、拒否側に倒した"
    if _SKIP_WORD_RE.search(tail):
        return "skip / xfail を足す変更"
    base_names = {m.group(1) or m.group(2) for m in _TOP_NAME_RE.finditer(base_src)}
    for m in _TOP_NAME_RE.finditer(tail):
        name = m.group(1) or m.group(2)
        if name in base_names:
            return f"`{name}` と同名の定義が、HEAD より増えた（あとの定義が、前を上書きする）"
    return None


def python_change_reason(base_src: str | None, new_src: str) -> str | None:
    """テストファイルの、HEAD からの変更が「足すだけ」でなければ、その理由。足すだけなら None。"""
    if base_src is None or base_src == new_src:
        return None  # 新規、または変更なし
    if len(base_src) + len(new_src) > BIG_FILE_LIMIT:
        return _big_file_reason(base_src, new_src)
    try:
        base, new = _Model(base_src), _Model(new_src)
    except (SyntaxError, ValueError, RecursionError):
        return "解析しきれない（構文エラーなど）ため、拒否側に倒した"
    if new.skips > base.skips:
        return "skip / xfail を足す変更"
    if not _is_subsequence(base.top, new.top):
        return "モジュール直下の文（import、定数、pytestmark など）が、変わった・消えた"
    for name, base_nodes in base.defs.items():
        new_nodes = new.defs.get(name, [])
        if len(new_nodes) < len(base_nodes):
            return f"`{name}` の定義が、消えた"
        if len(new_nodes) > len(base_nodes):
            return f"`{name}` と同名の定義が、HEAD より増えた（あとの定義が、前を上書きする）"
        for b, n in zip(base_nodes, new_nodes, strict=True):
            why = _compare_def(b, n)
            if why:
                return f"`{name}`: {why}"
    return None


PYTEST_CONFIG_FILES = {"pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"}
# conftest.py に足すと、テストを外せてしまう名前
CONFTEST_CONFIG_NAMES = {
    "collect_ignore",
    "collect_ignore_glob",
    "pytest_ignore_collect",
    "pytest_collection_modifyitems",
}


def _pytest_config(rel: str, src: str) -> object:
    name = posixpath.basename(rel)
    if name == "pyproject.toml":
        return tomllib.loads(src).get("tool", {}).get("pytest")
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.read_string(src)
    if name == "pytest.ini":
        return {s: dict(cp[s]) for s in cp.sections()}
    wanted = ["pytest"] if name == "tox.ini" else ["tool:pytest", "pytest"]
    return {s: dict(cp[s]) for s in wanted if cp.has_section(s)}


def pytest_config_reason(rel: str, base_src: str | None, new_src: str) -> str | None:
    if base_src is None or base_src == new_src:
        return None
    try:
        same = _pytest_config(rel, base_src) == _pytest_config(rel, new_src)
    except (tomllib.TOMLDecodeError, configparser.Error, ValueError):
        return "解析しきれない（構文エラーなど）ため、拒否側に倒した"
    return None if same else "pytest の設定が、変わった・消えた"


def conftest_config_reason(base_src: str | None, new_src: str) -> str | None:
    """conftest.py に、テストを外せる名前（collect_ignore など）を、新しく足していないか。"""
    try:
        new_names = set(_Model(new_src).defs) & CONFTEST_CONFIG_NAMES
        base_names = set(_Model(base_src).defs) if base_src is not None else set()
    except (SyntaxError, ValueError, RecursionError):
        return "解析しきれない（構文エラーなど）ため、拒否側に倒した"
    added = new_names - base_names
    if added:
        return f"テストを外せる設定（{', '.join(sorted(added))}）を、足す変更"
    return None
