---
id: 0013
slug: base-compare-ci
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: draft # draft | clarifying | planned | red | green | done
size: S2 # 暫定・要確認（hook の検査を、CI に広げる。品質の優先順位は、セキュリティが最上位なので、S2（カタログの全行）を提案）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし、守りの仕組みなので、検出できないこと・誤検出を、特に重く見る）
---

# 0013 base-compare-ci の状態

## いま
req.md を起こした（draft）。最初の質問（振る舞いは変わるか）に返事がなかったので、a（変わる=feature）としました。受け入れ条件は、状況だけ AI が起こし、期待値は全部 ⚠️ 未回答です。`/req-run 0013` で、選択肢つきの質問（推奨つき）にします。人間は、選ぶだけです。UNLOCK は、いまは要りません（`.claude/**`、`.github/**` を触るのは、実装のとき）。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
