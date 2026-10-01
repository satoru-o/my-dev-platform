#!/usr/bin/env python3
"""PreToolUse ガード。TDDの規律を機械で守る（ルールの正本は specs/README.md）。

1. 保護対象（.claude/**, CLAUDE.md, .github/**, specs/README.md, specs/_catalog/**）
   への書き込みは、`.claude/UNLOCK` が無い限り拒否する。UNLOCK は人間が手で置く
   （例: `! touch .claude/UNLOCK`）。編集が済んだら消す。
2. src/ への書き込みは、進行中のreq（status が planned / red / green）が無ければ拒否する。
3. tests/ への書き込みは、進行中のreqが無い、または status が red のものがあれば拒否する
   （red = 失敗するテストがあり、実装中。実装フェーズでは tests/ を触らない）。

Bash は、書き込みに見えるコマンドだけを見る「ベストエフォート」。完全な防御ではない。
  - heredoc: 受け取るのがデータだけ（cat、tee など）なら、本文は調べない（引用符なしなら、展開される
    `$(…)` とバッククォートだけ調べる。解析しきれないものは拒否）。bash や python など、実行するもの
    （知らないコマンドも含む）なら、本文を調べる。here-string（`<<<`）も同じ。
  - python: 書き込み先は、文字列リテラルか、リテラルを代入した変数から読む。代入が見えない変数は通す。
  - python 以外のインタプリタ（ruby、node など）: 丁寧には解析せず、「書き込み風の文字列」と
    「保護パスの文字列」が一緒にあれば拒否する（旧版と同じ。誤検出は残る。他の言語は将来の拡張）。
  - 巨大な入力で遅くならないこと（hook のタイムアウトは10秒。超えると素通りになる）が前提。
    入力量の2乗に比例する処理を入れない（test_guard.py の SLOW_CASES で確かめる）。
本当の壁は CODEOWNERS / ブランチ保護（M2）で作る。
想定外の例外は、安全側（拒否）に倒す。
"""

import ast
import bisect
import json
import os
import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROTECTED = (".claude", "CLAUDE.md", ".github", "specs/README.md", "specs/_catalog")
UNLOCK = ".claude/UNLOCK"
GIT_TIMEOUT_SECONDS = 5.0  # 「既存」の基準（HEAD）を取る git の、待つ時間の上限
ACTIVE = {"planned", "red", "green"}
WRITE_TOOLS = {
    "Edit": "file_path",
    "Write": "file_path",
    "NotebookEdit": "notebook_path",
}

# Bash 用。パスを表す正規表現（コマンド文字列の中から探す）
PATH_RE = {
    "protected": r"(?:\.claude(?![\w-])|CLAUDE\.md|\.github(?![\w-])|specs/README\.md|specs/_catalog(?![\w-]))",
    "tests": r"(?<![\w.-])tests(?:/|(?![\w.-]))",
    "src": r"(?<![\w.-])src(?:/|(?![\w.-]))",
}
WRITE_VERB = (
    r"(?:^|[;&|(]\s*|\bxargs\s+|\bsudo\s+)"
    r"(?:sed\s[^;&|\n]*-\w*i|tee|mv|cp|rm|touch|truncate|ln|chmod|chown|install|rsync|dd|patch)\b"
)

# heredoc（`<<`）。here-string（`<<<`）は含めない。
HEREDOC_RE = re.compile(
    r"(?<!<)<<(?!<)(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|(\\?)([A-Za-z_][\w.-]*))"
)
HERESTRING_RE = re.compile(r"<<<[ \t]*(?:\"([^\"\n]*)\"|'([^'\n]*)'|([^\s;&|<>]*))")
PYTHON_WORD_RE = re.compile(r"(?<![\w./-])python[\d.]*(?![\w.-])")
# python 以外のインタプリタ。丁寧には解析せず、旧版と同じ粗い判定にとどめる（Q9）。
# 他の言語（TypeScript など）を使うようになったら、拡張として別の要望で検討する。
OTHER_INTERPRETER_RE = re.compile(
    r"(?<![\w./-])(?:ruby|node|nodejs|perl|php|lua|deno|bun)(?![\w.-])"
)
# 書き込み風の文字列。`open(` の先読みは、巨大な入力で遅くならないよう、長さを区切る。
GENERIC_WRITE_RE = re.compile(
    r"""write_text|write_bytes|\.write\(|\bopen\([^)]{0,500}?["'][wax+]"""
)


