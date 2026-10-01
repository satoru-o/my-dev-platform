from base_compare import gitio


def test_V03_日本語_絵文字_空白_改行を含むパスも正しく読む():
    out = (
        b"M\0tests/test_a.py\0"
        + "A\0tests/テスト_🍎.py\0".encode()
        + b"D\0tests/with space.py\0"
        + b"A\0tests/new\nline.py\0"
    )

    assert gitio.parse_name_status(out) == [
        ("M", "tests/test_a.py"),
        ("A", "tests/テスト_🍎.py"),
        ("D", "tests/with space.py"),
        ("A", "tests/new\nline.py"),
    ]
