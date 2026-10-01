---
id: 0001
slug: cart-add-item
status: green # draft | clarifying | planned | red | green | done
size: S1 # AI暫定・要確認
risk: [] # 価格計算は範囲外のため、リスクタグなし（AI暫定・要確認）
---

# 0001 cart-add-item の状態

## いま
G3待ち。FB 2（mutation 実験で見つかったテストの穴、エラーの code の契約）に対応し、green。下の「結果」の FB 2 の項目と、`tests/test_add_item.py` の差分を見て、よければ done にしてください。

## 結果
（done時に人間が確認して確定）
- 実装: `src/cart_api/main.py`（FastAPI、メモリ上のカート、商品マスタ p1〜p3、数量1〜99）
- テスト: `tests/test_add_item.py` 16件（parametrize含む）。`make check`（ruff・pyright・pytest）通過
- Red/Greenの流れ: 8件の計画のうち、Redを確認してGreenにしたのは7件。残り1件（AC-1 別商品の追加順）は、1件目の実装が先に満たしていて一度もRedにならなかった
- 途中の発見: pydanticは数量の `"2"` を整数に自動変換して201にしていた（V-03）。厳密モードで422にした。FastAPI標準の422は `detail` 形式で、O-01/X-04に反していた
- 気づき: `_catalog/viewpoints.md` への追加案（人間の承認が必要）: 「文字列の数値を黙って受け入れる（型の自動変換）」をV-03の例に足す
- 対応済み（のちに）: `httpx2` への置き換え、pip-audit・秘密情報スキャンの導入
- FB 2（2026-10-01）: mutation 実験で見つかったテストの穴を塞いだ。テストを14件足した（16 → 30 件）: AC-3 カートの独立（2件）、AC-4 合算の境界（3件）、AC-5 p3（1件）、エラーの `code` の契約（8件。`product_not_found`、`invalid_request`、`quantity_exceeded`。`message` は固定しない）。実装は変更していない。足した14件は、すべて今の実装で通った（穴はテストにあった）ので、Red にならない「退行の網」。`make check` 通過（163件）。
- FB 2 の確認: mutation の測定用コピーで回し直し、検出が 44件（73%）→ 53件（88%）に増えた。生存の7件は、すべて `message` の変更（固定しないと決めたもの）。手で壊した p3 の削除、検証エラーの `code` も検出された。記録は `docs/experiments/mutation-0001.md` の末尾。
- FB 2 の保留: 観点カタログへの S-04（別の対象が互いに影響しない）の追加は、`_catalog/` が AI の編集対象外のため提案のまま。
