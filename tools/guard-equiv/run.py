"""guard の判定が、分割前（基準のコミット）と、いまの版で、同一かを確かめる。

使い方（リポジトリのどこからでも）: uv run python tools/guard-equiv/run.py
基準は、分割前のコミットの hash で固定する（リポジトリ内のコピーは使わない）。
同一なら終了コード0。1件でも違えば、違う入力を表示して、終了コード1。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# 0011（guard.py を分ける）の開始時点。guard.py が1193行の版
BASELINE = "55adc1b92167f2d3441eaf00b252365aef3e6a1b"  # pragma: allowlist secret

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))


def run_worker(directory: Path, out: Path) -> None:
    subprocess.run(  # noqa: S603
        [sys.executable, str(HERE / "worker.py"), str(directory), str(out)],
        check=True,
    )


def baseline_guard(into: Path) -> None:
    shown = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-C",
            str(ROOT),
            "show",
            f"{BASELINE}:.claude/hooks/guard.py",
        ],
        capture_output=True,
        check=True,
    )
    into.mkdir(parents=True, exist_ok=True)
    (into / "guard.py").write_bytes(shown.stdout)


def main() -> int:
    from worker import required_keys

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        baseline_guard(tmp / "base")
        run_worker(tmp / "base", tmp / "base.json")
        run_worker(ROOT / ".claude" / "hooks", tmp / "new.json")
        base = json.loads((tmp / "base.json").read_text(encoding="utf-8"))
        new = json.loads((tmp / "new.json").read_text(encoding="utf-8"))

    differ = sorted(k for k in base if base[k] != new.get(k))
    extra = sorted(set(new) - set(base))
    print(f"基準 {BASELINE[:12]}: {len(base)} 入力、いまの版: {len(new)} 入力")
    print("含まれていることの確認（入力: 判定）:")
    missing = []
    for label, keys in required_keys().items():
        for key in keys:
            if key not in new:
                missing.append(key)
                print(f"  [{label}] {key}: 無い")
                continue
            reason = new[key]["reason"]
            print(f"  [{label}] {key}: {'拒否' if reason else '許可'}")
    if differ or extra or missing:
        print(
            f"不一致 {len(differ)} 件、増えた入力 {len(extra)} 件、"
            f"足りない確認 {len(missing)} 件"
        )
        for key in differ[:20]:
            print(f"  {key}\n    基準: {base[key]}\n    いま: {new[key]}")
        return 1
    print("全件一致（理由とスイッチの消費まで）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
