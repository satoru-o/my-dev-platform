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
