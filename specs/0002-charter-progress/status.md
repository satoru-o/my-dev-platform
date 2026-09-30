---
id: 0002
slug: charter-progress
kind: chore # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: done # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: chore は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない）
---

# 0002 charter-progress の状態

## いま
done（G3で人間が確認済み）。変更は /req-fb（FB）で。

## 結果
（done時に人間が確認して確定）
- 変更: `docs/CHARTER.md` だけ（方針・スコープ・順序の本文は変更なし）。追加したのは、マイルストーンの進捗表（根拠つき）、成功の見方の判定表、次の一歩（候補、順序は未決）。
- 確認: `make check` 終了コード0、既存テスト103件通過。根拠に挙げたパス6つの存在、数字（0001: done・16件、hook テスト87件、リモート0、skill 3つ、履歴ディレクトリ15）を実物と照合して一致。変更ファイルは CHARTER と 0002 の status.md だけ。
- 判定の留保（CHARTER にも明記）: M0 は履歴が「見える」ことまで（`/resume` での再開は未確認）。hook は登録済みだが、実際に止まるかは未確認。「docs系PRが人手なしでマージ」は未達。
- 気づき: 前回の CHARTER 改訂で、私が M0 を根拠なしに「完了」と書いていた。今回、コンテナの `~/.claude` のマウントと履歴ディレクトリ15件を確認して根拠を足した。
