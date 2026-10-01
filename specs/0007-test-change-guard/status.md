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
Red 21件（既存テストを HEAD と AST で比べる中核: AC-2、Q2、Q11、Q12）が Green。次は、Bash 経由の書き換え（AC-2）、スイッチ（AC-3）、git 操作（AC-4）、pytest の設定（AC-5）、req.md（AC-6）、巨大な入力（V-04）の順。UNLOCK は置かれている。size は S2（AI提案。確認待ち）、リスクはタグなし。
