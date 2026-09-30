# specs/ 運用ルール

AI駆動の軽量フロー（TDD × スペック駆動）。目的は「作る → フィードバック → 注文をつけ直す」を小さく速く回すこと。
品質の優先順位は **セキュリティ >= 機能的正しさ > 保守性**。

## 人間の仕事は2つだけ
1. **具体例を出す**（入力と期待される出力）
2. **選ぶ**（AIの質問の選択肢。test-planの迷いどころも質問として questions.md に集約する）

期待値の出所は、必ず人間の例。AIが実装やテストから期待値を逆算してはいけない。

## ディレクトリ

```
specs/
  README.md              このファイル
  _catalog/viewpoints.md テスト観点カタログ
  _templates/            req / questions / test-plan の雛形
  NNNN-slug/             4桁連番 + slug（例: 0001-cart-add-item）
    req.md               要望。frontmatterに status / size / risk
    questions.md         AIの質問と人間の回答（Round制）
    test-plan.md         S1以上のみ
```

- 採番: 既存の最大NNNN + 1。欠番は埋めない。
- フィードバックは別ファイルにせず、`req.md` に `## FB 1`、`## FB 2` と積む。
- 質問が増えたら、ファイルを分けず `questions.md` に Round を積む。

## サイズ（AIが提案し、人間が確認する）

| サイズ | 対象 | 流れ |
| --- | --- | --- |
| S0 極小 | 数行で済み、分岐がほぼ無い | 受け入れ条件 → テスト → 実装（test-planなし） |
| S1 小 | 1機能。入力の種類が少ない | 10行程度のtest-plan → テスト → 実装 |
| S2 中以上 | 状態や複数機能にまたがる | フルのtest-plan（観点カタログを全行評価） |

### リスクタグ
`お金` / `個人情報` / `認証` / `データ削除` のどれかが付いたら、
- セキュリティ観点（X-01〜X-04）を **必須（適用しないは不可）** にする
- サイズを1段上げる（S0→S1、S1→S2）

## status（コマンドはこれを見て次の動きを決める）

```
draft → clarifying → planned → red → green → done
```

| status | 意味 | 次の動き |
| --- | --- | --- |
| draft | req.mdを書いた直後 | `/req-run`: 曖昧ならquestions.mdを書いて `clarifying` へ。明確なら次へ |
| clarifying | 質問待ち | 人間が回答（答えなければ推奨で進む）→ 再度 `/req-run` |
| planned | test-plan承認済み（S0は受け入れ条件確定） | テストを1件ずつ Red |
| red | 失敗するテストが1件ある | 最小の実装で Green |
| green | 全テストが通る | Refactor → 次のテストへ。全部終われば `done` 待ち |
| done | G3で人間が確認した | 変更は `/req-fb` |

S0は `planned` を「受け入れ条件の確定」で代替する。test-planは作らない。

## TDDの規律

- 1件ずつ **Red → Green → Refactor**。テストコードを一括生成しない。
- Redと認めるのは **assertionでの失敗のみ**。`ImportError` / `ModuleNotFoundError` / `SyntaxError` / 収集エラーでの失敗は不合格（先にスタブを作って、assertionで落とす）。
- 実装フェーズでは `tests/` を書き換えない。テストを直す必要が出たら止まって `questions.md` で人間に聞く。
- 既存テストの変更が必要なときも、勝手に直さず `questions.md` で聞く。
- バグを見つけたら、直す前にテストを足す。そのバグの種類を `_catalog/viewpoints.md` に観点として足す。
- 時刻と乱数は外から渡す（引数・依存注入）。外部依存はモックにする。
- テスト実行は `make test` の1発。

## 人間のゲート

| ゲート | 見るもの |
| --- | --- |
| G1 | 受け入れ条件、具体例、質問への回答 |
| G2 | test-plan（S1以上）。全部ではなく「適用しない」の理由と、AIが迷いを示した行だけ |
| G3 | 最終の `done` |

Red、Green、機械チェックは自動。

## AIが編集してはいけないもの（hook/CODEOWNERSが入るまでは規約）
`CLAUDE.md`、`.claude/**`、`.github/**`、`specs/README.md`、`specs/_catalog/**`。
変更が必要と思ったら、編集せずに人間へ提案する。ただし「バグで観点を足す」場合の `_catalog/` への追記は、提案の形で人間の承認を得てから行う。

## やらないこと
監査用の記録、重い承認プロセス、大きな仕様書、最初から全部作り込むこと。