def statuses(root: Path) -> list[str]:
    result = []
    for p in sorted((root / "specs").glob("[0-9][0-9][0-9][0-9]-*/status.md")):
        for line in p.read_text(encoding="utf-8").splitlines()[:30]:
            m = re.match(r"status:\s*([a-z]+)", line)
            if m:
                result.append(m.group(1))
                break
    return result


def rel_path(path: str, root: Path) -> str | None:
    """プロジェクト内の相対パス（posix）。プロジェクトの外なら None。"""
    full = os.path.normpath(os.path.join(root, path))
    try:
        return Path(full).relative_to(root).as_posix()
    except ValueError:
        return None


def kind_of(rel: str) -> str | None:
    for p in PROTECTED:
        if rel == p or rel.startswith(p + "/"):
            return "protected"
    for name in ("tests", "src"):
        if rel == name or rel.startswith(name + "/"):
            return name
    return None


def deny_reason(kind: str, root: Path) -> str | None:
    """拒否する理由。通してよければ None。"""
    if kind == "protected":
        if (root / UNLOCK).exists():
            return None
        return (
            "保護対象（.claude/**、CLAUDE.md、.github/**、specs/README.md、specs/_catalog/**）は"
            "人間の承認なしに編集できません。人間に提案してください。"
            "編集を承認する場合は、人間が `! touch .claude/UNLOCK` を実行し、編集後に削除します。"
        )
    sts = statuses(root)
    if kind == "src":
        if ACTIVE & set(sts):
            return None
        return (
            "進行中のreq（status が planned / red / green）がありません。"
            "src/ はreqなしに編集できません。`/req-new` で要望を起こすか、"
            "`/req-run` / `/req-fb` で進めてください。挙動が変わらない変更（chore）なら src/ には触れません。"
        )
    if kind == "tests":
        if "red" in sts:
            return (
                "status が red のreqがあります。実装フェーズでは tests/ を書き換えません"
                "（整形も含む）。テストを直す必要があれば、discussion-log.md で人間に聞いてください。"
            )
        if not ACTIVE & set(sts):
            return (
                "進行中のreq（status が planned / green）がありません。"
                "tests/ はreqなしに編集できません。`/req-new` / `/req-run` / `/req-fb` で進めてください。"
            )
    return None


# --- 既存テストを黙って書き換えさせない（0007） -------------------------------------
# 「既存」の基準は、最後にコミットした内容（HEAD）。足すのは自由。変える・弱める・消すは拒否する。

SKIP_NAMES = {"skip", "skipif", "xfail"}
CHANGE_HINT = (
    "足すのは自由です。承認する場合は、人間が `! touch .claude/ALLOW_TEST_CHANGE` を実行します"
    "（1回使うと消えます。承認した変更は、すぐコミットしてください）。"
)


class GitError(Exception):
    """「既存」の基準（HEAD）が取れない。呼び出し側は、拒否側に倒す。"""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    # 作業フォルダを固定し、GIT_ で始まる環境変数（GIT_DIR など）を掃除して呼ぶ。
    # 別のリポジトリを「基準」にされて、すべて新規として通ってしまうのを防ぐ。
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "--no-pager", *args],  # noqa: S607
            capture_output=True,
            cwd=root,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise GitError("git が時間内に答えない") from e
    except OSError as e:
        raise GitError(f"git を実行できない（{type(e).__name__}）") from e


