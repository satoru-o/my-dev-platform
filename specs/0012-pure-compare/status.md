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
req.md を起こした（draft）。**最初の質問（振る舞いは変わるか）と、範囲の2つの質問（CLI は段階3、道具は入れる）に、返事がなかった**ので、私の推奨（変わらない=refactor、CLI は段階3、道具は `tools/guard-equiv/` に入れる）を、そのまま暫定案にした。受け入れ条件の全部と、「やらないこと」「制約」が、AI の暫定案です。確認して、OK か修正を返してください。作業の前に、UNLOCK（外していれば、`! touch .claude/UNLOCK`）。そのあと `/req-run 0012`。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
