---
id: 0007
slug: test-change-guard
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: green # draft | clarifying | planned | red | green | done
size: S2 # AI提案・要確認（G1）。S1 から上げた: 守る対象がテスト・pytest の設定・req.md の3つに広がり、スイッチの自動消費と git 操作の判定が加わった
risk: [] # 暫定・要確認（タグには当たらない。ただしセキュリティ装置の変更なので、「拒否すべきものが通る」退行が最大の懸念。AC-2 と、既存のテスト133件で守る）
---

# 0007 test-change-guard の状態

## いま
Red 9件（V-04 巨大な入力、X-03 別の書き方、V-03 CRLF）が Green。test-plan の全項目を実装した。次は、docstring の更新、本物の hook での確認、結果の下書き（G3）。UNLOCK は置かれている。size は S2（AI提案。確認待ち）、リスクはタグなし。
