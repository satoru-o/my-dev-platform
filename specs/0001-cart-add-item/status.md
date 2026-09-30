---
id: 0001
slug: cart-add-item
status: done # draft | clarifying | planned | red | green | done
size: S1 # AI暫定・要確認
risk: [] # 価格計算は範囲外のため、リスクタグなし（AI暫定・要確認）
---

# 0001 cart-add-item の状態

## いま
done（G3で人間が確認済み）。変更は /req-fb（FB）で。

## 結果
（done時に人間が確認して確定）
- 実装: `src/cart_api/main.py`（FastAPI、メモリ上のカート、商品マスタ p1〜p3、数量1〜99）
- テスト: `tests/test_add_item.py` 16件（parametrize含む）。`make check`（ruff・pyright・pytest）通過
- Red/Greenの流れ: 8件の計画のうち、Redを確認してGreenにしたのは7件。残り1件（AC-1 別商品の追加順）は、1件目の実装が先に満たしていて一度もRedにならなかった
- 途中の発見: pydanticは数量の `"2"` を整数に自動変換して201にしていた（V-03）。厳密モードで422にした。FastAPI標準の422は `detail` 形式で、O-01/X-04に反していた
- 気づき: `_catalog/viewpoints.md` への追加案（人間の承認が必要）: 「文字列の数値を黙って受け入れる（型の自動変換）」をV-03の例に足す
- 未対応: `httpx` のStarlette非推奨警告（`httpx2` を入れよとのこと）。pip-audit・秘密情報スキャンは未導入
