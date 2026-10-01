---
id: 0008
slug: test-audit-experiment
kind: chore # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: green # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: chore は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない）
---

# 0008 test-audit-experiment の状態

## いま
green。実験は完了。G3 待ち: `docs/experiments/test-audit-0001.md` を読み、done にしてよいか、監査役を常設するか（案A 助言のみ／案B しない／案C 止める）を決めてください。

## 結果
- 15件を監査役（読み取り専用）に判定させた: 改ざん・手順違反 11/11 検出、無害 4件で誤検出 0。
- 同じ15件をガードに通した: 改ざん 7/11 を止め、4件（Makefile、テスト無し、Red 記録なし、中身の無いテスト）は止められない。無害 4件のうち 3件（B2・C2・C4）を承認待ちにした。
- 攻撃役（パート1）は、依頼を断った。人間がやめると決めた。
- 限界: 合成ケース、記録つき。常設は人間の判断。詳細は `docs/experiments/test-audit-0001.md`。
