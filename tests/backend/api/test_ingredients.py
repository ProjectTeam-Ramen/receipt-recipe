from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backend.api.routers.auth_routes import get_current_user
from app.backend.api.routers.ingredients import router as ingredients_router
from app.backend.database import Base, get_db
from app.backend.models import Food, FoodCategory, User, UserFood

_ = (Food, FoodCategory, UserFood)


def _build_test_app():
    app = FastAPI()
    app.include_router(ingredients_router, prefix="/api/v1/ingredients")
    return app


def _setup_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with TestingSessionLocal() as session:
        user = User(
            user_id=1,
            username="tester",
            email="tester@example.com",
            password_hash="hash",
        )
        session.add(user)
        session.flush()

        category = FoodCategory(category_id=1, category_name="テストカテゴリ")
        session.add(category)
        session.flush()

        session.add_all(
            [
                Food(food_id=1, food_name="トマト", category_id=category.category_id),
                Food(food_id=2, food_name="きゅうり", category_id=category.category_id),
            ]
        )
        session.commit()
    return engine, TestingSessionLocal


def _get_food_id(session_factory, name: str) -> int:
    with session_factory() as session:
        food = session.query(Food).filter(Food.food_name == name).first()
        assert food, f"food '{name}' must exist"
        return food.food_id


def test_create_and_list_ingredients():
    engine, SessionLocal = _setup_database()
    app = _build_test_app()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        return SimpleNamespace(user_id=1)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with TestClient(app) as client:
            tomato_id = _get_food_id(SessionLocal, "トマト")
            create_resp = client.post(
                "/api/v1/ingredients/",
                json={"food_id": tomato_id, "quantity_g": 250},
            )
            assert create_resp.status_code == 201
            create_data = create_resp.json()
            assert create_data["food_name"] == "トマト"
            assert create_data["quantity_g"] == 250
            assert create_data["status"] == "unused"

            list_resp = client.get("/api/v1/ingredients/")
            assert list_resp.status_code == 200
            list_data = list_resp.json()
            assert list_data["total"] == 1
            assert list_data["ingredients"][0]["food_name"] == "トマト"

            ingredient_id = create_data["user_food_id"]

            consume_resp = client.post(
                f"/api/v1/ingredients/{ingredient_id}/consume",
                json={"quantity_g": 100},
            )
            assert consume_resp.status_code == 200
            consume_data = consume_resp.json()
            assert consume_data["quantity_g"] == 150
            assert consume_data["status"] == "used"

            post_consume_list = client.get("/api/v1/ingredients/")
            assert post_consume_list.status_code == 200
            assert post_consume_list.json()["total"] == 0
            used_list = client.get("/api/v1/ingredients/?status=used")
            assert used_list.status_code == 200
            assert used_list.json()["total"] == 1

            over_resp = client.post(
                f"/api/v1/ingredients/{ingredient_id}/consume",
                json={"quantity_g": 200},
            )
            assert over_resp.status_code == 400

            finish_resp = client.post(
                f"/api/v1/ingredients/{ingredient_id}/consume",
                json={"quantity_g": 150},
            )
            assert finish_resp.status_code == 200
            finish_data = finish_resp.json()
            assert finish_data["quantity_g"] == 0
            assert finish_data["status"] == "used"

            update_resp = client.patch(
                f"/api/v1/ingredients/{ingredient_id}/status",
                json={"status": "used"},
            )
            assert update_resp.status_code == 200
            assert update_resp.json()["status"] == "used"

            used_resp = client.get("/api/v1/ingredients/?status=used")
            assert used_resp.status_code == 200
            assert used_resp.json()["total"] == 1

            delete_resp = client.patch(
                f"/api/v1/ingredients/{ingredient_id}/status",
                json={"status": "deleted"},
            )
            assert delete_resp.status_code == 200

            default_list_resp = client.get("/api/v1/ingredients/")
            assert default_list_resp.status_code == 200
            assert default_list_resp.json()["total"] == 0

            deleted_list_resp = client.get("/api/v1/ingredients/?status=deleted")
            assert deleted_list_resp.status_code == 200
            assert deleted_list_resp.json()["total"] == 1
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_delete_ingredient():
    engine, SessionLocal = _setup_database()
    app = _build_test_app()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        return SimpleNamespace(user_id=1)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with TestClient(app) as client:
            cucumber_id = _get_food_id(SessionLocal, "きゅうり")
            create_resp = client.post(
                "/api/v1/ingredients/",
                json={"food_id": cucumber_id, "quantity_g": 100},
            )
            assert create_resp.status_code == 201
            ingredient_id = create_resp.json()["user_food_id"]

            delete_resp = client.delete(f"/api/v1/ingredients/{ingredient_id}")
            assert delete_resp.status_code == 204

            list_resp = client.get("/api/v1/ingredients/")
            assert list_resp.status_code == 200
            assert list_resp.json()["total"] == 0

            deleted_list = client.get("/api/v1/ingredients/?status=deleted")
            assert deleted_list.status_code == 200
            assert deleted_list.json()["total"] == 1

            second_delete = client.delete(f"/api/v1/ingredients/{ingredient_id}")
            assert second_delete.status_code == 204

            not_found = client.delete("/api/v1/ingredients/9999")
            assert not_found.status_code == 404
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
