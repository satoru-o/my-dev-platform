# 0009 sandbox-feasibility-record

<!-- このファイルは「要求事項」だけを書く。status・size・risk・kind は status.md、質問・FB は discussion-log.md -->

## やりたいこと
段階0の記録を docs/experiments/sandbox-feasibility.md に残す。bwrapと弱いモードの結果、公式ドキュメントの要点（出典URLつき）、実験用 tests/ をhookが誤認した件（Bash解析の弱点の実例。段階6の誤検出の候補）を含める。

## 受け入れ条件
<!-- kind: chore のため、具体例の表は無し。確認項目を並べる。出典: [人]=人間が自分で述べた、[案→承認]=AIの案を人間が選んだ -->

- 既存テストが全件通る（`make check` が終了コード0） [人]
- `docs/experiments/sandbox-feasibility.md` に、次が含まれる [人]
  - bwrap の最小起動と、`enableWeakerNestedSandbox` を足した再試行の結果（どちらも「ユーザー名前空間が作れない」で失敗し、安全側に倒れて全コマンドが拒否された）
  - 公式ドキュメントの要点（既定は警告のみで sandbox なしに続行、`failIfUnavailable`、Edit/Write は sandbox を通らない、`.git/hooks` と `.git/config` は保護、弱いモードの対象）と、出典のURL
  - 実験用の `tests/` という名前を、hook がリポジトリの `tests/` と誤認して止めた件（Bash解析の弱点の実例。段階6の誤検出の候補として明記）
  - 結論と、代替（B: 結果を比べる層を主役にする）への切り替え
- 公式ドキュメントの要点は、取得した要約なので、人間の確認が要る [案→承認]
  - [ ] 出典URLと要点を確認した

## やらないこと
（暫定・要確認）
- `src/`、`tests/`、`.claude/**` の変更（記録だけ）
- sandbox の設定の導入（動かないため。段階4は B で進める）
- 誤検出の修正（段階6で扱う）

## 制約
（暫定・要確認）
- 数値と挙動は、実際に実行した結果だけを書く。推測は、推測と明記する（例: 拒否の原因がコンテナ側の設定だという点）
