from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backend.api.routers.auth_routes import get_current_user
from app.backend.api.routers.ingredients import router as ingredients_router
from app.backend.database import Base, get_db
from app.backend.models import User


def _build_test_app():
    app = FastAPI()
    app.include_router(ingredients_router, prefix="/api/v1/ingredients")
    return app


def _setup_database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
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
        session.commit()
    return engine, TestingSessionLocal


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
            create_resp = client.post(
                "/api/v1/ingredients/",
                json={"name": "トマト", "quantity_g": 250},
            )
            assert create_resp.status_code == 201
            create_data = create_resp.json()
            assert create_data["food_name"] == "トマト"
            assert create_data["quantity_g"] == 250

            list_resp = client.get("/api/v1/ingredients/")
            assert list_resp.status_code == 200
            list_data = list_resp.json()
            assert list_data["total"] == 1
            assert list_data["ingredients"][0]["food_name"] == "トマト"
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
