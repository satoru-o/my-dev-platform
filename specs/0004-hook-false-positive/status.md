---
id: 0004
slug: hook-false-positive
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: draft # draft | clarifying | planned | red | green | done
size: S1 # 暫定・要確認（1つの判定ロジックの修正。拒否側の退行を防ぐテストが要る）
risk: [] # 暫定・要確認（タグには当たらない。ただしセキュリティ装置の変更なので、「拒否すべきものが通る」退行が最大の懸念。ACの拒否側で守る）
---

# 0004 hook-false-positive の状態

## いま
「やらないこと」「制約」（暫定）と、size / risk（暫定）を確認してください。OK か修正を返してもらえれば、`/req-run 0004` で進めます。進める前に、保護対象の編集に備えて、人間が `! touch .claude/UNLOCK` を実行します。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
