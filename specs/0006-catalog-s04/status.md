---
id: 0006
slug: catalog-s04
kind: chore # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: green # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: chore は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない）
---

# 0006 catalog-s04 の状態

## いま
G3待ち。下の「結果（AI下書き）」と、`specs/_catalog/viewpoints.md` の差分（1行）を見て、よければ done にしてください。UNLOCK は外した（ロック済み）。

## 結果
（AI下書き。done時に人間が確認して確定）
- 変更: `specs/_catalog/viewpoints.md` に S-04 を1行追加（状態の節、S-03 の次。文面は、人間が選んだ「案（由来つき）」）。`specs/0001-cart-add-item/test-plan.md` の「提案中の観点」を「カタログに追加済み」に直した。
- 確認: `make check` 終了コード0（163件）。カタログの差分は追加の1行だけ。既存の観点は13行のまま（V 4、S 3、X 4、O 2）、S-04 の重複なし。変更ファイルは、カタログ、0001 の test-plan、0006 だけ。UNLOCK を外したあと、保護対象への書き込みが拒否されることを確認した。
- 他のファイルに、S-04 を「提案中・追加待ち」と書いた記述が残っている（今回は変更範囲の外）: `docs/CHARTER.md`（成功の見方の判定の留保、次の一歩）、`specs/0001-cart-add-item/status.md`（FB 2 の保留）。`docs/experiments/mutation-0001.md` は、当時の記録なので、そのままでよい。
