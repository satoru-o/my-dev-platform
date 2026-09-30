from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI()

    @app.post("/carts/{cart_id}/items")
    def add_item(cart_id: str) -> dict:
        return {}

    return app
