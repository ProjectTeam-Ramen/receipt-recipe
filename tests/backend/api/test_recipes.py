import json
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backend.api.routers import (
    recipes as recipes_router_module,  # type: ignore[import]
)
from app.backend.api.routers.auth_routes import get_current_user
from app.backend.api.routers.recipes import (
    router as recipes_router,  # type: ignore[import]
)
from app.backend.database import Base, get_db
from app.backend.models import (
    Food,
    FoodCategory,
    IngredientStatus,
    User,
    UserFood,
)
from app.backend.models.recipe import (
    Recipe,
    RecipeFood,
    UserRecipeHistory,
)  # type: ignore[import]


def _setup_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with SessionLocal() as session:
        user = User(
            user_id=1,
            username="tester",
            email="tester@example.com",
            password_hash="hash",
        )
        session.add(user)

        category = FoodCategory(category_id=1, category_name="野菜")
        session.add(category)

        food = Food(food_id=1, food_name="じゃがいも", category_id=category.category_id)
        session.add(food)

        recipe = Recipe(
            recipe_id=1,
            recipe_name="テスト肉じゃが",
            description="シンプルな肉じゃが",
            cooking_time=30,
            calories=450,
            instructions="1. 材料を切る\n2. 煮込む",
            is_japanese=True,
            is_main_dish=True,
        )
        session.add(recipe)
        session.flush()

        recipe_food = RecipeFood(
            recipe_id=recipe.recipe_id,
            food_id=food.food_id,
            quantity_g=Decimal("120"),
        )
        session.add(recipe_food)

        stock = UserFood(
            user_food_id=1,
            user_id=user.user_id,
            food_id=food.food_id,
            quantity_g=Decimal("200"),
            status=IngredientStatus.UNUSED,
        )
        session.add(stock)
        session.commit()

    return engine, SessionLocal


def _build_test_app(SessionLocal):
    app = FastAPI()
    app.include_router(recipes_router, prefix="/api/v1/recipes")

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    return app


def test_recipe_detail_includes_stock_levels():
    engine, SessionLocal = _setup_database()
    app = _build_test_app(SessionLocal)

    # inject optional current user for stock lookup
    app.dependency_overrides[recipes_router_module._optional_current_user] = (
        lambda: SimpleNamespace(user_id=1)
    )

    try:
        with TestClient(app) as client:
            resp = client.get("/api/v1/recipes/1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["recipe_name"] == "テスト肉じゃが"
            assert data["cooking_time"] == 30
            assert data["instructions"].startswith("1. 材料")
            assert data["is_japanese"] is True
            assert data["is_main_dish"] is True
            ingredient = data["ingredients"][0]
            assert ingredient["food_name"] == "じゃがいも"
            assert ingredient["quantity_g"] == 120.0
            assert ingredient["available_quantity_g"] == 200.0
            assert ingredient["missing_quantity_g"] == 0.0
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_cook_recipe_consumes_inventory():
    engine, SessionLocal = _setup_database()
    app = _build_test_app(SessionLocal)

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id=1)

    try:
        with TestClient(app) as client:
            cook_resp = client.post(
                "/api/v1/recipes/1/cook",
                json={"servings": 1},
            )
            assert cook_resp.status_code == 200
            body = cook_resp.json()
            assert body["recipe_id"] == 1
            assert body["consumed"][0]["consumed_quantity_g"] == 120.0

            detail_resp = client.get("/api/v1/recipes/1")
            assert detail_resp.status_code == 200
            ingredient = detail_resp.json()["ingredients"][0]
            assert round(ingredient["available_quantity_g"], 1) == 80.0

        with SessionLocal() as session:
            history_rows = session.query(UserRecipeHistory).all()
            assert len(history_rows) == 1
            entry = history_rows[0]
            assert getattr(entry, "recipe_id", None) == 1
            assert float(getattr(entry, "servings", 0)) == 1.0
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_static_catalog_lists_available_recipe_files(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(recipes_router, prefix="/api/v1/recipes")

    # setup fake dataset
    html_dir = tmp_path / "recipe-list"
    html_dir.mkdir()
    html_file = html_dir / "0001.html"
    html_file.write_text("<html><body><h1>dummy</h1></body></html>", encoding="utf-8")

    recipes_json_path = tmp_path / "recipes.json"
    recipes_json_path.write_text(
        json.dumps(
            [
                {
                    "name": "テスト肉じゃが",
                    "cooking_time": 25,
                    "calories": 500,
                    "ingredients": [
                        {"name": "じゃがいも", "quantity_g": 100},
                        {"name": "にんじん", "quantity_g": 50},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    # override module constants to point to temp files
    monkeypatch.setattr(recipes_router_module, "STATIC_RECIPE_HTML_DIR", html_dir)
    monkeypatch.setattr(
        recipes_router_module, "STATIC_RECIPE_JSON_PATH", recipes_json_path
    )

    with TestClient(app) as client:
        resp = client.get("/api/v1/recipes/static-catalog")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list) and body, "expected at least one recipe"
        first = body[0]
        assert first["title"] == "テスト肉じゃが"
        assert first["detail_path"].endswith("0001.html")
        assert first["ingredients"] == ["じゃがいも", "にんじん"]