def head_content(root: Path, rel: str) -> str | None:
    """HEAD にあるファイルの内容。HEAD に無い（新規）、コミットが0件なら None。

    基準が取れなければ GitError。「コミット0件」と「git の失敗」は、別に判定する。
    """
    has_head = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if has_head.returncode == 1 and not has_head.stdout.strip():
        return None  # コミットが0件: すべて新規として扱う
    if has_head.returncode != 0:
        raise GitError("git rev-parse が失敗した（リポジトリではない、など）")
    tree = _git(root, "ls-tree", "-z", "HEAD", "--", rel)
    if tree.returncode != 0:
        raise GitError("git ls-tree が失敗した")
    if not tree.stdout:
        return None  # HEAD に無い: 新規
    meta = tree.stdout.split(b"\t", 1)[0].decode("utf-8", "replace").split()
    if len(meta) < 3 or meta[1] != "blob":
        return None
    blob = _git(root, "cat-file", "blob", meta[2])
    if blob.returncode != 0:
        raise GitError("git cat-file が失敗した")
    return blob.stdout.decode("utf-8", "replace")


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


def python_change_reason(base_src: str | None, new_src: str) -> str | None:
    """テストファイルの、HEAD からの変更が「足すだけ」でなければ、その理由。足すだけなら None。"""
    if base_src is None or base_src == new_src:
        return None  # 新規、または変更なし
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


def _is_test_py(rel: str) -> bool:
    return (rel.startswith("tests/") and rel.endswith(".py")) or rel == "conftest.py"


def _new_content(tool_name: str, tool_input: dict, path: Path) -> str | None:
    """Edit・Write が成功したときの、ファイルの内容。内容の情報が無ければ None。"""
    if tool_name == "Write":
        content = tool_input.get("content")
        return content if isinstance(content, str) else None
    old, new = tool_input.get("old_string"), tool_input.get("new_string")
    if not isinstance(old, str) or not isinstance(new, str) or not old:
        return None
    try:
        current = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if old not in current:
        return None  # Edit 自体が失敗する
    return (
        current.replace(old, new)
        if tool_input.get("replace_all")
        else current.replace(old, new, 1)
    )


def change_reason(tool_name: str, tool_input: dict, root: Path, rel: str) -> str | None:
    """Edit・Write が、既存のテストを黙って変えるものなら、拒否する理由。"""
    if not _is_test_py(rel):
        return None
    new_src = _new_content(tool_name, tool_input, root / rel)
    if new_src is None:
        return None
    try:
        why = python_change_reason(head_content(root, rel), new_src)
    except GitError as e:
        return (
            f"「既存」の基準（HEAD）が取れないため、拒否しました（{e}）。{CHANGE_HINT}"
        )
    if why is None:
        return None
    return f"既存のテストを変える・弱める・消す変更です（{why}）。{CHANGE_HINT}"


# --- Bash: heredoc の解析 -----------------------------------------------------


@dataclass
class Heredoc:
    """heredoc 1つ分。body は本文（終了行は含まない）。"""

    receiver: str  # `<<` を含む1行。受け取るコマンドの判定に使う
    line_no: int  # receiver が、コマンドの何行目か
    seg: tuple[
        int, int
    ]  # receiver のうち、`<<` を含むコマンド列の範囲（`;` `&&` `||` `&` の区切りの間）
    quoted: bool  # 区切り語が引用符（`'EOF'`、`"EOF"`、`\EOF`）つき。本文は展開されない
    body: str


