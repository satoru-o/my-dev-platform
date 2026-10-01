"""「守る対象と決まったあとに、比べるだけ」の純粋関数。hook と CI（段階3）の両方から使う。

入力は、ファイルの相対パス（posix）と、旧・新の内容の文字列だけ。git、ファイル、環境変数、スイッチ、
status.md には触れない（それらは hook 側の責務: `changes`）。標準ライブラリだけを使う。

解析しきれない入力（構文エラー、壊れた TOML・ini、再帰が深すぎる、巨大な入力）は、例外にせず、
拒否する理由を返す（拒否側に倒す）。想定していない例外は、そのまま投げる（呼び出し側が拒否側に倒す）。
時間制限（別プロセスで打ち切る処理）は、呼び出し側の責務。
"""

from guardlib.pyrules import (
    PYTEST_CONFIG_FILES,
    conftest_config_reason,
    pytest_config_reason,
    python_change_reason,
)
from guardlib.reqrules import _REQ_RE, req_change_reason


def is_test_py(rel: str) -> bool:
    return (rel.startswith("tests/") and rel.endswith(".py")) or rel == "conftest.py"


def compare_kind(rel: str) -> str | None:
    """パスから、何として比べるか（"test" / "pytest_config" / "req"）。比べる対象でなければ None。

    status.md は見ない。「実装中の req.md か」の判定は、hook 側の責務。
    """
    if is_test_py(rel) or rel.endswith("/conftest.py"):
        return "test"
    if rel in PYTEST_CONFIG_FILES:
        return "pytest_config"
    if _REQ_RE.fullmatch(rel):
        return "req"
    return None


def change_reason_for(rel: str, base_src: str | None, new_src: str) -> str | None:
    """既存のテスト・pytest の設定・req.md の AC を、変える・弱める・消す変更なら、その理由。

    base_src が None（HEAD に無い＝新規）なら、通す（None）。new_src は str だけ（内容が分からない
    場合は、呼び出し側が、この関数を呼ばずに通す）。足すだけなら None。
    """
    kind = compare_kind(rel)
    if kind is None:
        return None
    if kind == "test":
        why = python_change_reason(base_src, new_src)
        if why is None and rel.endswith("conftest.py"):
            why = conftest_config_reason(base_src, new_src)
        label = "既存のテスト"
    elif kind == "pytest_config":
        why, label = pytest_config_reason(rel, base_src, new_src), "pytest の設定"
    else:
        why, label = (
            req_change_reason(base_src, new_src),
            "実装中の req.md の受け入れ条件",
        )
    if why is None:
        return None
    return f"{label}を変える・弱める・消す変更です（{why}）"
