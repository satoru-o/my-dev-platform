# 0012 pure-compare

<!-- このファイルは「要求事項」だけを書く。status・size・risk・kind は status.md、質問・FB は discussion-log.md -->

## やりたいこと
guard の比較ロジックを、git・ファイル・環境変数に触れない純粋関数にまとめ、あとから CI（段階3）でも使えるようにする。設計見直しの段階2。hook の判定は変えない。

（人間の指示は、`/req-new で段階2を起こして` と、slug `pure-compare` のみ。下の内容は、前の提案（CHARTER の段階表）にある段階2の説明と、私の推奨を元にした AI の暫定案で、まだ人間の承認を受けていない。）

## 受け入れ条件
<!-- kind: refactor のため、具体例の表は無し。確認項目を並べる。出典: [人]=人間が自分で述べた、[案→承認]=AIの案を人間が選んだ。承認前のものは「AI暫定」 -->

- 既存テストが全件通る（`make check` が終了コード0。341件を基準にする） [案→承認]（0011 と同じ基準。AI暫定）
- `tests/`、`.claude/hooks/test_guard.py`、`.claude/settings.json` が、`main` と無改変である（AI暫定）
- 判定が同一である。0011 と同じ 1753 入力（Edit・Write、Bash、巨大なファイル、CRLF、git なし）を、変更前（`main` の版）と変更後に通し、理由とスイッチの消費まで全件一致する（AI暫定）
- 新しい純粋関数が1つある: `guardlib/compare.py` の `change_reason_for(rel, base_src, new_src)`（暫定名）。入力は、ファイルの相対パスと、旧・新の文字列だけ。`rel` の種類（テスト、conftest、pytest の設定、実装中の req.md）で、`pyrules` / `reqrules` の比較に振り分け、拒否する理由か `None` を返す。git、ファイル読み込み、環境変数、スイッチに触れない（AI暫定）
- hook の `changes.change_reason` は、HEAD の取得と、Edit・Write の適用後の内容の作成だけを行い、比較は `change_reason_for` に任せる（AI暫定）
- **責務の線引き**: `change_reason_for` は「守る対象と決まったあとに、比べるだけ」の関数。次は hook 側（`changes`）に残し、純粋関数に入れない [人]
  - 「守る対象か」の判定（`_guarded_kind`）。特に、`status.md` を読んで「実装中の req.md の保護が有効か」を決める部分
  - スイッチ（`ALLOW_TEST_CHANGE`）の扱い
  - 時間制限（別プロセスで打ち切る処理）。これも hook 側の責務のまま
- **新規・削除・内容不明の扱い**（先に決める。AI が決めた案で、人間の確認が要る）
  - `base_src` が `None`（HEAD に無い＝新規）: 通す（`None` を返す）。現行どおり
  - `new_src` は `str` だけを受け取る（`None` は受け取らない）。「Edit が失敗する」「内容が分からない」場合は、現行どおり hook 側が `change_reason_for` を呼ばずに通す。ファイルの削除は、Edit・Write では起きない（Bash 経由の `rm` などは、Bash 解析の側が扱い、変えない）
  - 判定が同一であることの比較に使う 0011 の 1753 入力に、次が含まれていることを確認し、結果を `status.md` に書く: 新規ファイル（`write_new_test`、Bash の新規ファイル書き込み、`nogit/no_commits`）、削除（`edit_delete_test`、Bash の `rm`、`git rm`）、内容不明（`edit_nonexistent_old`、`edit_no_path`）
- **解析しきれない入力は、純粋関数の内側で、拒否側に倒す**: 構文エラー、解析できない TOML・ini、再帰が深すぎる入力、巨大な入力は、例外を投げず、拒否する理由を返す [人]。入力例を、比較の対象に含める（`edit_syntax_error`、`write_pyproject_broken`、巨大なファイルの書き換え）
- 比較の道具（0011 で使った、生成スクリプトと、1753 入力の判定比較）を、リポジトリに入れる。置き場所は暫定で `tools/guard-equiv/`（`docs/**` は自動マージの対象なので、コードは置かない）。`make check` の lint を通し、使い方を README に書く（AI暫定）
  - **比較の基準は、分割前のコミットの hash で固定する**: `55adc1b92167f2d3441eaf00b252365aef3e6a1b`（0011 の開始時点。`guard.py` が1193行の版）。道具は `git show <hash>:.claude/hooks/guard.py` で基準を取り出し、リポジトリ内のコピーは使わない [人]
  - **段階4への申し送り**: `tools/guard-equiv/` は、守りの検査の基準を作る道具なので、段階4で保護パス（`PROTECTED` と `permissions.deny`）に足す。README と、この req の「結果」に、そのメモを残す（この req では、保護パスに足さない） [人]

## やらないこと
（暫定・要確認）
- 挙動の変更（判定の追加、緩和、削除。誤検出の修正も含む）
- CLI の入口（`origin/main` と比べて PR 全体を検査するコマンド）。段階3
- CI への組み込み、件数・AC番号・Makefile の比較。段階3
- Bash 解析の削除（sandbox が使えないので、行わない）
- `permissions.deny` による `.claude/hooks/**` の保護（段階4から。UNLOCK が効かなくなるため）
- `settings.json`、`CLAUDE.md`、`specs/README.md` の変更
- テストの書き換え、削除、追加

## 制約
（暫定・要確認）
- `.claude/**` は保護対象。人間が UNLOCK を置いてから編集する。終わったら外す
- 使い捨ての作業コピーで組み立てて、検証してから、本物にコピーする（0011 と同じ）
- 変更は小さくコミットを分ける。各コミットで、`make check` が通る
- 純粋関数は、標準ライブラリだけを使う
