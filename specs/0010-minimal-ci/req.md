# 0010 minimal-ci

<!-- このファイルは「要求事項」だけを書く。status・size・risk・kind は status.md、質問・FB は discussion-log.md -->

## やりたいこと
push時に make check を回すだけのGitHub Actionsを足す。あとで AST・件数・AC番号の比較を足せる形にする。

## 受け入れ条件
<!-- kind: chore のため、具体例の表は無し。確認項目を並べる。出典: [人]=人間が自分で述べた、[案→承認]=AIの案を人間が選んだ -->

- 既存テストが全件通る（`make check` が終了コード0） [案→承認]
- push 時に GitHub Actions が `make check` を実行し、Actions で緑になる [人]
- あとで AST・件数・AC番号の比較を足せる形にする。CI の検査は `make` のターゲット経由にして（workflow に検査の中身を直接書かない）、検査の追加が workflow の変更を要しないようにする [人]
- 赤くなることも確かめる。わざと失敗させた push（使い捨てブランチ）で、Actions が赤になる [案→承認]

## 根拠（依存の追加）
GitHub Actions が使う外部の action と、取得元。AI の案で、取得内容は要約（実際の確認は `/req-run` で行い、URL とコミットSHAを書く）。
- `actions/checkout`: <https://github.com/actions/checkout>
- `astral-sh/setup-uv`: <https://github.com/astral-sh/setup-uv>
- 採用するタグとコミットSHA（`git ls-remote` で取得。2026-10-01。どちらも軽量タグで、タグのSHAがそのままコミットSHA）
  - `actions/checkout` v6.1.0 = `d23441a48e516b6c34aea4fa41551a30e30af803`
  - `astral-sh/setup-uv` v10.2.0 = `c18668ad3cf93ea998bef934396af7bb5c839dc7`
- [X] 上の取得元と、SHA固定で使うことを確認した

## やらないこと
（暫定・要確認）
- `origin/main` との比較（AST、件数の非減少、AC番号の対応）。次の req
- pre-push hook、ブランチ保護、必須チェック（非公開の Free プランでは使えない）。マージの前に赤を見ないのは、運用で守る
- `src/`、`tests/`、`Makefile` の変更
- push 以外のトリガー（pull_request、schedule）

## 制約
（暫定・要確認）
- workflow の権限は `contents: read` のみ。シークレットは使わない
- 外部の action は、タグでなくコミットSHAで固定する（サプライチェーン対策）
- `.github/**` は保護対象。人間が UNLOCK を置いてから編集する
- 実行時間は、`make check` が、ローカルで約30秒。CI も数分以内
