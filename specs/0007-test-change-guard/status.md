---
id: 0007
slug: test-change-guard
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: draft # draft | clarifying | planned | red | green | done
size: S1 # 暫定・要確認（hook の判定の追加。拒否側の退行を防ぐテストが要る）
risk: [] # 暫定・要確認（タグには当たらない。ただしセキュリティ装置の変更なので、「拒否すべきものが通る」退行が最大の懸念。AC-2 と、既存のテスト133件で守る）
---

# 0007 test-change-guard の状態

## いま
「やらないこと」「制約」「size / risk」（暫定）を確認してください（OK か修正）。そのあと `/req-run 0007` を打つと、残る設計の判断（解除のスイッチ、「既存」の定義、Bash 経由の書き換え）を、質問として出します。
