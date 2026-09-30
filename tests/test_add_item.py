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
