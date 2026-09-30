.PHONY: test check lint typecheck audit secrets mutate

# テストはこの1発（tests/ と、hookのテスト .claude/hooks/）。0件のときは何もしない（pytestのexit 5を成功扱いにする）
test:
	uv run pytest -q tests .claude/hooks || [ $$? -eq 5 ]

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run pyright

# 依存の既知の脆弱性を調べる（PyPIの脆弱性DBに問い合わせるため、ネットワークが要る）
audit:
	uv run pip-audit --progress-spinner off

# gitで管理しているファイルに、秘密情報（鍵・トークン・パスワード等）が無いか調べる
# 誤検出は、その行に `# pragma: allowlist secret` を付けて許可する
secrets:
	git ls-files -z | xargs -0 uv run detect-secrets-hook  # pragma: allowlist secret

# 実験用: mutation testing（常設しない。機能がdoneになったあとに1回。結果の読み方は docs/experiments/mutation-0001.md）
mutate:
	uv run mutmut run
	uv run mutmut results

# 機械チェック一式
check: lint typecheck test audit secrets
