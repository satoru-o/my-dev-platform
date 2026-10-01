"""guard.py のテスト。「止めるべきものが止まり、通すべきものが通る」ことを確かめる。"""

import json
import os
import subprocess
import sys
from pathlib import Path

import guard
import pytest

GUARD = Path(__file__).with_name("guard.py")


def make_project(
    tmp_path: Path, statuses: dict[str, str] | None = None, unlock: bool = False
) -> Path:
    for name, status in (statuses or {}).items():
        d = tmp_path / "specs" / name
        d.mkdir(parents=True)
        (d / "status.md").write_text(
            f"---\nid: 0\nstatus: {status} # comment\n---\n", encoding="utf-8"
        )
    if unlock:
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "UNLOCK").write_text("", encoding="utf-8")
    return tmp_path.resolve()


def edit(root: Path, path: str, tool: str = "Edit") -> str | None:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return guard.decide(tool, {key: path}, root)


def bash(root: Path, command: str) -> str | None:
    return guard.decide("Bash", {"command": command}, root)


# --- 保護対象 ---------------------------------------------------------------

PROTECTED_PATHS = [
    ".claude/settings.json",
    ".claude/hooks/guard.py",
    ".claude/skills/req-run/SKILL.md",
    ".claude/UNLOCK",
    "CLAUDE.md",
    ".github/workflows/ci.yml",
    "specs/README.md",
    "specs/_catalog/viewpoints.md",
]


@pytest.mark.parametrize("path", PROTECTED_PATHS)
@pytest.mark.parametrize("tool", ["Edit", "Write", "NotebookEdit"])
def test_保護対象はUNLOCKが無ければ拒否する(tmp_path, path, tool):
    root = make_project(tmp_path, {"0001-a": "green"})
    assert edit(root, str(root / path), tool) is not None


@pytest.mark.parametrize("path", PROTECTED_PATHS)
def test_保護対象はUNLOCKがあれば通す(tmp_path, path):
    root = make_project(tmp_path, unlock=True)
    assert edit(root, str(root / path)) is None


def test_UNLOCKがあってもsrcとtestsの規則は緩まない(tmp_path):
    root = make_project(tmp_path, {"0001-a": "done"}, unlock=True)
    assert edit(root, str(root / "src/a.py")) is not None
    assert edit(root, str(root / "tests/test_a.py")) is not None


def test_dotdotで保護対象に回り込んでも拒否する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green"})
    assert edit(root, str(root / "src/../CLAUDE.md")) is not None
    assert edit(root, "src/../../elsewhere/x") is None  # プロジェクトの外は対象外


def test_相対パスもプロジェクト基準で判定する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green"})
    assert edit(root, "CLAUDE.md") is not None
    assert edit(root, "docs/CHARTER.md") is None


# --- src/ -------------------------------------------------------------------


@pytest.mark.parametrize("status", ["planned", "red", "green"])
def test_srcは進行中のreqがあれば通す(tmp_path, status):
    root = make_project(tmp_path, {"0001-a": "done", "0002-b": status})
    assert edit(root, str(root / "src/cart_api/main.py")) is None


@pytest.mark.parametrize(
    "statuses", [{}, {"0001-a": "done"}, {"0001-a": "draft", "0002-b": "clarifying"}]
)
def test_srcは進行中のreqが無ければ拒否する(tmp_path, statuses):
    root = make_project(tmp_path, statuses)
    assert edit(root, str(root / "src/cart_api/main.py")) is not None


# --- tests/ -----------------------------------------------------------------


@pytest.mark.parametrize("status", ["planned", "green"])
def test_testsはplannedかgreenなら通す(tmp_path, status):
    root = make_project(tmp_path, {"0001-a": status})
    assert edit(root, str(root / "tests/test_a.py")) is None


def test_testsはredのreqがあれば拒否する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green", "0002-b": "red"})
    assert edit(root, str(root / "tests/test_a.py")) is not None


@pytest.mark.parametrize(
    "statuses", [{}, {"0001-a": "done"}, {"0001-a": "draft"}, {"0001-a": "clarifying"}]
)
def test_testsは進行中のreqが無ければ拒否する(tmp_path, statuses):
    root = make_project(tmp_path, statuses)
    assert edit(root, str(root / "tests/test_a.py")) is not None


