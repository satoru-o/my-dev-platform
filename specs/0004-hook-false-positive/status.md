---
id: 0004
slug: hook-false-positive
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: red # draft | clarifying | planned | red | green | done
size: S1 # 暫定・要確認（1つの判定ロジックの修正。拒否側の退行を防ぐテストが要る）
risk: [] # 暫定・要確認（タグには当たらない。ただしセキュリティ装置の変更なので、「拒否すべきものが通る」退行が最大の懸念。ACの拒否側で守る）
---

# 0004 hook-false-positive の状態

## いま
Red 1件（FB 1: bash <<< の here-string）。他の7件は今の実装でも通る（網）。guard.py を直して Green にする。UNLOCK は置かれている。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
