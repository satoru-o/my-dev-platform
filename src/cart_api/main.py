from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

PRODUCTS = {"p1", "p2", "p3"}


class AddItemRequest(BaseModel):
    product_id: str
    quantity: int


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def create_app() -> FastAPI:
    app = FastAPI()
    carts: dict[str, list[dict]] = {}

    @app.exception_handler(ApiError)
    def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.post("/carts/{cart_id}/items", status_code=201)
    def add_item(cart_id: str, body: AddItemRequest) -> dict:
        if body.product_id not in PRODUCTS:
            raise ApiError(404, "product_not_found", "product not found")
        items = carts.setdefault(cart_id, [])
        for item in items:
            if item["product_id"] == body.product_id:
                item["quantity"] += body.quantity
                break
        else:
            items.append({"product_id": body.product_id, "quantity": body.quantity})
        return {"cart_id": cart_id, "items": items}

    return app
