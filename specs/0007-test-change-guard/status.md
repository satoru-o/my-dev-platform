---
id: 0007
slug: test-change-guard
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: planned # draft | clarifying | planned | red | green | done
size: S2 # AI提案・要確認（G1）。S1 から上げた: 守る対象がテスト・pytest の設定・req.md の3つに広がり、スイッチの自動消費と git 操作の判定が加わった
risk: [] # 暫定・要確認（タグには当たらない。ただしセキュリティ装置の変更なので、「拒否すべきものが通る」退行が最大の懸念。AC-2 と、既存のテスト133件で守る）
---

# 0007 test-change-guard の状態

## いま
実装中（planned）。Round 1〜3 の回答を反映済み（条件つき）で、test-plan の `⚠️` は無い。退行の網のテストから、1件ずつ Red → Green で進める。`guard.py` は、作業用のコピーで確かめてから、本物に反映する。UNLOCK は置かれている。size は S2（AI提案。確認待ち）、リスクはタグなし。
