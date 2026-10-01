#!/usr/bin/env python3
"""PreToolUse ガード。TDDの規律を機械で守る（ルールの正本は specs/README.md）。

1. 保護対象（.claude/**, CLAUDE.md, .github/**, specs/README.md, specs/_catalog/**）
   への書き込みは、`.claude/UNLOCK` が無い限り拒否する。UNLOCK は人間が手で置く
   （例: `! touch .claude/UNLOCK`）。編集が済んだら消す。
2. src/ への書き込みは、進行中のreq（status が planned / red / green）が無ければ拒否する。
3. tests/ への書き込みは、進行中のreqが無い、または status が red のものがあれば拒否する
   （red = 失敗するテストがあり、実装中。実装フェーズでは tests/ を触らない）。
4. 既存のテスト（tests/ の既存の Python ファイル、conftest.py）、pytest の設定（pyproject.toml の
   `[tool.pytest]`、pytest.ini、tox.ini、setup.cfg）、実装中の req.md の AC の表は、「足すのは自由、
   変える・弱める・消すは拒否」（0007）。「既存」の基準は、最後にコミットした内容（HEAD）。
   - テスト: ASTで HEAD と比べる。assert・期待値・本文の文・デコレータが消える、変わる、同名の定義が
     増える、skip / xfail が増える、構文エラーになる、は拒否。parametrize の値を足すのは通す。
   - Bash 経由の、既存のファイルへの書き込みは拒否（まだ無いファイルは通す）。追記は Edit を使う。
   - git: HEAD を動かす・書き換える操作（amend、rebase、reset --hard、reset <コミット>）は常に拒否。
     守る対象を戻す・消す操作（checkout --、restore、rm、mv）は、そのパスに触れるときだけ拒否。
   - 解除: 人間が `! touch .claude/ALLOW_TEST_CHANGE` を置く。AI は作れない（UNLOCK があっても）。
     スイッチが無ければ拒否される変更を通したときだけ、1回で消える。履歴を動かす操作は通せない。
   - HEAD が取れないとき: コミット0件ならすべて新規。git の失敗・タイムアウトは拒否。git は、作業
     フォルダを固定し、GIT_ で始まる環境変数を掃除して呼ぶ。
   - 大きなファイル（合計60万文字超）は、足すだけの追記に限って、正規表現で調べる（AST は遅い）。

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

import json
import os
import posixpath
import re
import shlex
import sys
from pathlib import Path

from guardlib.changes import CHANGE_HINT, _with_switch, change_reason
from guardlib.gitbase import _head_paths_cache
from guardlib.heredoc import (
    _WRAPPERS,
    HERESTRING_RE,
    _segment_bounds,
    _separator_bounds,
    expansions,
    segment_is_data_only,
    split_heredocs,
)
from guardlib.paths import WRITE_TOOLS, active_req_dirs, deny_reason, kind_of, rel_path
from guardlib.pywrites import python_kinds, python_targets
from guardlib.shellwrites import PATH_RE, WRITE_VERB, _shell_targets, bash_change_reason

GIT_TIMEOUT_SECONDS = 5.0  # 「既存」の基準（HEAD）を取る git の、待つ時間の上限


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


# --- 既存テストを黙って書き換えさせない（0007） -------------------------------------
# 「既存」の基準は、最後にコミットした内容（HEAD）。足すのは自由。変える・弱める・消すは拒否する。


# --- pytest の設定と、req.md の AC の表 -------------------------------------------------


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
    return _bash_scan(command, root)[0]


def _bash_scan(command: str, root: Path) -> tuple[list[str], list[str], str]:
    """（書き込みに見えるコマンドが触れるパスの種類、書き込み先のパスの文字列、調べたシェルの文）。ベストエフォート。"""
    shell, docs = split_heredocs(command)
    shell_parts = [shell]
    kinds: set[str] = set()
    targets: list[str] = []
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
            targets += python_targets(d.body)
        elif not data_only:
            # 実行されうる本文は、シェルのコマンドとして調べる
            shell_parts.append(d.body)
        elif not d.quoted:
            # データでも、引用符なしなら、展開される部分は実行される
            units, parsed = expansions(d.body)
            for unit in units:
                kinds |= set(_legacy_kinds(unit))
                targets += _shell_targets(unit)
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
                targets += python_targets(content)
            kinds |= set(_legacy_kinds(content))
            targets += _shell_targets(content)

    if PYTHON_WORD_RE.search(shell):
        # `python3 -c "…"` など。書き込み先で判定する
        kinds |= python_kinds(shell, root)
        targets += python_targets(shell)
    if OTHER_INTERPRETER_RE.search(shell) and GENERIC_WRITE_RE.search(shell):
        # python 以外は、書き込み風の文字列と保護パスの文字列が一緒にあれば、そのパスに書くものとみなす
        kinds |= {k for k, path in PATH_RE.items() if re.search(path, shell)}
    kinds |= set(_legacy_kinds(shell))
    targets += _shell_targets(shell)
    return [k for k in PATH_RE if k in kinds], targets, shell


def decide(tool_name: str, tool_input: dict, root: Path) -> str | None:
    """拒否する理由。通してよければ None。"""
    _head_paths_cache.clear()
    timeout = GIT_TIMEOUT_SECONDS
    if tool_name in WRITE_TOOLS:
        path = tool_input.get(WRITE_TOOLS[tool_name])
        if not path:
            return None
        rel = rel_path(str(path), root)
        kind = kind_of(rel) if rel is not None else None
        reason = deny_reason(kind, root) if kind else None
        if reason or rel is None or tool_name not in ("Edit", "Write"):
            return reason
        return _with_switch(
            change_reason(tool_name, tool_input, root, rel, timeout), root
        )
    if tool_name == "Bash":
        kinds, targets, shell = _bash_scan(str(tool_input.get("command", "")), root)
        for kind in kinds:
            reason = deny_reason(kind, root)
            if reason:
                return reason
        git_why, git_switchable = git_reason(shell, root)
        if git_why and not git_switchable:
            return git_why  # 履歴を動かす操作は、スイッチでは通さない
        # 守る対象の変更は、スイッチがあれば、1回だけ通す（複数あっても、1回で足りる）
        return _with_switch(git_why or bash_change_reason(targets, root, timeout), root)
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
