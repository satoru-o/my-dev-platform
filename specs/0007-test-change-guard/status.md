---
id: 0007
slug: test-change-guard
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: clarifying # draft | clarifying | planned | red | green | done
size: S1 # 暫定・要確認（hook の判定の追加。拒否側の退行を防ぐテストが要る）
risk: [] # 暫定・要確認（タグには当たらない。ただしセキュリティ装置の変更なので、「拒否すべきものが通る」退行が最大の懸念。AC-2 と、既存のテスト133件で守る）
---

# 0007 test-change-guard の状態

## いま
G1待ち。`discussion-log.md` の Round 1（Q1〜Q5）に回答してください。未回答は推奨で進みます。「やらないこと」「制約」「size / risk」（暫定。S1、リスクなし）の修正があれば、そちらも。実装には UNLOCK が要りますが、今はまだ要りません。
