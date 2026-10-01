import pytest
from fastapi.testclient import TestClient

from cart_api.main import create_app


def test_AC1_初回追加でカート全体が返る():
    client = TestClient(create_app())

    res = client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 2})

    assert res.status_code == 201
    assert res.json() == {
        "cart_id": "c1",
        "items": [{"product_id": "p1", "quantity": 2}],
    }


def test_AC1_続けて別商品を追加すると追加順に並ぶ():
    client = TestClient(create_app())
    client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 2})

    res = client.post("/carts/c1/items", json={"product_id": "p2", "quantity": 1})

    assert res.status_code == 201
    assert res.json() == {
        "cart_id": "c1",
        "items": [
            {"product_id": "p1", "quantity": 2},
            {"product_id": "p2", "quantity": 1},
        ],
    }


def test_AC2_同じ商品を追加すると数量が加算される():
    client = TestClient(create_app())
    client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 2})

    res = client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 3})

    assert res.status_code == 201
    assert res.json() == {
        "cart_id": "c1",
        "items": [{"product_id": "p1", "quantity": 5}],
    }


def test_S01_存在しない商品は404でエラー形式が統一される():
    client = TestClient(create_app())

    res = client.post("/carts/c1/items", json={"product_id": "p999", "quantity": 1})

    assert res.status_code == 404
    body = res.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message"}


@pytest.mark.parametrize("quantity", [0, -1, 100])
def test_V02_数量が範囲外なら422(quantity):
    client = TestClient(create_app())

    res = client.post(
        "/carts/c1/items", json={"product_id": "p1", "quantity": quantity}
    )

    assert res.status_code == 422


def test_V02_数量99ちょうどは追加できる():
    client = TestClient(create_app())

    res = client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 99})

    assert res.status_code == 201
    assert res.json()["items"] == [{"product_id": "p1", "quantity": 99}]


def test_V02_合算が99を超えたら422でカートは変わらない():
    client = TestClient(create_app())
    client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 50})

    res = client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 50})
    after = client.post("/carts/c1/items", json={"product_id": "p2", "quantity": 1})

    assert res.status_code == 422
    assert after.json()["items"] == [
        {"product_id": "p1", "quantity": 50},
        {"product_id": "p2", "quantity": 1},
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"product_id": "p1", "quantity": "2"},
        {"quantity": 2},
        {"product_id": "p1"},
        {},
    ],
)
def test_V03_V01_型違いや必須項目の欠落は422(payload):
    client = TestClient(create_app())

    res = client.post("/carts/c1/items", json=payload)

    assert res.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"product_id": "p1", "quantity": 100},
        {"product_id": "p1", "quantity": "2"},
        {},
    ],
)
def test_X04_422のエラー本文はcodeとmessageだけ(payload):
    client = TestClient(create_app())

    res = client.post("/carts/c1/items", json=payload)

    assert res.status_code == 422
    body = res.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message"}


def test_AC3_別のカートの中身は混ざらない():
    client = TestClient(create_app())
    client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 2})

    res = client.post("/carts/c2/items", json={"product_id": "p2", "quantity": 1})

    assert res.status_code == 201
    assert res.json() == {
        "cart_id": "c2",
        "items": [{"product_id": "p2", "quantity": 1}],
    }


def test_AC3_別のカートの同じ商品の数量は合算されない():
    client = TestClient(create_app())
    client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 2})

    res = client.post("/carts/c2/items", json={"product_id": "p1", "quantity": 3})

    assert res.status_code == 201
    assert res.json() == {
        "cart_id": "c2",
        "items": [{"product_id": "p1", "quantity": 3}],
    }


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (98, 1),
        (50, 49),
    ],
)
def test_AC4_合算がちょうど99なら追加できる(first, second):
    client = TestClient(create_app())
    client.post("/carts/c1/items", json={"product_id": "p1", "quantity": first})

    res = client.post("/carts/c1/items", json={"product_id": "p1", "quantity": second})

    assert res.status_code == 201
    assert res.json()["items"] == [{"product_id": "p1", "quantity": 99}]


def test_AC4_合算が99を1でも超えたら422でカートは変わらない():
    client = TestClient(create_app())
    client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 99})

    res = client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 1})
    after = client.post("/carts/c1/items", json={"product_id": "p2", "quantity": 1})

    assert res.status_code == 422
    assert after.json()["items"] == [
        {"product_id": "p1", "quantity": 99},
        {"product_id": "p2", "quantity": 1},
    ]


def test_AC5_商品p3も追加できる():
    client = TestClient(create_app())

    res = client.post("/carts/c1/items", json={"product_id": "p3", "quantity": 1})

    assert res.status_code == 201
    assert res.json() == {
        "cart_id": "c1",
        "items": [{"product_id": "p3", "quantity": 1}],
    }


def test_Q12_存在しない商品のcodeはproduct_not_found():
    client = TestClient(create_app())

    res = client.post("/carts/c1/items", json={"product_id": "p999", "quantity": 1})

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "product_not_found"


@pytest.mark.parametrize(
    "payload",
    [
        {"product_id": "p1", "quantity": 0},
        {"product_id": "p1", "quantity": -1},
        {"product_id": "p1", "quantity": 100},
        {"product_id": "p1", "quantity": "2"},
        {"quantity": 2},
        {},
    ],
)
def test_Q12_数量の範囲外や型違いや欠落のcodeはinvalid_request(payload):
    client = TestClient(create_app())

    res = client.post("/carts/c1/items", json=payload)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_request"


def test_Q12_合算が99を超えるときのcodeはquantity_exceeded():
    client = TestClient(create_app())
    client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 99})

    res = client.post("/carts/c1/items", json={"product_id": "p1", "quantity": 1})

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "quantity_exceeded"
