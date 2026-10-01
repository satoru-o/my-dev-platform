---
id: 0009
slug: sandbox-feasibility-record
kind: chore # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: done # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: chore は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない）
---

# 0009 sandbox-feasibility-record の状態

## いま
done。G3 確認済み。次は最小 CI（`/req-new minimal-ci`）。

## 結果
- `docs/experiments/sandbox-feasibility.md` を書いた（bwrap と弱いモードの結果、公式ドキュメントの要点と出典URL、hook の誤認2件、結論と代替 B）。
- 確認: `make check` が通る（341 passed、pip-audit、detect-secrets）。コード、テスト、保護対象は変更なし。
- 未確認: req の人間チェック `[ ]`（出典URLと要点の確認）は、人間がする。
- 気づき: 誤認の実例が2件になった（実験用の `tests/` という名前、`sed -i` の置換文に保護パスの語）。段階6の候補。
