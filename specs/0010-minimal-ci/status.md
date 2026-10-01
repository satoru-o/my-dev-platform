---
id: 0010
slug: minimal-ci
kind: chore # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: draft # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: chore は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし CI は、シークレットを持たせない）
---

# 0010 minimal-ci の状態

## いま
req.md を起こした（draft）。「やらないこと」「制約」と、根拠の取得元は AI の暫定案です。確認して、OK か修正を返してください。作業の前に、`! touch .claude/UNLOCK`（`.github/**` のため）。そのあと `/req-run 0010`。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