def split_heredocs(command: str) -> tuple[str, list[Heredoc]]:
    """コマンドを、本文を除いたシェルの文と、heredoc の一覧に分ける。

    終了行は、`<<` なら行全体が区切り語と等しいとき、`<<-` なら行頭のタブを除いて等しいとき。
    空白つきの `EOF` などは終了行にならない（シェルの規則どおり）。閉じていなければ末尾まで本文。
    """
    lines = command.split("\n")
    shell: list[str] = []
    docs: list[Heredoc] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        line_no = i
        shell.append(line)
        i += 1
        matches = list(HEREDOC_RE.finditer(line))
        bounds = _separator_bounds(line) if matches else ([], [])
        for m in matches:
            dash = bool(m.group(1))
            delim = m.group(2) or m.group(3) or m.group(5)
            body: list[str] = []
            while i < len(lines):
                cur = lines[i]
                i += 1
                if (cur.lstrip("\t") if dash else cur) == delim:
                    break
                body.append(cur)
            quoted = (
                m.group(2) is not None or m.group(3) is not None or bool(m.group(4))
            )
            docs.append(
                Heredoc(
                    receiver=line,
                    line_no=line_no,
                    seg=_segment_bounds(bounds, len(line), m.start()),
                    quoted=quoted,
                    body="\n".join(body),
                )
            )
    return "\n".join(shell), docs


# データとして受け取るだけのコマンド。これ以外（bash、python、不明なもの）は、本文を実行するものとして扱う。
DATA_RECEIVERS = {"cat", "tee", "head", "tail", "wc", "sort", "uniq", "grep", "diff"}
DATA_GIT_SUBCOMMANDS = {"commit", "tag"}  # `git commit -F -` のメッセージなど
_SEP_RE = re.compile(r";|&&|\|\||&")
_WRAPPERS = {"sudo", "env", "exec", "time", "nohup", "command", "builtin"}


def _separator_bounds(line: str) -> tuple[list[int], list[int]]:
    """区切り（`;` `&&` `||` `&`）の、始まりの位置の一覧と、終わりの位置の一覧。"""
    spans = [m.span() for m in _SEP_RE.finditer(line)]
    return [s for s, _ in spans], [e for _, e in spans]


def _segment_bounds(
    bounds: tuple[list[int], list[int]], length: int, pos: int
) -> tuple[int, int]:
    """pos を含む1つのコマンド列の範囲。1行に `<<` が大量にあっても、遅くならないよう二分探索する。"""
    starts, ends = bounds
    i = bisect.bisect_right(ends, pos)
    j = bisect.bisect_left(starts, pos)
    return (ends[i - 1] if i else 0), (starts[j] if j < len(starts) else length)


def _is_data_command(command: str) -> bool:
    words = command.split()
    while words and (re.fullmatch(r"\w+=\S*", words[0]) or words[0] in _WRAPPERS):
        words.pop(0)
    if not words:
        return False
    name = posixpath.basename(words[0])
    if name == "git":
        rest = [w for w in words[1:] if not w.startswith("-")]
        return bool(rest) and rest[0] in DATA_GIT_SUBCOMMANDS
    return name in DATA_RECEIVERS


def segment_is_data_only(segment: str) -> bool:
    """heredoc の本文が、実行されず、データとして書かれるだけか（`<<` を含むコマンド列で判定する）。

    パイプでつながったすべてのコマンドが、データを受けるだけのものであること。
    判定できなければ（知らないコマンドがあれば）、実行されるものとして扱う（安全側）。
    """
    return all(_is_data_command(c) for c in segment.split("|"))


MAX_SUBSTITUTION_DEPTH = 10


