"""git からの読み取り（`git diff` の出力の解釈、ファイルの内容の取得）。"""


def parse_name_status(out: bytes) -> list[tuple[str, str]]:
    """`git diff --name-status -z` の出力を、（状態, パス）の一覧にする。"""
    tokens = [t.decode("utf-8", "replace") for t in out.split(b"\0") if t != b""]
    return list(zip(tokens[0::2], tokens[1::2], strict=False))