# --- 対象外 -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "docs/CHARTER.md",
        "Makefile",
        "pyproject.toml",
        ".gitignore",
        "specs/0001-a/req.md",
        "specs/0001-a/status.md",
        "specs/0001-a/discussion-log.md",
        "specs/_templates/req.md",
        "srcx/a.py",
        "mytests/a.py",
    ],
)
def test_対象外のパスは常に通す(tmp_path, path):
    root = make_project(tmp_path, {"0001-a": "red"})
    assert edit(root, str(root / path)) is None


def test_Write系以外のツールとfile_path無しは通す(tmp_path):
    root = make_project(tmp_path)
    assert guard.decide("Read", {"file_path": str(root / "CLAUDE.md")}, root) is None
    assert guard.decide("Write", {}, root) is None


# --- Bash（ベストエフォート） ------------------------------------------------

BASH_DENIED_PROTECTED = [
    "sed -i 's/a/b/' CLAUDE.md",
    "sed -i.bak s/a/b/ specs/README.md",
    "echo hi > .claude/hooks/guard.py",
    "echo hi >> specs/_catalog/viewpoints.md",
    "cat > .claude/settings.json <<'EOF'\n{}\nEOF",
    "cd x && tee .github/workflows/ci.yml",
    "rm -rf .claude/hooks",
    "mv specs/README.md /tmp/x",
    "touch .claude/UNLOCK",
    "python3 -c \"open('CLAUDE.md','w').write('x')\"",
    "python3 - <<'EOF'\nfrom pathlib import Path\nPath('.claude/x').write_text('x')\nEOF",
]


@pytest.mark.parametrize("command", BASH_DENIED_PROTECTED)
def test_Bashの保護対象への書き込みは拒否する(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "green"})
    assert bash(root, command) is not None


def test_BashもUNLOCKがあれば通す(tmp_path):
    root = make_project(tmp_path, unlock=True)
    assert bash(root, "sed -i 's/a/b/' CLAUDE.md") is None


@pytest.mark.parametrize(
    "command",
    [
        "git add CLAUDE.md .claude && git commit -m 'docs: CLAUDE.mdを更新' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'",
        "grep -n foo CLAUDE.md",
        "cat .claude/skills/req-run/SKILL.md",
        "ls .claude/hooks && head -5 specs/README.md",
        "git diff --stat -- .claude",
        "make check",
        "uv run pytest -q tests .claude/hooks",
        "uv run ruff format tests",
        "echo hi > /tmp/x",
        "sed -i 's/a/b/' specs/0001-a/status.md",
        "git mv specs/_templates/a.md specs/_templates/b.md",
    ],
)
def test_Bashの読み取りや無関係なコマンドは通す(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "red"})
    assert bash(root, command) is None


def test_Bashのtests書き込みはredで拒否しplannedで通す(tmp_path):
    red = make_project(tmp_path / "r", {"0001-a": "red"})
    planned = make_project(tmp_path / "p", {"0001-a": "planned"})
    assert bash(red, "echo x > tests/test_a.py") is not None
    assert bash(planned, "echo x > tests/test_a.py") is None


def test_Bashのsrc書き込みは進行中のreqが無ければ拒否する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "done"})
    assert bash(root, "cat > src/cart_api/main.py <<'EOF'\nx\nEOF") is not None
    assert bash(root, "cat src/cart_api/main.py") is None


# --- 0004: heredoc と変数経由の書き込み（誤検出の修正） -----------------------------
# 退行の網: 今の実装でも通るもの。誤検出を直す途中で、拒否すべきものが通らないようにする。


def test_変数経由で保護対象を開いて書くのは拒否する(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    command = "python3 - <<'EOF'\np='CLAUDE.md'\nopen(p,'w').write('x')\nEOF"
    assert bash(root, command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "bash <<'EOF'\ntouch .claude/x\nEOF",
        "cat <<'EOF' | bash\ntouch .claude/x\nEOF",
    ],
)
def test_インタプリタに渡したheredocの本文は拒否する(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, command) is not None


