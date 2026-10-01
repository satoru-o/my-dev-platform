---
id: 0011
slug: split-guard
kind: refactor # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: draft # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: refactor は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし、hook は、守りの仕組みなので、判定が同一であることを、機械で確かめる）
---

# 0011 split-guard の状態

## いま
req.md を起こした（draft）。受け入れ条件の2〜6つ目、「やらないこと」「制約」、分け方は AI の暫定案です。確認して、OK か修正を返してください。作業の前に、`! touch .claude/UNLOCK`。そのあと `/req-run 0011`。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
