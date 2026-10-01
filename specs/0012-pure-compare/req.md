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
- 比較の道具（0011 で使った、生成スクリプトと、1753 入力の判定比較）を、リポジトリに入れる。置き場所は暫定で `tools/guard-equiv/`（`docs/**` は自動マージの対象なので、コードは置かない）。`make check` の lint を通し、使い方を README に書く（AI暫定）

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