def test_変数経由で保護対象でない所に書くのは通す(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    command = "python3 - <<'EOF'\np='specs/a.md'\nopen(p,'w').write('x')\nEOF"
    assert bash(root, command) is None


# Red 1（AC-1）: 今回の事例。書き込み先は specs/ で、本文の文章に保護パスがあるだけ


def test_pythonのheredocで書き込み先がspecsなら本文に保護パスの文章があっても通す(
    tmp_path,
):
    root = make_project(tmp_path, {"0001-a": "planned"})
    command = (
        "python3 - <<'EOF'\n"
        "p='specs/0003/status.md'\n"
        "open(p,'w').write('see `touch .claude/x`')\n"
        "EOF"
    )
    assert bash(root, command) is None


# Red 2（AC-1）: データとして受けるだけのコマンドの heredoc は、本文を調べない


def test_catのheredocは本文の行頭が書き込み風でも通す(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    command = "cat > specs/x.md <<'EOF'\ntouch .claude/x\nEOF"
    assert bash(root, command) is None


# 退行の網（S-02、V-03、V-01）: 追加した時点で通る。誤検出を直しても、拒否すべきものが通らないことを守る


@pytest.mark.parametrize(
    "command",
    [
        "cat > specs/x.md <<'EOF'\nhello\nEOF\ncat > CLAUDE.md <<'EOF'\nx\nEOF",
        "python3 - <<'EOF'\nopen('specs/a.md','w').write('x')\nopen('CLAUDE.md','w').write('y')\nEOF",
    ],
)
def test_書き込みが2つあり片方が保護対象なら拒否する(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, command) is not None


def test_日本語と絵文字の本文でも判定は変わらない(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    cat_doc = "cat > specs/x.md <<'EOF'\n日本語の文章 🍎\ntouch .claude/x\nEOF"
    py_doc = (
        "python3 - <<'EOF'\n"
        "p='specs/a.md'\n"
        "open(p,'w').write('日本語 🍎 `touch .claude/x`')\n"
        "EOF"
    )
    assert bash(root, cat_doc) is None
    assert bash(root, py_doc) is None
    assert bash(root, "bash <<'EOF'\n日本語 🍎\ntouch .claude/x\nEOF") is not None


def test_commandが空や無いときは今までどおり通す(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, "") is None
    assert guard.decide("Bash", {}, root) is None


# Red 3（Q4、Q5）: 引用符なしの heredoc は、本文の `$(…)` とバッククォートが展開される


@pytest.mark.parametrize(
    "command",
    [
        "cat > specs/x.md <<EOF\n$(touch .claude/x)\nEOF",
        "cat > specs/x.md <<EOF\n`touch .claude/x`\nEOF",
        # 解析しきれないもの（閉じていない、入れ子が深すぎる）は、拒否側に倒す
        "cat > specs/x.md <<EOF\n$(touch .claude/x\nEOF",
        "cat > specs/x.md <<EOF\n" + "$(" * 30 + "date" + ")" * 30 + "\nEOF",
    ],
)
def test_引用符なしのheredocは本文の展開される部分を調べる(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, command) is not None


def test_引用符なしのheredocでも無害な展開は通す(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, "cat > specs/x.md <<EOF\ntoday: $(date)\nEOF") is None


def test_引用符ありのheredocは展開されないので通す(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, "cat > specs/x.md <<'EOF'\n$(touch .claude/x)\nEOF") is None


def test_heredocが終わったあとの行は普通のコマンドとして調べる(tmp_path):
    root = make_project(tmp_path, {"0001-a": "planned"})
    command = "cat > specs/x.md <<'EOF'\nbody\nEOF\ntouch .claude/x"
    assert bash(root, command) is not None


# Red 4（V-04、Q6、Q8）: 巨大な入力でも、2秒以内に判定する（hook のタイムアウトは10秒。超えると素通りになる）

TIME_LIMIT_SECONDS = 2.0
MB = 1024 * 1024

SLOW_CASES = {
    # 無害な大きな本文
    "1MBの無害なheredoc本文": "cat > specs/x.md <<'EOF'\n"
    + ("あ" * 99 + "\n") * (MB // 100)
    + "EOF",
    "1MBの無害な1行のコマンド": "echo " + "a" * MB,
    # 最悪ケース（正規表現や走査が極端に遅くなりやすいもの）
    "閉じていないheredocと長い本文": "cat <<'EOF'\n" + "x\n" * 500_000,
    "小さなheredocが大量": "cat <<'EOF'\nx\nEOF\n" * 50_000,
    "1行に<<が大量": "cat " + "<<EOF " * 100_000,
    "openの繰り返し": 'python3 -c "' + "open(" * 200_000 + '"',
    "書き込み風の動詞の繰り返し": "tee " * 200_000,
    "リダイレクト記号の繰り返し": "echo " + ">" * 500_000,
    "rubyの書き込み風の文字列の繰り返し": 'ruby -e "' + "File.write(" * 200_000 + '"',
    "rubyのopen(の繰り返し": 'ruby -e "' + "open(" * 200_000 + '"',
    "pythonのheredocでopen(の繰り返し": "python3 - <<'EOF'\n"
    + "open('" * 100_000
    + "\nEOF",
    "$(の繰り返し（引用符なしheredoc）": "cat <<EOF\n" + "$(" * 200_000 + "\nEOF",
    "バッククォートの繰り返し（引用符なしheredoc）": "cat <<EOF\n"
    + "`" * 200_000
    + "\nEOF",
    "閉じた$(の繰り返し（引用符なしheredoc）": "cat <<EOF\n"
    + "$(date) " * 100_000
    + "\nEOF",
}


_CHILD = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "sys.dont_write_bytecode = True\n"
    f"sys.path.insert(0, {str(GUARD.parent)!r})\n"
    "import guard\n"
    "command = sys.stdin.read()\n"
    "start = time.perf_counter()\n"
    "guard.decide('Bash', {'command': command}, Path(sys.argv[1]))\n"
    "print(time.perf_counter() - start)\n"
)


def decide_seconds(root: Path, command: str) -> float | None:
    """判定にかかった秒数。上限を超えたら None（別プロセスで動かし、上限で打ち切る）。

    同じプロセスで動かすと、遅いケースが終わるまで待つことになり、テスト自体が何分もかかる。
    """
    try:
        done = subprocess.run(  # noqa: S603
            [sys.executable, "-c", _CHILD, str(root)],
            input=command,
            capture_output=True,
            text=True,
            timeout=TIME_LIMIT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    return float(done.stdout)


@pytest.mark.parametrize("name", list(SLOW_CASES))
def test_巨大な入力でも判定は時間内に終わる(tmp_path, name):
    root = make_project(tmp_path, {"0001-a": "planned"})

    elapsed = decide_seconds(root, SLOW_CASES[name])

    assert elapsed is not None, f"{name}: {TIME_LIMIT_SECONDS}秒以内に終わらなかった"
    assert elapsed < TIME_LIMIT_SECONDS


# Red 5（FB 1、Q7）: heredoc の書き方のゆれ。ガードが「閉じた」と思う位置と、シェルが閉じる位置がずれると、
# 本文のあとのコマンドを見逃す。期待値は Q7=A で承認済み。

TAB = "\t"


@pytest.mark.parametrize(
    "command",
    [
        # Q7-1: タブつきの終了行でも閉じる。次の行は普通のコマンド
        f"cat <<-'EOF'\nbody\n{TAB}EOF\ntouch .claude/x",
        # Q7-2: `\EOF` でも、`EOF` の行で閉じる
        "cat > specs/x.md <<\\EOF\nbody\nEOF\ntouch .claude/x",
        # Q7-4: here-string も、受け取るのがインタプリタなら実行される
        'bash <<< "touch .claude/x"',
        # Q7-6、8: 行頭・末尾が空白の `EOF` は閉じ扱いにならず、本文は全部実行される（bash）
        "bash <<'EOF'\n EOF\ntouch .claude/x\nEOF",
        "bash <<'EOF'\nEOF \ntouch .claude/x\nEOF",
    ],
)
def test_heredocの書き方のゆれでも本文のあとのコマンドを見逃さない(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, command) is not None


@pytest.mark.parametrize(
    "command",
    [
        # Q7-3: `\EOF` は引用符つきと同じ扱い。本文は展開されない
        "cat > specs/x.md <<\\EOF\n$(touch .claude/x)\nEOF",
        # Q7-5: データとして受けるだけ
        'cat <<< "touch .claude/x"',
        # Q7-7、8: 行頭・末尾が空白の `EOF` は閉じ扱いにならず、本文は最後の `EOF` まで続く（cat）
        "cat > specs/x.md <<'EOF'\n EOF\ntouch .claude/x\nEOF",
        "cat > specs/x.md <<'EOF'\nEOF \ntouch .claude/x\nEOF",
    ],
)
def test_heredocの書き方のゆれでもデータとして書かれるだけなら通す(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, command) is None


# Red 6（Q9）: python 以外のインタプリタ（ruby、node、perl、php など）は、旧版と同じ粗い判定にとどめる。
# 旧版が（偶然）拒否していたものを、退行させない。他の言語の丁寧な解析は、将来の拡張。


@pytest.mark.parametrize(
    "command",
    [
        "ruby -e \"File.write('CLAUDE.md','x')\"",
        "node -e \"require('fs').createWriteStream('CLAUDE.md').write('x')\"",
        "perl -e \"open(F,'>CLAUDE.md')\"",
        "ruby -e \"File.open('.claude/x','w'){|f| f.write('x')}\"",
    ],
)
def test_python以外のインタプリタが保護対象に書くのは拒否する(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "ruby -e \"File.write('specs/a.md','x')\"",
        "node -e \"console.log('CLAUDE.md')\"",
    ],
)
def test_python以外のインタプリタでも保護パスに書かないなら通す(tmp_path, command):
    root = make_project(tmp_path, {"0001-a": "planned"})
    assert bash(root, command) is None


# --- 0007: 既存テストを黙って書き換えさせない ----------------------------------------
# 「既存」の基準は、最後にコミットした内容（HEAD）。足すのは自由、変える・弱める・消すは拒否。

BASE_TEST = """import pytest


def test_a():
    assert f(1) == 2
    assert f(2) == 3


@pytest.mark.parametrize("x", [1, 2])
def test_b(x):
    assert x > 0


class TestK:
    def test_m(self):
        assert True
"""


def _git_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def run_git(path: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", "-C", str(path), *args],  # noqa: S607
        check=True,
        capture_output=True,
        env=_git_env(),
    )


def make_repo(
    tmp_path: Path,
    files: dict[str, str] | None = None,
    statuses: dict[str, str] | None = None,
    commit: bool = True,
    init: bool = True,
) -> Path:
    """テスト用のリポジトリ。files をコミットした状態にする（commit=False ならコミット0件）。"""
    root = make_project(tmp_path, statuses or {"0001-a": "planned"})
    for rel, text in (files or {"tests/test_x.py": BASE_TEST}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    if init:
        run_git(root, "init", "-q")
        run_git(root, "config", "user.email", "t@example.com")
        run_git(root, "config", "user.name", "t")
        if commit:
            run_git(root, "add", "-A")
            run_git(root, "commit", "-q", "-m", "base")
    return root


def change_edit(
    root: Path, rel: str, old: str, new: str, replace_all: bool = False
) -> str | None:
    tool_input = {
        "file_path": str(root / rel),
        "old_string": old,
        "new_string": new,
        "replace_all": replace_all,
    }
    return guard.decide("Edit", tool_input, root)


def change_write(root: Path, rel: str, content: str) -> str | None:
    return guard.decide(
        "Write", {"file_path": str(root / rel), "content": content}, root
    )


TEST_X = "tests/test_x.py"
APPEND_AFTER = "        assert True\n"  # BASE_TEST の末尾（一意）

# AC-1（足すのは自由）: 今の実装でも通る網


def test_AC1_新しいテスト関数を末尾に足すのは通す(tmp_path):
    root = make_repo(tmp_path)
    new = APPEND_AFTER + "\n\ndef test_new():\n    assert f(3) == 4\n"
    assert change_edit(root, TEST_X, APPEND_AFTER, new) is None


def test_AC1_まだ無いテストファイルを作るのは通す(tmp_path):
    root = make_repo(tmp_path)
    assert (
        change_write(root, "tests/test_new.py", "def test_n():\n    assert True\n")
        is None
    )


def test_AC1_parametrizeのリストに値を足すのは通す(tmp_path):
    root = make_repo(tmp_path)
    assert change_edit(root, TEST_X, "[1, 2]", "[1, 2, 3]") is None


def test_内容の情報がない呼び出しは今までどおり通す(tmp_path):
    root = make_repo(tmp_path)
    assert guard.decide("Edit", {"file_path": str(root / TEST_X)}, root) is None


# AC-2（変える・弱める・消すは拒否）


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("    assert f(2) == 3\n", ""),  # assert 行を消す
        ("    assert f(1) == 2\n", "    assert f(1) == 5\n"),  # 期待値を変える
        ("[1, 2]", "[1, 9]"),  # parametrize の値を変える
        ("    assert x > 0\n", "    assert x >= 0\n"),  # 比較を弱める
    ],
)
def test_AC2_既存テストのassertや期待値を変える_消すは拒否する(tmp_path, old, new):
    root = make_repo(tmp_path)
    assert change_edit(root, TEST_X, old, new) is not None


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("def test_a():", "@pytest.mark.skip\ndef test_a():"),
        ("def test_a():", "@pytest.mark.xfail\ndef test_a():"),
        ("    assert f(1) == 2\n", "    pytest.skip('x')\n    assert f(1) == 2\n"),
    ],
)
def test_AC2_既存テストにskipやxfailを付けるのは拒否する(tmp_path, old, new):
    root = make_repo(tmp_path)
    assert change_edit(root, TEST_X, old, new) is not None


