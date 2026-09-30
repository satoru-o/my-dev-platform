# CLAUDE.md

個人ラボ。AI駆動の軽量開発フロー（TDD × スペック駆動）の実験場。スタックは uv、pytest、ruff、pyright、hypothesis、FastAPI。品質の優先順位は **セキュリティ >= 機能的正しさ > 保守性**。人間の仕事は「具体例を出す」と「選ぶ」だけ。

運用ルールの正本は `specs/README.md`。企画は `docs/CHARTER.md`。

## 最初にやること：入口の仕分け
依頼を受けたら、作業の前に必ず、次のどれかに分類して一行で伝え、人間の確認を待つ（詳細は `specs/README.md` の「入口の仕分け」）。

- **req**: `src/` の挙動が変わる → `/req-new` から始めるよう提案する。
- **chore**: `src/` の挙動が変わらない → reqは作らず、**確認コマンドを先に宣言**してから作業する。
- **探索**: 使い捨ての試作 → 探索と宣言してから作業する。

例: 「これは chore です（依存の置き換えだけで挙動は変わらない）。確認は `make check` が通ること。この分類でよいですか」。
迷ったら req に寄せる。`src/` や `tests/` を、reqなしに編集しない。

## コマンド
- `make test`: テスト（0件でも成功）
- `make check`: lint、型、テスト、脆弱性（pip-audit）、秘密情報（detect-secrets）
- `/req-new <slug>`: 要望の雛形を作る。`/req-run <id>`: 次の一手を進める。`/req-fb <id>`: 未対応のFBに対応して、AI回答を書く

## 守ること
- 期待値の出所は、人間が書いた例だけ。実装やテストから逆算しない。
- Redは assertion での失敗だけ。`ImportError` などは不合格。テストは1件ずつ書く。
- 実装フェーズでは `tests/` を書き換えない。直す必要があれば `discussion-log.md` で聞く。
- 編集してよいのは、人間が明示的に指示したときだけ: `CLAUDE.md`、`.claude/**`、`.github/**`、`specs/README.md`、`specs/_catalog/**`。それ以外のときは、提案するだけにする。
- AIの回答は、`discussion-log.md` に書く（チャットは要約）。
- gitは、`main` に直接コミットせず、ブランチで作業する。コミットは細かく。pushは頼まれたときだけ。
