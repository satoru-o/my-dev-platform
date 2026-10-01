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