@pytest.mark.parametrize(
    "appended",
    [
        "\n\n@pytest.mark.skip\ndef test_new():\n    assert True\n",
        "\n\n@pytest.mark.xfail\ndef test_new():\n    assert False\n",
        "\n\npytestmark = pytest.mark.skip\n",
    ],
)
def test_AC2_新しく足すテストでもskipやxfailやpytestmarkは拒否する(tmp_path, appended):
    root = make_repo(tmp_path)
    assert change_edit(root, TEST_X, APPEND_AFTER, APPEND_AFTER + appended) is not None


def test_AC2_既存テスト関数を消すのは拒否する(tmp_path):
    root = make_repo(tmp_path)
    old = "def test_a():\n    assert f(1) == 2\n    assert f(2) == 3\n\n\n"
    assert change_edit(root, TEST_X, old, "") is not None


def test_AC2_既存ファイルを丸ごと置き換えてassertが減るのは拒否する(tmp_path):
    root = make_repo(tmp_path)
    assert change_write(root, TEST_X, "def test_only():\n    assert True\n") is not None


def test_AC2_内容が変わらない置き換えは通す(tmp_path):
    root = make_repo(tmp_path)
    assert change_write(root, TEST_X, BASE_TEST) is None


def test_AC2_構文エラーになる変更は拒否する(tmp_path):
    root = make_repo(tmp_path)
    assert (
        change_edit(root, TEST_X, "    assert f(1) == 2\n", "    assert f(1) ==\n")
        is not None
    )


