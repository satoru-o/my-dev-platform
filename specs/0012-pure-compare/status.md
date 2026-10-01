---
id: 0012
slug: pure-compare
kind: refactor # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: draft # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: refactor は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし hook は守りの仕組みなので、判定が同一であることを、機械で確かめる）
---

# 0012 pure-compare の状態

## いま
req.md を起こした（draft）。人間が「暫定案で進めてよい」と返し、4点（責務の線引き、新規・削除・内容不明の扱い、解析しきれない入力、道具の基準と段階4への申し送り）を足すよう指示した。足した。新規・削除・内容不明の扱いは、AI が決めた案です（req.md の該当箇所）。確認してください。UNLOCK は、人間が置く。そのあと `/req-run 0012`。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
