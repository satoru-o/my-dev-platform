---
id: 0007
slug: test-change-guard
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: clarifying # draft | clarifying | planned | red | green | done
size: S2 # AI提案・要確認（G1）。S1 から上げた: 守る対象がテスト・pytest の設定・req.md の3つに広がり、スイッチの自動消費と git 操作の判定が加わった
risk: [] # 暫定・要確認（タグには当たらない。ただしセキュリティ装置の変更なので、「拒否すべきものが通る」退行が最大の懸念。AC-2 と、既存のテスト133件で守る）
---

# 0007 test-change-guard の状態

## いま
G1待ち。Round 1 の回答は反映済み（条件つき）。`discussion-log.md` の Round 2（Q6〜Q9: スイッチの単位、git 操作の範囲、pytest 設定、req.md の保護）に回答してください。未回答は推奨で進みます。size は S2 に上げた（AI提案・要確認）。リスクは、タグなしのまま。実装には UNLOCK が要りますが、今はまだ要りません。