# Q12: 同名の定義（あとの定義が前を上書きする）


@pytest.mark.parametrize(
    "appended",
    [
        "\n\ndef test_a():\n    assert True\n",  # 同名の関数
        "\n    def test_m(self):\n        assert False\n",  # 同じクラスの同名メソッド
        "\n\ntest_a = lambda: None\n",  # 代入での上書き
    ],
)
def test_Q12_同名の定義が増えるのは拒否する(tmp_path, appended):
    root = make_repo(tmp_path)
    assert change_edit(root, TEST_X, APPEND_AFTER, APPEND_AFTER + appended) is not None


def test_Q12_別のクラスの同名メソッドは通す(tmp_path):
    root = make_repo(tmp_path)
    appended = "\n\nclass TestOther:\n    def test_m(self):\n        assert True\n"
    assert change_edit(root, TEST_X, APPEND_AFTER, APPEND_AFTER + appended) is None


# Q2: 「既存」の基準は HEAD。未コミットのテストは自由に直せる


def test_Q2_HEADに無いファイルは自由に直せる(tmp_path):
    root = make_repo(tmp_path)
    (root / "tests/test_u.py").write_text(
        "def test_u():\n    assert 1 == 1\n", encoding="utf-8"
    )
    assert (
        change_edit(root, "tests/test_u.py", "assert 1 == 1", "assert 1 == 2") is None
    )


