---
id: 0012
slug: pure-compare
kind: refactor # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: green # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: refactor は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし hook は守りの仕組みなので、判定が同一であることを、機械で確かめる）
---

# 0012 pure-compare の状態

## いま
green。G3 待ち: 結果を確認して、done にしてよいか返してください。確認してほしい点が2つあります（「気づき」の1と2）。UNLOCK は、外してかまいません。

## 結果
### 何を変えたか
- `.claude/hooks/guardlib/compare.py`（新規）: `change_reason_for(rel, base_src, new_src)`。ファイルの相対パスと、旧・新の文字列だけを入れる純粋関数。標準ライブラリと `pyrules`・`reqrules` だけを使う（import して確かめた: 読み込まれる `guardlib` のモジュールは、`compare`・`pyrules`・`reqrules` の3つだけ。`subprocess` も読み込まれない）。`compare_kind(rel)`（テスト / pytest の設定 / req.md の、どれとして比べるか）と `is_test_py` も、ここに移した。
- `guardlib/changes.py`: `change_reason` は、HEAD の取得と、Edit・Write の適用後の内容の作成だけを行い、比較は `change_reason_for` に任せる。「守る対象か」の判定（実装中の req.md か＝`status.md` を読む部分）、スイッチ、HEAD が取れないときの拒否は、hook 側に残した。時間制限も hook 側のまま。
- `tools/guard-equiv/`（新規）: `run.py`（基準と、いまの版を比べる）、`worker.py`（入力の一覧と、判定の記録）、`README.md`。基準は、分割前のコミット `55adc1b92167…`（0011 の開始時点）の hash で固定し、`git show` で取り出す（コピーは置かない）。

### 確認した項目
- `make check`: 通る（341 passed、lint、型、pip-audit、detect-secrets）。detect-secrets が、基準のコミット hash を、高エントロピーの文字列として誤検出したので、`# pragma: allowlist secret` で許可した。
- `tests/`、`.claude/hooks/test_guard.py`、`.claude/settings.json`: `main` と無改変。
- 判定の同一性: `tools/guard-equiv/run.py` で、1853 入力（0011 の 1753 に、解析しきれない入力の例を足したもの）を、基準と、いまの版に通し、理由とスイッチの消費まで全件一致（拒否 1021、許可 832）。コミットの途中（`compare.py` を入れた時点）と、最後の両方で確認。
- 入力の一覧に含まれていること（`run.py` が毎回表示する）:
  - 新規: `write_new_test`（許可）、`write_pytest_ini_new`（許可）、Bash の新規ファイル書き込み（許可）、`nogit/no_commits`（許可）
  - 削除: `edit_delete_test`（拒否）、Bash の `rm`（拒否）、`git rm`（拒否）
  - 内容不明: `edit_nonexistent_old`（許可）、`edit_no_path`（許可）
  - 解析しきれない: 構文エラー、壊れた TOML、NUL 文字、深い入れ子、壊れた conftest、巨大なファイルの書き換え（すべて拒否）、`tool = 1`（下の気づき1）
- ガードのテスト 311 件（`test_guard.py`）は、使い捨てコピーでも、本物でも、通る。

### 気づき（人間の確認がほしい）
1. **純粋関数の内側で拒否側に倒していない入力が1つある**: pyproject.toml に `tool = 1`（TOML として正しいが、型が違う）と書くと、`pytest_config_reason` が `AttributeError` を投げる。hook では、`main()` が例外を拾って「ガードの内部エラーのため拒否しました」と拒否するので、安全側ではある。ただし、CI（段階3）から直接呼ぶと、例外になる。req の「例外を投げず」は、挙げた入力（構文エラー、壊れた TOML・ini、深い再帰、巨大な入力）では満たしている。この入力を内側で扱うと、拒否の文面が変わり、スイッチが置かれていると通せてしまう（今は、内部エラーはスイッチで通せない）ため、「挙動を変えない」この req では直さなかった。直すかは、別の req（段階6の候補）で決めたい。それまで、CI から呼ぶ側は、例外も拒否として扱うこと。
2. **新規・削除・内容不明の扱い**（AI が決めた案）は、req のとおり実装した。`base_src is None` は通す。`new_src` は `str` のみ。削除は、Edit・Write では起きず、Bash 側が扱う（変えていない）。この分け方でよいか、確認してほしい。
3. `tools/guard-equiv/run.py` は、約4分かかる（入力ごとに、使い捨ての git リポジトリを作るため）。`make check` には入れていない（常設すると、遅くなる）。段階3で、CI に入れるかは、あとで決める。
4. 段階4への申し送り（人間の指示）: `tools/guard-equiv/` を、保護パス（`guardlib/paths.py` の `PROTECTED` と `permissions.deny`）に足す。足さないと、道具か基準の hash を書き換えて「判定は同一」と言えてしまう。`tools/guard-equiv/README.md` に残した。この req では足していない。
