---
id: 0010
slug: minimal-ci
kind: chore # feature | chore | refactor（/req-new の最初の質問で決まる。振る舞いが変わらないなら chore か refactor）
status: planned # draft | clarifying | planned | red | green | done
size: S0 # 暫定・要確認（kind: chore は S0）
risk: [] # 暫定・要確認（お金・個人情報・認証・データ削除のいずれにも該当しない。ただし CI は、シークレットを持たせない）
---

# 0010 minimal-ci の状態

## いま
planned。`.github/workflows/check.yml` を書いた（ローカルで、`make check` と YAML の構文は確認済み）。残りは「Actions で緑」と「わざと失敗させて赤」の確認で、push が要る。人間の指示を待つ（ブランチ `chore/minimal-ci` を push してよいか）。

## 結果
<!-- done時に記入: 何ができたか、テスト件数、気づき -->
