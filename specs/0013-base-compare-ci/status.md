---
id: 0013
slug: base-compare-ci
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: green # draft | clarifying | planned | red | green | done
size: S2 # 暫定・要確認（hook の検査を、CI に広げる。品質の優先順位は、セキュリティが最上位なので、S2（カタログの全行）を提案）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし、守りの仕組みなので、検出できないこと・誤検出を、特に重く見る）
---

# 0013 base-compare-ci の状態

## いま
planned（G2 通過）。Round 2 の回答を `req.md` と `test-plan.md` に反映した（`### AI回答（Round 2）`）。test-plan は19手順。次は、テスト1件目（差分が空 → 緑）を Red から。確認してほしい AI 案が1つ: 種別のラッパーが、分類表に無い理由を受け取ったときは「比較できない」（承認でも赤）にする（`discussion-log.md` の AI回答（Round 2））。`.github/**`、`.claude/**` を触る段階で UNLOCK を使う（いまは置いてある）。次は `/req-run 0013`。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
