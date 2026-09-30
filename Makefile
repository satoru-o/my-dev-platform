.PHONY: test check lint typecheck

# テストはこの1発。テストが0件のときは何もしない（pytestのexit 5を成功扱いにする）
test:
	uv run pytest -q || [ $$? -eq 5 ]

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run pyright

# 機械チェック一式（pip-audit、秘密情報スキャンは次段階で追加）
check: lint typecheck test
