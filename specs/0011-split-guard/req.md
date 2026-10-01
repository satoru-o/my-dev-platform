# 0011 split-guard

<!-- このファイルは「要求事項」だけを書く。status・size・risk・kind は status.md、質問・FB は discussion-log.md -->

## やりたいこと
guard.py（1193行）を、機能ごとのモジュールに分ける。移動だけで、挙動は一切変えない。設計見直しの段階1。パス分類、git(HEAD)取得、AST比較、pytest設定比較、reqの表比較、Bash解析が1ファイルに同居しているのを、段階2（純粋関数の整備）と段階3（CIからの利用）の土台にするため、先に分ける。

## 受け入れ条件
<!-- kind: refactor のため、具体例の表は無し。確認項目を並べる。出典: [人]=人間が自分で述べた、[案→承認]=AIの案を人間が選んだ -->

- 既存テストが全件通る（`make check` が終了コード0。311件を基準にする） [人]
- `.claude/hooks/test_guard.py` と `tests/` が、無改変である（`git diff main -- tests .claude/hooks/test_guard.py` が空） [案→承認]
- 移動の前後で、判定が同一である。0008 の15件、`test_guard.py` の全ケースの入力、追加の入力（保護パス、Bash の書き込み、git の操作、巨大な入力、CRLF）を、分割前の `guard.py`（`main` の版）と、分割後の `guard.py` に通し、判定（許可/拒否と理由）が全件一致する。比較の方法と結果は、`status.md` の「結果」に残す [案→承認]
- `guard.py` を `python3 guard.py`（hook と同じ呼び出し）で実行しても、動く。`settings.json` は変更しない [案→承認]
- テストが使う `guard` の名前は、`decide`、`GIT_TIMEOUT_SECONDS`、CLI（`main`）だけ。この3つは、`guard.py` に残し、`GIT_TIMEOUT_SECONDS` は呼び出し時に読んで、git を呼ぶモジュールに引数で渡す（`monkeypatch.setattr(guard, "GIT_TIMEOUT_SECONDS", …)` が効き続ける） [案→承認]
- 2秒以内に判定する性能テスト（既存）が、通り続ける。モジュールを分けたことで、起動時間が増えていない [案→承認]

## やらないこと
（暫定・要確認）
- 挙動の変更（判定の追加、緩和、削除。誤検出の修正も含む）。これは段階2以降
- 純粋関数への整理（段階2）、CI からの利用（段階3）、Bash 解析の削除（段階5。sandbox が使えないので、行わない）
- `permissions.deny` による `.claude/hooks/**` の保護（段階4から。UNLOCK が効かなくなるため）
- `settings.json`、`CLAUDE.md`、`specs/README.md` の変更
- テストの書き換え、削除、追加（追加も、段階1では行わない）

## 制約
（暫定・要確認）
- `.claude/**` は保護対象。人間が UNLOCK を置いてから編集する。終わったら外す
- 開発は、使い捨ての作業コピー（`$CLAUDE_JOB_DIR/tmp/dev` など）で行い、テストが通ってから、本物の `.claude/hooks/` にコピーする（壊れた `guard.py` で、編集できなくならないため）
- 分け方の暫定案: `paths`（パス分類、保護パス、req の状態）、`gitbase`（HEAD の取得）、`pyrules`（AST 比較、pytest 設定、conftest）、`reqrules`（req.md の AC 行）、`bashscan`（Bash 解析、git 操作）。`guard.py` には、`decide` と `main` と `GIT_TIMEOUT_SECONDS` を残す。最終的な分け方は、`/req-run` で、依存の向き（循環しない）を確かめながら決める
- 移動は、1モジュールずつ、コミットを分ける。各コミットで、`make check` が通る
