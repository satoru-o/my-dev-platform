from pydantic import BaseModel

from fastapi import FastAPI


class AddItemRequest(BaseModel):
    product_id: str
    quantity: int


def create_app() -> FastAPI:
    app = FastAPI()
    carts: dict[str, list[dict]] = {}

    @app.post("/carts/{cart_id}/items", status_code=201)
    def add_item(cart_id: str, body: AddItemRequest) -> dict:
        items = carts.setdefault(cart_id, [])
        for item in items:
            if item["product_id"] == body.product_id:
                item["quantity"] += body.quantity
                break
        else:
            items.append({"product_id": body.product_id, "quantity": body.quantity})
        return {"cart_id": cart_id, "items": items}

    return app
