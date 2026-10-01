---
id: 0013
slug: base-compare-ci
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: clarifying # draft | clarifying | planned | red | green | done
size: S2 # 暫定・要確認（hook の検査を、CI に広げる。品質の優先順位は、セキュリティが最上位なので、S2（カタログの全行）を提案）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし、守りの仕組みなので、検出できないこと・誤検出を、特に重く見る）
---

# 0013 base-compare-ci の状態

## いま
clarifying（G2 待ち）。Round 1 の5問の回答を `req.md` に反映し（`### AI回答（Round 1）`）、`test-plan.md`（S2、カタログ14行）を書いた。見てほしいのは、(1) test-plan の「適用しない」の理由（O-02 の1行だけ）と `⚠️` の行（S-01、S-04、X-01、O-01）、(2) `discussion-log.md` の Round 2（Q6〜Q9。**答えなくてよい。答えなければ推奨で進む**）、(3) size S2（暫定・AI提案・要確認）。承認したら `/req-run 0013`（planned にして、テスト1件目から）。UNLOCK は、実装に入る前に、`! touch .claude/UNLOCK`（`.github/**` を触るため）。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