def test_Q2_未コミットで足したテストは直せるがHEADの行は変えられない(tmp_path):
    root = make_repo(tmp_path)
    p = root / TEST_X
    p.write_text(BASE_TEST + "\n\ndef test_u():\n    assert 1 == 1\n", encoding="utf-8")
    assert change_edit(root, TEST_X, "assert 1 == 1", "assert 1 == 2") is None
    assert change_edit(root, TEST_X, "    assert f(2) == 3\n", "") is not None


# Q11: HEAD が取れないとき


def test_Q11_コミットが0件ならすべて新規として通す(tmp_path):
    root = make_repo(tmp_path, commit=False)
    assert change_edit(root, TEST_X, "    assert f(2) == 3\n", "") is None


def test_Q11_gitのリポジトリではないなら拒否する(tmp_path):
    root = make_repo(tmp_path, init=False)
    assert (
        change_edit(
            root,
            TEST_X,
            "    assert f(1) == 2\n",
            "    assert f(1) == 2\n    assert True\n",
        )
        is not None
    )


def test_Q11_gitコマンドが無いなら拒否する(tmp_path, monkeypatch):
    root = make_repo(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "no-such-dir"))
    assert (
        change_edit(
            root,
            TEST_X,
            "    assert f(1) == 2\n",
            "    assert f(1) == 2\n    assert True\n",
        )
        is not None
    )


