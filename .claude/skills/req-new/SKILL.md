---
name: req-new
description: 新しい要望 specs/NNNN-slug/req.md を雛形から作る。/req-new <slug> で手動起動する。
disable-model-invocation: true
argument-hint: <slug>
allowed-tools: Read, Write, Glob, Bash(ls:*)
---

新しい要望の雛形を作る。引数: `$ARGUMENTS`（slug。英小文字・数字・ハイフンのみ）。

## 手順
1. `$ARGUMENTS` が slug として妥当か確認する（`^[a-z0-9]+(-[a-z0-9]+)*$`）。不正なら理由を示して止まる。
2. `specs/` 直下の `NNNN-*` を列挙し、最大のNNNN + 1 を4桁で採番する（無ければ `0001`）。同じslugが既にあれば止まって知らせる。
3. `specs/_templates/req.md` を読み、`id`、`slug`、タイトル（`# NNNN slug`）を置換して `specs/NNNN-slug/req.md` に書く。
4. 「やりたいこと」「受け入れ条件」は **空のまま**にする。AIが埋めたり、例の期待値を提案してはいけない（期待値の出所は人間の例のみ）。
5. `size` と `risk` は、ユーザーが口頭で要望を述べていれば暫定値を提案してよい。その場合は「暫定・要確認」と明記する。述べていなければ雛形のまま。
6. 最後に次の一歩だけ伝える: 「`req.md` の『やりたいこと』と、各ACの具体例（2〜3個）を書いてください。書けたら `/req-run NNNN`」。

## やらないこと
- questions.md、test-plan.md、テスト、実装を作らない。
- 既存の req.md を上書きしない。
