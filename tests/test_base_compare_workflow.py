import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/check.yml"


def workflow_text():
    return WORKFLOW.read_text(encoding="utf-8")


def test_AC6_pushとpull_requestの両方で動き_pull_requestはラベルの付け外しでも動く():
    text = workflow_text()

    assert re.search(r"^on:\n  push:", text, re.MULTILINE)
    found = re.search(r"^  pull_request:\n    types: \[([^\]]*)\]", text, re.MULTILINE)
    assert found
    types = {t.strip() for t in found.group(1).split(",")}
    assert {"opened", "synchronize", "reopened", "labeled", "unlabeled"} <= types


def jobs(text):
    """jobs: の下の、job ごとの本文（2文字のインデントの見出しで区切る）。"""
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([\w-]+):\n", body, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def test_X01_ラベルを外すjobだけが書き込み権限を持ち_PRのコードを扱わない():
    found = jobs(workflow_text())

    assert {"check", "unlabel", "compare"} <= set(found)
    assert "pull-requests: write" in found["unlabel"]
    assert "actions/checkout" not in found["unlabel"]
    for name in ("check", "compare"):
        assert "write" not in found[name], name
    assert "pull-requests: write" not in workflow_text().split("\njobs:\n")[0]


def test_AC5_比較のjobは_ラベルを外すjobの後に動き_pull_requestのときだけ動く():
    found = jobs(workflow_text())
    assert "compare" in found
    compare = found["compare"]

    assert re.search(r"needs:\s*\[?unlabel\]?", compare)
    assert "github.event_name == 'pull_request'" in compare


def test_AC5_ラベルは実行時にAPIで読み直し_新しいコミットのときは無いものとして扱う():
    found = jobs(workflow_text())
    compare = found["compare"]

    assert "github.event.pull_request.labels" not in workflow_text()
    assert re.search(r'gh api "repos/\$REPO/issues/\$PR/labels"', compare)
    assert re.search(r'if \[ "\$ACTION" = "synchronize" \]; then\s+LABELS=""', compare)
    assert "github.event.action == 'synchronize'" in found["unlabel"]


def test_AC6_比較のjobは履歴を全部取る_checkoutに認証情報を残さない():
    found = jobs(workflow_text())

    for name in ("check", "compare"):
        assert "fetch-depth: 0" in found[name], name
        assert "persist-credentials: false" in found[name], name


def test_AC6_makeにcompareがあり_make_checkに含まれ_警告だけのモードで動く():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    target = re.search(r"^compare:\n((?:\t.*\n?)+)", makefile, re.MULTILINE)
    assert target
    assert "python -m base_compare" in target.group(1)
    assert "--mode local" in target.group(1)
    check = re.search(r"^check:(.*)$", makefile, re.MULTILINE)
    assert check
    assert "compare" in check.group(1).split()


def test_X03_runの中にPRのタイトルやブランチ名を直接埋め込まない():
    run_lines = [
        line
        for line in workflow_text().split("\n")
        if "${{" in line and not line.lstrip().startswith(("#", "if:"))
    ]
    in_env = re.compile(r"^\s+[A-Z_]+: \$\{\{ [\w.]+ \}\}$")

    for line in run_lines:
        assert in_env.match(line), line
    for danger in ("head_ref", "pull_request.title", "pull_request.body", "head.ref"):
        assert danger not in workflow_text()