def expansions(body: str) -> tuple[list[str], bool]:
    """引用符なしの heredoc の本文のうち、展開されて実行される部分（`$(…)` とバッククォート）。

    戻り値は、その中身の一覧と、解析しきれたかどうか。閉じていない、入れ子が深すぎるものは、
    解析しきれなかったものとして扱う（呼び出し側が、拒否側に倒す）。
    """
    units: list[str] = []
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == "\\":
            i += 2
        elif body.startswith("$(", i):
            arithmetic = body.startswith("$((", i)
            depth, j = 1, i + 2
            while j < n and depth > 0:
                ch = body[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "(":
                    depth += 1
                    if depth > MAX_SUBSTITUTION_DEPTH:
                        return units, False
                elif ch == ")":
                    depth -= 1
                j += 1
            if depth != 0:
                return units, False
            if not arithmetic:
                units.append(body[i + 2 : j - 1])
            i = j
        elif c == "`":
            j = i + 1
            while j < n and body[j] != "`":
                j += 2 if body[j] == "\\" else 1
            if j >= n:
                return units, False
            units.append(body[i + 1 : j])
            i = j + 1
        else:
            i += 1
    return units, True


# --- Bash: python の書き込み先の判定 -------------------------------------------

_STR = r"""(?:'([^'\n]*)'|"([^"\n]*)")"""
_ARG = rf"""\s*(?:{_STR}|([A-Za-z_]\w*))"""
_ASSIGN_RE = re.compile(rf"""\b([A-Za-z_]\w*)\s*=\s*(?:Path\(\s*)?{_STR}""")
_OPEN_RE = re.compile(
    rf"""\bopen\({_ARG}\s*(?:,\s*(?:mode\s*=\s*)?['"]([^'"\n]*)['"])?"""
)
_PATH_WRITE_RE = re.compile(
    rf"""\bPath\({_ARG}\s*\)\s*\.\s*(?:write_text|write_bytes)\b"""
)
_VAR_WRITE_RE = re.compile(r"""\b([A-Za-z_]\w*)\s*\.\s*(?:write_text|write_bytes)\b""")
_FUNC_RE = re.compile(
    rf"""\b(?:shutil\.(?:copy|copy2|copyfile|move|rmtree)|os\.(?:remove|rename|replace|unlink))\({_ARG}(?:\s*,{_ARG})?"""
)


def _path_kind(path: str, root: Path) -> str | None:
    rel = rel_path(path, root)
    return kind_of(rel) if rel is not None else None


def python_kinds(code: str, root: Path) -> set[str]:
    """python のコードが書き込む（と判断できる）パスの種類。

    書き込み先は、文字列リテラルか、リテラルを代入した変数から読む。
    代入が見えない変数（`p=sys.argv[1]` など）は、判断できないので通す（ベストエフォート）。
    """
    assigns: dict[str, str] = {}
    for m in _ASSIGN_RE.finditer(code):
        assigns[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)

    def resolve(single: str | None, double: str | None, ident: str | None):
        if single is not None:
            return single
        if double is not None:
            return double
        return assigns.get(ident or "")

    targets: list[str | None] = []
    for m in _OPEN_RE.finditer(code):
        mode = m.group(4)
        if mode and set(mode) & set("wax+"):
            targets.append(resolve(m.group(1), m.group(2), m.group(3)))
    for m in _PATH_WRITE_RE.finditer(code):
        targets.append(resolve(m.group(1), m.group(2), m.group(3)))
    for m in _VAR_WRITE_RE.finditer(code):
        targets.append(assigns.get(m.group(1)))
    for m in _FUNC_RE.finditer(code):
        targets.append(resolve(m.group(1), m.group(2), m.group(3)))
        targets.append(resolve(m.group(4), m.group(5), m.group(6)))

    kinds: set[str] = set()
    for t in targets:
        if t:
            kind = _path_kind(t, root)
            if kind:
                kinds.add(kind)
    return kinds


# --- Bash: 判定 -------------------------------------------------------------------


def _legacy_kinds(text: str) -> list[str]:
    """書き込みに見えるシェルのコマンドが触れるパスの種類（ベストエフォート）。"""
    kinds = []
    for kind, path in PATH_RE.items():
        # `>` を語に含めない（`>>>>…` のような入力で、各 `>` から末尾まで読んで、遅くならないように）
        redirect = rf">>?\s*[\"']?(?:[^\s\"';&|>]*/)?{path}"
        verb = rf"{WRITE_VERB}[^;&|\n]*{path}"
        if re.search(redirect, text) or re.search(verb, text, re.MULTILINE):
            kinds.append(kind)
    return kinds


def bash_kinds(command: str, root: Path) -> list[str]:
    """書き込みに見えるコマンドが触れるパスの種類（ベストエフォート）。"""
    shell, docs = split_heredocs(command)
    shell_parts = [shell]
    kinds: set[str] = set()
    # 受け取るコマンドの判定は、1行に `<<` が大量にあっても、同じコマンド列につき1回だけ行う
    receivers: dict[tuple, tuple[bool, bool]] = {}

    def receiver(key: tuple, line: str, seg: tuple[int, int]) -> tuple[bool, bool]:
        """（python か、データを受けるだけか）"""
        if key not in receivers:
            segment = line[seg[0] : seg[1]]
            receivers[key] = (
                bool(PYTHON_WORD_RE.search(segment)),
                segment_is_data_only(segment),
            )
        return receivers[key]

    for d in docs:
        is_python, data_only = receiver(("doc", d.line_no, d.seg), d.receiver, d.seg)
        if is_python:
            # python の本文は、書き込み先で判定する
            kinds |= python_kinds(d.body, root)
        elif not data_only:
            # 実行されうる本文は、シェルのコマンドとして調べる
            shell_parts.append(d.body)
        elif not d.quoted:
            # データでも、引用符なしなら、展開される部分は実行される
            units, parsed = expansions(d.body)
            for unit in units:
                kinds |= set(_legacy_kinds(unit))
            if not parsed:
                # 解析しきれないものは、拒否側に倒す
                kinds.add("protected")
    shell = "\n".join(shell_parts)

    # here-string（`<<<`）も、受け取るのがデータだけでなければ、中身が実行される
    for line_no, line in enumerate(shell.split("\n")):
        if "<<<" not in line:
            continue
        bounds = _separator_bounds(line)
        for m in HERESTRING_RE.finditer(line):
            seg = _segment_bounds(bounds, len(line), m.start())
            is_python, data_only = receiver(("hs", line_no, seg), line, seg)
            if data_only:
                continue
            content = next(g for g in m.groups() if g is not None)
            if is_python or PYTHON_WORD_RE.search(content):
                kinds |= python_kinds(content, root)
            kinds |= set(_legacy_kinds(content))

    if PYTHON_WORD_RE.search(shell):
        # `python3 -c "…"` など。書き込み先で判定する
        kinds |= python_kinds(shell, root)
    if OTHER_INTERPRETER_RE.search(shell) and GENERIC_WRITE_RE.search(shell):
        # python 以外は、書き込み風の文字列と保護パスの文字列が一緒にあれば、そのパスに書くものとみなす
        kinds |= {k for k, path in PATH_RE.items() if re.search(path, shell)}
    kinds |= set(_legacy_kinds(shell))
    return [k for k in PATH_RE if k in kinds]


def decide(tool_name: str, tool_input: dict, root: Path) -> str | None:
    """拒否する理由。通してよければ None。"""
    if tool_name in WRITE_TOOLS:
        path = tool_input.get(WRITE_TOOLS[tool_name])
        if not path:
            return None
        rel = rel_path(str(path), root)
        kind = kind_of(rel) if rel is not None else None
        reason = deny_reason(kind, root) if kind else None
        if reason or rel is None or tool_name not in ("Edit", "Write"):
            return reason
        return change_reason(tool_name, tool_input, root, rel)
    if tool_name == "Bash":
        for kind in bash_kinds(str(tool_input.get("command", "")), root):
            reason = deny_reason(kind, root)
            if reason:
                return reason
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        )
        reason = decide(
            payload.get("tool_name", ""),
            payload.get("tool_input") or {},
            root.resolve(),
        )
    except Exception as e:  # 安全側（拒否）に倒す
        reason = f"ガードの内部エラーのため拒否しました: {type(e).__name__}: {e}"
    if reason:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