def test_Q11_gitが時間内に答えないなら拒否する(tmp_path, monkeypatch):
    root = make_repo(tmp_path)
    fake = tmp_path / "bin"
    fake.mkdir()
    script = fake / "git"
    script.write_text("#!/bin/sh\nsleep 5\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake))
    monkeypatch.setattr(guard, "GIT_TIMEOUT_SECONDS", 0.3)
    assert (
        change_edit(
            root,
            TEST_X,
            "    assert f(1) == 2\n",
            "    assert f(1) == 2\n    assert True\n",
        )
        is not None
    )


def test_Q11_GIT_DIRを細工しても判定は変わらない(tmp_path, monkeypatch):
    root = make_repo(tmp_path / "real")
    evil = tmp_path / "evil"
    evil.mkdir()
    run_git(
        evil, "init", "-q"
    )  # コミット0件のリポジトリ（これが基準にされると、すべて「新規」で通ってしまう）
    monkeypatch.setenv("GIT_DIR", str(evil / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(evil))
    assert change_edit(root, TEST_X, "    assert f(2) == 3\n", "") is not None
    assert (
        change_edit(
            root,
            TEST_X,
            APPEND_AFTER,
            APPEND_AFTER + "\n\ndef test_n():\n    assert True\n",
        )
        is None
    )


# --- 実際のスクリプトを標準入力で動かす -----------------------------------------


def run_guard(root: Path, stdin: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    return subprocess.run(  # noqa: S603
        [sys.executable, str(GUARD)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def payload(tool: str, **tool_input: str) -> str:
    return json.dumps(
        {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
    )


def test_スクリプトは拒否するときdenyのJSONを出す(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green"})

    res = run_guard(root, payload("Write", file_path=str(root / "CLAUDE.md")))

    assert res.returncode == 0
    out = json.loads(res.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == "deny"
    assert out["permissionDecisionReason"]


def test_スクリプトは通すとき何も出さない(tmp_path):
    root = make_project(tmp_path, {"0001-a": "green"})

    res = run_guard(root, payload("Edit", file_path=str(root / "src/a.py")))

    assert (res.returncode, res.stdout) == (0, "")


def test_スクリプトは壊れた入力を安全側で拒否する(tmp_path):
    root = make_project(tmp_path)

    res = run_guard(root, "これはJSONではない")

    assert res.returncode == 0
    assert json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
