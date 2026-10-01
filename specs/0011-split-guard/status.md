---
id: 0011
slug: split-guard
kind: refactor # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: done # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: refactor は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし、hook は、守りの仕組みなので、判定が同一であることを、機械で確かめる）
---

# 0011 split-guard の状態

## いま
done。G3 確認済み。次は段階2（純粋関数の整備）。比較の道具をリポジトリに入れるかは、段階2の req で決める。

## 結果
### 何を変えたか
- `.claude/hooks/guard.py`（1193行）を、`decide`・`main`・`GIT_TIMEOUT_SECONDS` だけ残して 126行にし、残りを `.claude/hooks/guardlib/` の10モジュールに移した。依存は一方向（循環なし）。
  - `paths`（パスの分類、保護パス、req の状態）、`gitbase`（HEAD の取得）、`pyrules`（AST 比較、pytest 設定。純粋関数）、`reqrules`（AC の表の比較。純粋関数）、`changes`（既存テストの変更の検出、スイッチ）、`heredoc`、`pywrites`、`shellwrites`、`gitops`、`bashscan`（Bash 解析）。
  - 暫定案の5つより細かくした（Bash 解析の約550行が、1つでは大きいため）。
- 移動は、行の範囲を指定した生成スクリプトで機械的に行った（手で書き写していない）。1モジュールずつ、11コミット（準備1、移動10）。各コミットで、`make lint` と `make test`（341件）が通る。
- 唯一、移動でない変更（準備のコミット `1d9cf8a`）: `GIT_TIMEOUT_SECONDS` を、`decide` が呼び出し時に読み、git を呼ぶ関数に引数（`timeout`）で渡す形にした。`monkeypatch.setattr(guard, "GIT_TIMEOUT_SECONDS", …)` が、今までどおり効く。

### 確認した項目
- `make check`: 通る（341 passed。lint、型、pip-audit、detect-secrets も）。
- `tests/`、`.claude/hooks/test_guard.py`、`.claude/settings.json`: `main` と無改変（`git diff main --stat` が空）。
- 判定の同一性: 1753 入力を、分割前（`main` の版）と分割後に通し、判定の理由・スイッチが消えたかまで、全件一致（JSON をバイト比較）。内訳は、Edit・Write 640、Bash 1104（スイッチ・UNLOCK の有無、status は無し/planned/red/done）、巨大なファイル5、CRLF 2、git なし2。拒否 953、許可 800。
  - 比較の検出力も確かめた: 分割後のコードに、わざと1文字の違い（`--hard` の判定）を入れると、32件が不一致になった。
  - 加えて、`test_guard.py` の全テスト中の `decide` 呼び出し 323件も、分割前後で同一だった（ログ比較）。
  - 全10段階の各状態で、311件のガードのテストが通ることも、使い捨てコピーで確認してから、本物に反映した。
- `python3 guard.py`（hook と同じ呼び出し）で動く。起動は1回約50ms。`settings.json` は変更なし。性能テスト（2秒以内）は通る。

### 気づき
- 比較の道具（生成スクリプトと、1753 入力の比較）は、使い捨てコピーの場所（リポジトリの外）にある。段階2・3でも使うので、リポジトリに入れるかは人間が決める。
- 作業中、私が誤って `git stash` と `git checkout main -- .claude/hooks/guard.py` を実行し、`guard.py` が旧版に戻り、この `status.md` の変更が stash された。気づいてすぐ、`git checkout HEAD -- .claude/hooks/guard.py` と `git stash pop` で戻し、1753 入力の比較をやり直して、一致を確認した（stash は空）。コミットは影響なし。
