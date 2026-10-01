# sandbox の実現可能性（段階0。0009）

hook（guard.py）の設計見直しの段階0。「Claude Code の sandbox で、Bash からの書き込みを OS レベルで禁止できれば、Bash 解析（guard.py の約半分）を削除できる」という仮説を、この devcontainer で確かめた記録。

## 結論（先に）
- **この環境では、sandbox は動かない**（弱いモード `enableWeakerNestedSandbox` を足しても同じ）。
- よって、段階4（sandbox による Bash 書き込み禁止）は中止し、段階5（Bash 解析の削除）は行わない。
- 代替は B: 「結果を比べる層」（`origin/main` との比較: AST、件数の非減少、設定・Makefile、AC番号の対応）を主役にし、Bash 解析は残す。
- 動かなかった原因は、コンテナ側の設定（seccomp など）だという推測。ホスト側の設定は確認していない（推測）。コンテナの権限を広げて直す案（A）は、採らない。

## 実験1: bwrap の最小起動（使い捨て領域）
環境: Linux 6.6.87.2-microsoft-standard-WSL2、devcontainer、実行ユーザー `node`（uid 1000）。`/usr/bin/bwrap` と `/usr/bin/socat` は入っている。

| 確認 | 結果 |
| --- | --- |
| `bwrap --ro-bind / / --dev /dev --proc /proc true` | 失敗。`bwrap: No permissions to create a new namespace, likely because the kernel does not allow non-privileged user namespaces.` |
| `unshare -U true` | 失敗。`Operation not permitted` |
| `/proc/sys/user/max_user_namespaces` | 55473（カーネル自体は、上限を0にしていない） |

## 実験2: 弱いモードで再試行（使い捨てコピー）
設定: `sandbox.enabled: true`、`failIfUnavailable: true`、`allowUnsandboxedCommands: false`、`enableWeakerNestedSandbox: true`、`filesystem.denyWrite: ["./ro_dir"]`。`claude -p`（Claude Code 2.1.285）に、書き込み禁止の `ro_dir/` と、書き込み可の `free/` への、書き込みを1つずつ実行させた。

- **結果は実験1と同じ bwrap のエラー**で、2つとも失敗した（`free/` への書き込みも失敗）。
- ファイルは変わっていない（`ro_dir/a.txt` は元のまま、`free/` は空）。
- sandbox が黙って無効になったのではなく、`allowUnsandboxedCommands: false` のため、**全コマンドが拒否された**（安全側に倒れた）。
- 弱いモードは、公式ドキュメントでは「新しい `/proc` をマウントできない」場合の回避策として書かれている。今回の失敗（ユーザー名前空間が作れない）には効かなかった。

注意: この試行は、`claude -p` に実行させた1回だけで、決定的なスクリプトではない。「効いていることの確認」は、段階4で動く環境が得られたら、決定的なスクリプトで行う。

## 公式ドキュメントの要点
出典: <https://code.claude.com/docs/en/sandboxing>（取得日 2026-10-01。取得内容は要約。人間の確認が要る）

- Linux と WSL2 で動く。bubblewrap と socat が要る。
- **既定では、sandbox が起動できないと、警告を出して、sandbox なしでコマンドを実行する**（黙って無効になる）。`sandbox.failIfUnavailable: true` で、起動を失敗させられる。
- `sandbox.filesystem.denyWrite` / `denyRead` / `allowWrite` は、OS レベルで強制され、子プロセスにも効く。
- `allowUnsandboxedCommands: false` にしないと、`dangerouslyDisableSandbox`（sandbox なしで再実行する逃げ道）が使える。
- **Read / Edit / Write のツールは、sandbox を通らず、permissions だけで制御される**。つまり、sandbox は Bash（と子プロセス）にしか効かない。
- `.git/hooks` と `.git/config` などは、書き込み保護の対象で、`allowWrite` でも解除できない。`git merge` や `git checkout` が、保護されたファイルを置き換える場合は、失敗しうる。
- `enableWeakerNestedSandbox`: Docker 内で `/proc` をマウントできない場合の回避策。セキュリティを大きく弱めるので、外側のコンテナが隔離を提供する場合だけ使うべき、とされている。

## 実例: hook が、実験用の `tests/` を、リポジトリの `tests/` と誤認した
実験1の最初の試行で、実験用のディレクトリを `tests/` と名付けて、Bash で書き込みを試したところ、hook に止められた。

- 止められた理由: `進行中のreq（status が planned / green）がありません。tests/ はreqなしに編集できません。`
- 実際の書き込み先は、リポジトリの外（`$CLAUDE_JOB_DIR/tmp/sbx/work/tests/`）で、リポジトリの `tests/` ではなかった。
- 原因: Bash 解析は、コマンドの**文字列**から書き込み先を推定する。`tests/` という語と、書き込みの形（`echo x > …/tests/a.txt`）が揃うと、パスの実体（リポジトリの中か外か）を解決できないまま、止める側に倒す（`$D` のような変数は、解決できない）。
- このときは、実験用の名前を `ro_dir` に変えて再実行した。ガードを回避したのではなく、対象がリポジトリの `tests/` ではないことを、名前で明示した（実験の中身は変わらない）。
- 同じ日に、もう1件。0009 の `status.md` を `sed -i` で書き換えたとき、置換文の中に、保護パスの語（`src/` や `tests/` を並べた説明文）が入っていたため、止められた。書き換え先は `specs/0009-…/status.md` で、保護対象ではない。Edit ツール（パスだけで判定する）なら通った。
- **Bash 解析の弱点の実例**。「書き方を当てる」方式は、(a) 本物を見逃す（0008 でも、止められないものがあった）、(b) 無関係なものを止める、の両方が起きる。
- **段階6（誤検出の緩和）の候補**: 書き込み先が、リポジトリの外の絶対パスだと解決できる場合は、対象外にする。変数が絡む場合は、止める側のままにするか、別途決める（要検討）。

## 次の一歩
- 最小 CI（push 時に `make check`）→ 段階1（guard.py の分割。移動だけ）→ 段階2・3（純粋関数と、結果を比べる CI）。
- sandbox が使える環境が将来できたら、段階0を再実行する（`failIfUnavailable: true` を付けて、黙って無効になっていないことを、決定的なスクリプトで確かめる）。
