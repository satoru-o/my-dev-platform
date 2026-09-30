---
name: req-run
description: specs/NNNN-slug の status を見て次の一手を進める（質問→test-plan→Red/Green/Refactor）。/req-run <id> で手動起動する。
disable-model-invocation: true
argument-hint: <id>
---

要望を1段階進める。引数: `$ARGUMENTS`（NNNN。例 `0001`）。
ルールの正本は `specs/README.md`。迷ったらそれに従う。

## 0. 準備
1. `specs/$ARGUMENTS-*/req.md` を読む（無ければ止まる）。frontmatter の `status` / `size` / `risk` を確認する。
2. **既存テストを全部実行する**: `make test`。ただしテストが0件（`tests/` に `test_*.py` が無い）ならスキップしてそう報告する。
   - 失敗があれば、そこで止まって報告する。直さない。
3. 既存テストの変更が必要になったら、勝手に直さず `questions.md` に質問として書いて止まる。

## 1. status別の動き

### draft
1. req.md が「明確」か判断する。明確の条件: すべてのACに、人間が書いた具体例が2つ以上ある／「やらないこと」が書かれている／用語の解釈が一意。
2. **曖昧なら**: `specs/_templates/questions.md` を元に `questions.md` に Round を書き、`status: clarifying` にして **止まる**。
   - 1ラウンド最大5問。各質問は「シナリオ + 選択肢 + 推奨 + 推奨の理由」。
   - 質問は、具体例が足りないACと、カタログ観点から浮かぶ仕様の穴に絞る。
3. **サイズとリスクの提案**: req.md の `size` / `risk` を提案値に更新し、「AI提案・要確認（G1）」と明記して伝える。リスクタグ（お金/個人情報/認証/データ削除）に該当しうるなら、理由を添えて指摘し、該当すれば size を1段上げ X-01〜X-04 を必須にする。
4. **明確なら**: S0 は `status: planned` にして「テスト1件目へ」。S1以上は test-plan へ（下記）。

### clarifying
- `questions.md` の最新Roundの回答を読む。**未回答は推奨を採用**して進み、採用したことを `questions.md` の該当行に「（推奨を採用）」と追記する。
- 回答を req.md の受け入れ条件・制約に反映する（期待値は人間の回答・例のみから。AIが作らない）。
- まだ曖昧なら次のRoundを積んで止まる。明確になれば `draft` の手順3以降へ。

### test-plan（S1以上、status が draft/clarifying から明確になった後）
1. `specs/_catalog/viewpoints.md` を読み、`specs/_templates/test-plan.md` を元に `specs/NNNN-slug/test-plan.md` を書く。
   - S1: 10行程度。効く観点だけ。S2: カタログの全行を評価する。
   - 観点ごとに1行: 観点 | 適用/適用しない | 具体例 | 理由 | 対応するAC。
   - 「適用しない」には必ず理由を書く。リスクタグ付きは X-01〜X-04 を「適用しない」にしない。
   - **具体例の期待値は req.md の人間の例から取る**。カタログ観点から新しい期待値が要る場合は、空欄にして、`questions.md` の新しいRoundに質問として書き、人間に聞く（迷いどころを test-plan には書かない）。
   - 自信のない行には `⚠️` を付け、その理由と選択肢は `questions.md` の新しいRoundに「シナリオ + 選択肢 + 推奨 + 推奨の理由」で書く。
2. `status: planned` にはしない。**G2で止まる**: 「適用しない」の理由と `⚠️` の行、および `questions.md` の新しいRoundの質問だけを人間に見せ、承認を待つ。承認後に `status: planned`。

### planned → red → green（1件ずつ）
1. test-plan（S0はAC）から**次の1件だけ**選ぶ。複数件を一括生成しない。
2. **Red**: そのテストを `tests/` に書き、`make test` で実行する。
   - 合格のRed = **assertionでの失敗**（`AssertionError`）。
   - `ImportError` / `ModuleNotFoundError` / `SyntaxError` / 収集エラー / fixture未定義 での失敗は **不合格**。先に最小のスタブ（関数の骨組みだけ、戻り値は誤った値）を `src/` に作り、assertionで落ちるようにする。
   - Redを確認したら `status: red`。
3. **Green**: テストを通す**最小の実装**を `src/` に書く。この間 `tests/` は編集しない。テストが間違っていると思ったら、編集せず `questions.md` に書いて止まる。
   - 期待値をテストや実装から逆算して変えない。
   - `make test` が全件通れば `status: green`。
4. **Refactor**: 重複除去など。テストは変えない。`make test` が緑のまま。
5. 時刻・乱数は引数や依存注入で外から渡す。外部依存はモックにする。
6. 次の1件があれば 2. に戻る。無ければ、機械チェック（`make check` があれば実行）を行い、結果を req.md の「結果」に下書きして **G3（done）で止まる**。`done` にするのは人間の確認後。

## 共通の約束
- 期待値の出所は人間の例だけ。
- 止まるときは、何が必要か（質問・承認・失敗の内容）を1〜3行で伝え、次に打つコマンド（例 `/req-run 0001`）を示す。
- `CLAUDE.md`、`.claude/**`、`.github/**`、`specs/README.md`、`specs/_catalog/**` は編集しない。
- バグを見つけたら、直す前に再現テストを足す。観点カタログへの追加は提案するだけにする。
