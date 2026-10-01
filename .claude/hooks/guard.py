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
import sys
from pathlib import Path

from guardlib.bashscan import (
    _bash_scan,
)
from guardlib.changes import (
    _with_switch,
    change_reason,
)
from guardlib.gitbase import _head_paths_cache
from guardlib.gitops import (
    git_reason,
)
from guardlib.paths import (
    WRITE_TOOLS,
    deny_reason,
    kind_of,
    rel_path,
)
from guardlib.shellwrites import (
    bash_change_reason,
)

GIT_TIMEOUT_SECONDS = 5.0  # 「既存」の基準（HEAD）を取る git の、待つ時間の上限


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
