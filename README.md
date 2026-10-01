# my-dev-platform

個人ラボ。**AI駆動の軽量な開発フロー（TDD × スペック駆動）を試す実験場**です。
人間の仕事は「具体例を出す」と「選ぶ」だけ。書く作業はAI、確認は機械、という分担を目指しています。

> 先に読むもの: **[docs/retrospective-2026-10.md](docs/retrospective-2026-10.md)**（振り返り）。
> 現時点では、製品（カートAPI）よりも、それを守る仕組みのほうが大きくなっています。この README は、その現状を、そのまま説明します。

## いまの状態（2026-10-01 時点）

| 項目 | 内容 |
| --- | --- |
| 製品コード | カートAPI（FastAPI）。「商品を追加する」1機能だけ（`src/cart_api/main.py`、60行。テスト30件） |
| 開発フロー | 要望（req）→ 質問 → テスト計画 → Red → Green → 完了確認。3つの skill と、`specs/` で動く |
| 守りの仕組み | 既存のテストを黙って書き換えさせない hook、`origin/main` と比べる CI の検査 |
| 実験の記録 | mutation testing、監査エージェント、sandbox の実現可能性（`docs/experiments/`） |
| 完了した req | 0001〜0013（`specs/` に、要望・議論・結果が全部残っている） |
| 凍結・未着手 | `gh` の導入と `settings.json` の `permissions`、段階4（`permissions.deny`）、CLAUDE.md・specs/README への反映 |

## 3行でわかるフロー

1. **`/req-new <slug>`**: 要望の雛形を作る（振る舞いが変わるか、で feature か chore に分ける）。
2. **`/req-run <NNNN>`**: 次の一手を進める。質問 → テスト計画（承認）→ Red（落ちるテスト）→ Green（最小の実装）→ 完了確認。
3. **`/req-fb <NNNN>`**: 人間のフィードバックに、AI が答えて直す。

運用のルールの正本は **[specs/README.md](specs/README.md)**、AIへの指示は **[CLAUDE.md](CLAUDE.md)**、企画は **[docs/CHARTER.md](docs/CHARTER.md)** です。

## 守りの仕組み（3層）

AI が、テストを書き換えたり、規律を回避したりしないようにする仕組みです。

| 層 | 場所 | 何をするか |
| --- | --- | --- |
| hook（書く瞬間に止める） | `.claude/hooks/guard.py` と `guardlib/`、設定は `.claude/settings.json` | 保護対象（`.claude/**`、`CLAUDE.md`、`.github/**` など）は、人間が `.claude/UNLOCK` を置くまで編集不可。進行中の req が無ければ `src/` `tests/` も不可。**既存のテストの変更・弱体化・削除は拒否**（足すのは自由）。人間が `.claude/ALLOW_TEST_CHANGE` を置くと、1回だけ通る |
| CI（あとから比べる） | `.github/workflows/check.yml` と `src/base_compare/` | PR で、`origin/main` と比べて、既存テストの変更、テスト ID の消失、守りの仕組み自体の変更を検出して赤にする。人間が PR にラベル（`test-change-approved`、`guard-change-approved`）を付けると通る。新しいコミットが載ると、ラベルは自動で外れる |
| 機械チェック（全部） | `make check` | lint、型、テスト、脆弱性（pip-audit）、秘密情報（detect-secrets）、`origin/main` との比較（ローカルは警告だけ） |

限界（正直に）: hook の Bash 解析は「ベストエフォート」で、完全な防御ではありません。CI の検査も、ブランチ内の workflow で動くので、書き換えれば消せます（ブランチ保護が使えない非公開 Free プランのため）。本当の壁は、人間の目です。

## ディレクトリ

