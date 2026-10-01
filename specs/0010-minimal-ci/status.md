---
id: 0010
slug: minimal-ci
kind: chore # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: done # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: chore は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし CI は、シークレットを持たせない）
---

# 0010 minimal-ci の状態

## いま
done。G3 確認済み。次は段階1（guard.py の分割。`/req-new` で起こす。UNLOCK が要る）。

## 結果
- `.github/workflows/check.yml` を足した。push 時に `uv sync --locked` と `make check` を実行する。権限は `contents: read` のみ。外部の action 2つ（checkout v6.1.0、setup-uv v10.2.0）は、コミットSHAで固定。
- 確認: ローカルの `make check` が通る（341 passed）。`chore/minimal-ci` を push して、Actions で緑（人間が画面で確認）。使い捨てブランチ（未使用 import を1行足した）で、Actions が赤になることも確認（人間が画面で確認）。使い捨てブランチは、リモートとローカルの両方を削除済み。
- 気づき: `gh` が無いので、Actions の結果は人間が画面で見て伝える。`fetch-depth: 0` は、あとで `origin/main` との比較を足すための準備。ブランチ保護と必須チェックは、非公開の Free プランでは使えないので、赤のままマージしないのは運用で守る。
