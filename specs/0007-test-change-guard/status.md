---
id: 0007
slug: test-change-guard
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: red # draft | clarifying | planned | red | green | done
size: S2 # AI提案・要確認（G1）。S1 から上げた: 守る対象がテスト・pytest の設定・req.md の3つに広がり、スイッチの自動消費と git 操作の判定が加わった
risk: [] # 暫定・要確認（タグには当たらない。ただしセキュリティ装置の変更なので、「拒否すべきものが通る」退行が最大の懸念。AC-2 と、既存のテスト133件で守る）
---

# 0007 test-change-guard の状態

## いま
Red 22件（Q5、Q3 Bash 経由の書き換え、AC-3 スイッチ）が Green。次は、git 操作（AC-4）、pytest の設定（AC-5）、req.md（AC-6）、巨大な入力（V-04）、別の書き方・解析しきれないもの、の順。UNLOCK は置かれている。size は S2（AI提案。確認待ち）、リスクはタグなし。