```
.
├── CLAUDE.md                 AI への指示（入口の仕分け、守ること）
├── Makefile                  make test / check / compare ほか
├── pyproject.toml            uv、pytest、ruff、pyright の設定
├── src/
│   ├── cart_api/             製品: カートAPI（FastAPI）
│   └── base_compare/         道具: origin/main と比べる検査（CI と make compare）
├── tests/                    製品と base_compare のテスト
├── tools/guard-equiv/        道具: hook の判定が基準と同一かを確かめる（1853入力）
├── specs/
│   ├── README.md             運用ルールの正本
│   ├── _catalog/             テスト観点カタログ（V-01〜O-02）
│   ├── _templates/           req / status / discussion-log / test-plan の雛形
│   └── NNNN-slug/            1つの要望 = 1ディレクトリ
│       ├── req.md            要求事項（受け入れ条件。人間の例と、出典 [人]/[案→承認]）
│       ├── status.md         状態（draft → clarifying → planned → red → green → done）と結果
│       ├── discussion-log.md AIと人間の質問・回答・FB
│       └── test-plan.md      テストのリスト（S1以上）
├── docs/
│   ├── CHARTER.md            企画書
│   ├── retrospective-2026-10.md  振り返り
│   └── experiments/          実験の記録（mutation、監査エージェント、sandbox）
├── .claude/
│   ├── settings.json         hook の登録
│   ├── hooks/                guard.py（入口）、guardlib/（10モジュール）、test_guard.py（311件）
│   └── skills/               req-new / req-run / req-fb
├── .github/workflows/        CI（check、unlabel、compare）
└── .devcontainer/            開発コンテナ
```

## 使い方

前提: devcontainer（または Python 3.12 と [uv](https://docs.astral.sh/uv/)）。

```bash
uv sync                # 依存を入れる
make test              # テスト（製品 + hook のテスト。0件でも成功）
make check             # lint、型、テスト、脆弱性、秘密情報、origin/main との比較
make compare           # origin/main と比べる検査だけ（ローカルは警告のみ）
```

カートAPI は、まだ起動用の設定（uvicorn など）を入れていません。動作は `tests/test_add_item.py`（FastAPI の TestClient）で確かめます。

仕様の進め方（Claude Code 上で）:

```
/req-new <slug>        要望を起こす
/req-run <NNNN>        次の一手へ（質問 → テスト計画 → Red → Green → 完了確認）
/req-fb <NNNN>         フィードバックに答える
```

最初にやることは、**入口の仕分け**（CLAUDE.md）: 依頼を **req**（`src/` の挙動が変わる）、**chore**（変わらない: 依存・ドキュメント・整形・リファクタ）、**探索**（使い捨ての試作）に分け、人間の確認を待ちます。

人間がやる操作（AI は代行できない）:

| やりたいこと | 操作 |
| --- | --- |
| 保護対象（`.claude/**` など）の編集を AI に許す | `! touch .claude/UNLOCK`（終わったら削除） |
| 既存テストの変更を、1回だけ許す | `! touch .claude/ALLOW_TEST_CHANGE`（1回使うと消える） |
| PR の承認ラベルを付ける | GitHub の画面から（`test-change-approved`、`guard-change-approved`） |
| マージ、`main` への push | 人間だけ（AI は作業ブランチまで） |

## 歴史（req の一覧）

| req | 内容 |
| --- | --- |
| 0001 | カートAPI「商品を追加する」＋ mutation testing で見つけた穴の FB |
| 0002〜0003, 0005 | 企画書（CHARTER）の更新 |
| 0004 | hook の誤検出の修正（heredoc、python の書き込み先、性能） |
| 0006 | 観点カタログに S-04（別の対象が互いに影響しない）を追加 |
| 0007 | 既存テストを黙って書き換えさせない hook |
| 0008 | 監査エージェントの実験（改ざん 11/11 を検出、hook は 7/11） |
| 0009 | sandbox の実現可能性の記録（この環境では動かない） |
| 0010 | 最小の CI（push で `make check`） |
| 0011 | guard.py を10モジュールに分ける（移動だけ。1753入力で判定が同一） |
| 0012 | 比較だけの純粋関数 `change_reason_for`、`tools/guard-equiv` |
| 0013 | `origin/main` と比べる検査を CI に足す（PR ラベルで承認） |

## 次にやること（人間が決める）

振り返りの提案（詳細は [docs/retrospective-2026-10.md](docs/retrospective-2026-10.md)）:

1. **道具の増築を凍結**し、カートAPIの2つ目の機能を、軽量版のフローで1回作って測る（人間の時間、経過時間、コミット数、質問数）。
2. 承認ラベルの安全性のために、`settings.json` の `permissions`（`gh pr create --label` と `gh pr edit` と `gh api` を deny など）だけは小さくやる。
3. コミット粒度（AC 単位）と、質問の形式（最大3問、推奨を出さない）の見直しを、CLAUDE.md と skills に反映する。

## 注意

- これは**個人の実験場**です。仕組みの多くは、「やってみて、重すぎた」という学びを含みます。そのまま真似するより、振り返りを先に読んでください。
- 守りの仕組み（hook、CI の検査）は、AI を縛る前提で作られています。人間の操作（UNLOCK、スイッチ、ラベル）を要する場面が多いのは、そのためです。
