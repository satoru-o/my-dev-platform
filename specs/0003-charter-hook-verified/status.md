---
id: 0003
slug: charter-hook-verified
kind: chore # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: done # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: chore は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない）
---

# 0003 charter-hook-verified の状態

## いま
done（G3で人間が確認済み）。変更は /req-fb（FB）で。

## 結果
（done時に人間が確認して確定）
- 変更: `docs/CHARTER.md` だけ（4行ずつの差し替え。方針・スコープ・順序の本文は変更なし）。進捗表の M4（hook の確認結果）、リスク表の1行（規約→hook）、次の一歩の1項目を更新。
- 確認: `make check` 終了コード0。旧い「実際に止まるかは未確認」の記述は0件。未確認として残したのは、UNLOCK を置いた状態での書き込みの残存と、red の間の `tests/` 拒否（単体テストのみ）の2点。変更ファイルは CHARTER と 0003 だけ。
- 書いた「確認済み」の根拠は、2026-10-01 に開き直したセッションでの試行: 拒否4種（保護対象への Write、`src/` と `tests/` への Write、Bash の `touch` で保護対象を触る回り込み）、通過2種（`git status`、`make check`）、UNLOCK を外した後の再拒否。
- 気づき1: リスク表の「M2が後回しのため…」の行も、hook が動いた事実に合わせて更新した（要望の確認項目には無かったが、古い記述が残ると矛盾するため）。範囲を超えていれば戻す。
- 気づき2（hook の誤検出）: この結果を書こうとした Bash コマンドが、guard.py に誤って止められた。Python の heredoc に「ファイルを書く関数」と「保護対象のパスを含む文章」が両方あると、書き込みと判定される。保護対象ではない `specs/` への書き込みだったので、Write ツールで書き直した（回避ではなく、正規の経路）。改善案は、報告（チャット）に記載。
