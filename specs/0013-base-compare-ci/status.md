---
id: 0013
slug: base-compare-ci
kind: feature # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: red # draft | clarifying | planned | red | green | done
size: S2 # 暫定・要確認（hook の検査を、CI に広げる。品質の優先順位は、セキュリティが最上位なので、S2（カタログの全行）を提案）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし、守りの仕組みなので、検出できないこと・誤検出を、特に重く見る）
---

# 0013 base-compare-ci の状態

## いま
green（実装は一通り終わった）。G3 の前に、人間にお願いしたいことが2つある。(1) `! touch .claude/ALLOW_TEST_CHANGE`（`tests/test_base_compare_cli.py` の import の並び順を1行直すため。lint が1件落ちている。下の「気づき」1）。(2) GitHub 上の動作確認（push して PR を開き、ラベルの動きを見る。下の「確認していないこと」）。そのあと、done にしてよいか返してください。UNLOCK は、外してかまいません。

## 結果

### 何を作ったか
- `src/base_compare/`（新規）: `core.py`（検出と緑・赤の判定。0012 の `change_reason_for` をそのまま使う。承認ラベル、「比較できない」の種別、ツール自身の失敗）、`gitio.py`（`git diff` の読み取り、merge-base、危険な文字列のパスも安全に扱う）、`collect.py`（`pytest --collect-only` でIDを集める。2回収集して一致を確かめる）、`report.py`（要約。50件まで）、`cli.py`（入口 `python -m base_compare --base --mode ci|local --labels`）。
- `.github/workflows/check.yml`: `pull_request`（opened / synchronize / reopened / labeled / unlabeled）でも動く。job は3つ: `check`（`make check`）、`unlabel`（新しいコミットで承認ラベルを外す。書き込み権限 `pull-requests: write` はここだけ。PR のコードは取得しない）、`compare`（`origin/main` と比べる。`unlabel` の後。ラベルは実行時に API で読み直す。新しいコミットのときは、残っているラベルを無いものとして扱う）。
- `Makefile`: `compare`（ローカルは警告だけ）を足し、`make check` に含めた。
- `pyproject.toml`: pyright の `extraPaths`（`src` と `.claude/hooks`）、tests の lint で、一時リポジトリでの git 呼び出し（S108、S603、S607）を許可。

### 確認した項目
- テスト: 341件 → 393件（新しい52件）。`make typecheck test audit secrets compare` が通る。`make lint` は1件落ちている（気づき1）。
- **実際のリポジトリの複製で、検出すべき変更に通した**（使い捨ての複製。元は変えていない）: (1) この作業ブランチを `origin/main` と比べると、`.github/workflows/check.yml` と `Makefile` の変更が検出され、ラベルなしで終了コード1、両方のラベルで0、(2) 既存のテストの期待値を書き換えると検出され、`test-change-approved` で0、(3) テストを1つ消すと、定義の消失とIDの消失の両方が検出、(4) pytest の設定で hook のテストを収集から外すと、設定の変更と、外れたテストID（数百件。要約は50件までに切り詰め）が検出。
- hook の「構文エラー、巨大なファイル、`tool = 1`」は、`change_reason_for` の結果をそのまま使い、例外は「ツール自身の失敗」（承認でも赤）にした。
- テストの種類: Red を確認したテスト（`AssertionError`）と、「網」のテスト（既存の実装がすでに満たすので Red が無いもの。コミットメッセージに明記）がある。

### 気づき（人間の確認がほしい）
1. **lint が1件落ちている**: `tests/test_base_compare_cli.py` の import の並び順（`I001`）。Red のコミットの前に `make lint` を回さなかった私のミス。コミット済みのテストなので、直すには `.claude/ALLOW_TEST_CHANGE` が要る（hook が、テストの書き換えとして止める）。直すのは、import の2行の順序だけ（assert は変えない）。お願い: `! touch .claude/ALLOW_TEST_CHANGE`。
2. **Q9 の「構文エラーは承認で通せる」は、CI では実現できていない**: 構文エラーのテストがあると、`pytest --collect-only` 自体が失敗し、「収集に失敗した」というツール自身の失敗（承認でも赤）になる。比較の関数は「検出（承認可）」を返す（core のテストで確認済み）が、収集の失敗が先に起きる。意図して壊れたテストを承認で通す場面は、まず無く、壊れたテストは `make test` も落ちるので、このままにした。違う扱いがよければ、教えてください。
3. **ID の数が多いときの要約**: 実際に試したら、hook のテスト（約300件）が収集から外れただけで、数百行になったので、50件までに切り詰めた（Red から追加）。
4. `gh api ... || true`（ラベルを外す job）は、失敗しても続ける。ただし、`compare` は、新しいコミットのとき、ラベルを無いものとして扱うので、外れなかった古いラベルで通ることはない。
5. pyright の `extraPaths` を書くと、`src` の自動検出が消えて、typecheck が壊れた（直前のコミットで気づき、`src` も書いて直した。コミット `f6d6c6b`）。
6. このブランチ自身が、守りの仕組み（`.github/**`、`Makefile`、`.claude/**`、`tools/guard-equiv/**`）を変えている。PR を開くと、`guard-change-approved` が要る（検査の最初の実例になる）。
7. ローカルの `origin/main` が古い（0011・0012 を push していない）ので、`make compare` は、その分も警告に出す。push すれば出なくなる。

### 確認していないこと（GitHub 上でしか確かめられない）
- Actions 上の動作: `unlabel` → `compare` の順序、ラベルを API で読めること、ラベルを付けた・外したときの再実行、新しいコミットでラベルが外れること、`pull-requests: read` で足りること。手順: ブランチを push → PR を開く（`gh` が無いので、画面から）→ 検出で赤 → 画面でラベルを付けて緑 → 新しいコミットを push してラベルが外れ、赤に戻る。
- `gh pr create --label` の deny などの `settings.json` の設定（この req の外。別の小さな req）。それが入るまでは、承認ラベルの安全性は足りない。
- 工程の説明: Red を確認できないテスト（網）は、`discussion-log.md` の AI案ではなく、コミットメッセージに理由を書いた。
