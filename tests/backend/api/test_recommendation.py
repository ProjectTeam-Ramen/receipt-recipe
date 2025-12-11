from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backend.api.routers import recommendation as recommendation_module
from app.backend.api.routers.recommendation import router as recommendation_router
from app.backend.database import Base, get_db
from app.backend.models import (
    Food,
    FoodCategory,
    IngredientStatus,
    Recipe,
    RecipeFood,
    User,
    UserFood,
)


def _build_test_app():
    app = FastAPI()
    app.include_router(recommendation_router, prefix="/api/v1/recommendation")
    return app


def _setup_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with SessionLocal() as session:
        user1 = User(
            user_id=1,
            username="alice",
            email="alice@example.com",
            password_hash="hash",
        )
        user2 = User(
            user_id=2,
            username="bob",
            email="bob@example.com",
            password_hash="hash",
        )
        category = FoodCategory(category_id=1, category_name="カテゴリ")
        carrot = Food(food_id=1, food_name="にんじん", category_id=category.category_id)
        pork = Food(food_id=2, food_name="豚肉", category_id=category.category_id)

        session.add_all([user1, user2, category, carrot, pork])
        session.flush()

        recipe_carrot = Recipe(
            recipe_id=101,
            recipe_name="にんじんスープ",
            cooking_time=15,
            calories=200,
            is_japanese=True,
            is_main_dish=True,
        )
        recipe_pork = Recipe(
            recipe_id=202,
            recipe_name="豚肉炒め",
            cooking_time=20,
            calories=450,
            is_chinese=True,
            is_main_dish=True,
        )
        session.add_all([recipe_carrot, recipe_pork])
        session.flush()

        session.add_all(
            [
                RecipeFood(
                    recipe_food_id=1,
                    recipe_id=recipe_carrot.recipe_id,
                    food_id=carrot.food_id,
                    quantity_g=100,
                ),
                RecipeFood(
                    recipe_food_id=2,
                    recipe_id=recipe_pork.recipe_id,
                    food_id=pork.food_id,
                    quantity_g=120,
                ),
            ]
        )

        session.add_all(
            [
                UserFood(
                    user_food_id=1,
                    user_id=user1.user_id,
                    food_id=carrot.food_id,
                    quantity_g=150,
                    status=IngredientStatus.UNUSED,
                ),
                UserFood(
                    user_food_id=2,
                    user_id=user2.user_id,
                    food_id=pork.food_id,
                    quantity_g=200,
                    status=IngredientStatus.UNUSED,
                ),
            ]
        )
        session.commit()

    return engine, SessionLocal


def _override_db(SessionLocal):
    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return _get_db


def test_authenticated_request_uses_server_inventory():
    engine, SessionLocal = _setup_database()
    app = _build_test_app()

    app.dependency_overrides[get_db] = _override_db(SessionLocal)
    app.dependency_overrides[recommendation_module._optional_current_user] = (
        lambda: SimpleNamespace(user_id=1)
    )

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/recommendation/propose",
                json={
                    "user_id": 999,
                    "max_time": 60,
                    "max_calories": 800,
                    "allergies": [],
                    "inventory": [{"name": "豚肉", "quantity": "500"}],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["recipe_name"] == "にんじんスープ"
            assert data[0]["inventory_source"] == "server"
            assert data[0]["inventory_count"] == 1
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_unauthenticated_request_requires_inventory():
    engine, SessionLocal = _setup_database()
    app = _build_test_app()

    app.dependency_overrides[get_db] = _override_db(SessionLocal)
    app.dependency_overrides[recommendation_module._optional_current_user] = (
        lambda: None
    )

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/recommendation/propose",
                json={
                    "user_id": 2,
                    "max_time": 60,
                    "max_calories": 800,
                    "allergies": [],
                    "inventory": [{"name": "豚肉", "quantity": "200"}],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["recipe_name"] == "豚肉炒め"
            assert data[0]["inventory_source"] == "client"

            missing_inventory = client.post(
                "/api/v1/recommendation/propose",
                json={
                    "user_id": 2,
                    "max_time": 60,
                    "max_calories": 800,
                    "allergies": [],
                },
            )
            assert missing_inventory.status_code == 400
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
