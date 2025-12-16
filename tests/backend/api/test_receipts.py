from __future__ import annotations

import importlib
import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backend.database import Base, get_db
from app.backend.models import Food, FoodCategory, IngredientAbstraction

receipts_module = importlib.import_module("app.backend.api.routers.receipts")
receipts_router = receipts_module.router

receipts_module_typed: Any = receipts_module


class DummyOCRService:
    def __init__(self, processed_dir: Path) -> None:
        self.processed_dir = processed_dir

    def process(self, filename: str):
        lines = [
            SimpleNamespace(
                line_id=0,
                text="りんご 2個 200円",
                confidence=0.92,
                bbox=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
                center=[0.5, 0.5],
            ),
            SimpleNamespace(
                line_id=1,
                text="牛乳 1本 150円",
                confidence=0.88,
                bbox=[[0.0, 1.0], [1.0, 1.0], [1.0, 2.0], [0.0, 2.0]],
                center=[0.5, 1.5],
            ),
        ]
        processed_path = self.processed_dir / f"{Path(filename).stem}_processed.png"
        return SimpleNamespace(
            lines=lines,
            processed_image_path=processed_path,
            text_content="\n".join(line.text for line in lines),
        )


def _build_test_app():
    app = FastAPI()
    app.include_router(receipts_router, prefix="/api/v1/receipts")
    return app


def test_receipt_upload_and_text_edit(tmp_path):
    data_dir = tmp_path / "receipt_image"
    processed_dir = tmp_path / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    original_data_dir = receipts_module_typed.DATA_DIR
    original_processed_dir = receipts_module_typed.PROCESSED_DATA_DIR
    original_service = receipts_module_typed._OCR_SERVICE

    receipts_module_typed.DATA_DIR = data_dir
    receipts_module_typed.PROCESSED_DATA_DIR = processed_dir
    receipts_module_typed._OCR_SERVICE = None

    dummy_service = DummyOCRService(processed_dir)

    app = _build_test_app()
    app.dependency_overrides[receipts_module_typed._ocr_service_dependency] = (
        lambda: dummy_service
    )

    try:
        original_resolver_builder = receipts_module_typed._build_resolver
        receipts_module_typed._build_resolver = lambda: (None, None)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/receipts/upload",
                files={
                    "file": ("sample.png", io.BytesIO(b"fake"), "image/png"),
                },
            )
            assert resp.status_code == 202

            receipts_module_typed._process_receipt_async(
                1, "receipt_1.png", dummy_service
            )

            status = client.get("/api/v1/receipts/1/status")
            assert status.status_code == 200
            assert status.json()["status"] == "completed"

            text_resp = client.get("/api/v1/receipts/1/text")
            assert text_resp.status_code == 200
            assert "りんご" in text_resp.json()["text"]

            patch_resp = client.patch(
                "/api/v1/receipts/1/items/1",
                json={"raw_text": "バナナ 3本 300円"},
            )
            assert patch_resp.status_code == 200

            plain_resp = client.get("/api/v1/receipts/1/text?format=plain")
            assert plain_resp.status_code == 200
            assert "バナナ" in plain_resp.text
    finally:
        receipts_module_typed._build_resolver = original_resolver_builder
        receipts_module_typed.DATA_DIR = original_data_dir
        receipts_module_typed.PROCESSED_DATA_DIR = original_processed_dir
        receipts_module_typed._OCR_SERVICE = original_service


def test_food_options_endpoint_returns_all_foods(tmp_path):
    db_path = tmp_path / "food_options.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    original_session_local = receipts_module_typed.SessionLocal
    receipts_module_typed.SessionLocal = TestingSession

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = _build_test_app()
    app.dependency_overrides[get_db] = _override_get_db

    try:
        with TestingSession() as session:
            category = FoodCategory(category_name="テストカテゴリ")
            session.add(category)
            session.flush()
            for idx in range(1, 78):
                session.add(
                    Food(
                        food_name=f"テスト食材{idx}",
                        category_id=category.category_id,
                        is_trackable=True,
                    )
                )
            session.commit()

        with TestClient(app) as client:
            resp = client.get("/api/v1/receipts/food-options")
            assert resp.status_code == 200, resp.text
            options = resp.json()
            assert len(options) == 77
            assert len({opt["food_id"] for opt in options}) == 77

    finally:
        app.dependency_overrides.pop(get_db, None)
        receipts_module_typed.SessionLocal = original_session_local
        Base.metadata.drop_all(engine)
        engine.dispose()


class DummyResolver:
    def __init__(self) -> None:
        self.calls = []

    def resolve(self, raw_text: str):
        self.calls.append(raw_text)
        return SimpleNamespace(
            resolved_food_name="りんご",
            normalized_text="リンゴ",
            food_id=10,
            confidence=0.99,
            source="test",
            cached=False,
            metadata={"note": "dummy"},
        )


class DummyDBSession:
    def __init__(self) -> None:
        self.committed = False
        self.closed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_receipt_upload_with_ingredient_resolution(tmp_path):
    data_dir = tmp_path / "receipt_image"
    processed_dir = tmp_path / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    original_data_dir = receipts_module_typed.DATA_DIR
    original_processed_dir = receipts_module_typed.PROCESSED_DATA_DIR
    original_service = receipts_module_typed._OCR_SERVICE
    original_resolver_builder = receipts_module_typed._build_resolver

    receipts_module_typed.DATA_DIR = data_dir
    receipts_module_typed.PROCESSED_DATA_DIR = processed_dir
    receipts_module_typed._OCR_SERVICE = None

    dummy_service = DummyOCRService(processed_dir)
    dummy_db = DummyDBSession()
    dummy_resolver = DummyResolver()

    def _resolver_builder():
        return dummy_resolver, dummy_db

    receipts_module_typed._build_resolver = _resolver_builder

    app = _build_test_app()
    app.dependency_overrides[receipts_module_typed._ocr_service_dependency] = (
        lambda: dummy_service
    )

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/receipts/upload",
                files={
                    "file": ("sample.png", io.BytesIO(b"fake"), "image/png"),
                },
            )
            assert resp.status_code == 202

            receipts_module_typed._process_receipt_async(
                1, "receipt_1.png", dummy_service
            )

            receipt_resp = client.get("/api/v1/receipts/1")
            assert receipt_resp.status_code == 200
            data = receipt_resp.json()

            assert len(data["items"]) == 2
            first_item = data["items"][0]
            assert first_item["food_name"] == "りんご"
            assert first_item["food_id"] == 10
            assert first_item["ingredient_resolution"] is not None
            assert first_item["ingredient_resolution"]["metadata"] == {"note": "dummy"}

            assert dummy_db.committed is True
            assert dummy_db.closed is True
            assert dummy_resolver.calls[0] == "りんご 2個 200円"
    finally:
        receipts_module_typed._build_resolver = original_resolver_builder
        receipts_module_typed.DATA_DIR = original_data_dir
        receipts_module_typed.PROCESSED_DATA_DIR = original_processed_dir
        receipts_module_typed._OCR_SERVICE = original_service


def test_manual_resolution_persists_to_db(tmp_path):
    data_dir = tmp_path / "receipt_image"
    processed_dir = tmp_path / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    db_path = tmp_path / "test_manual_resolution.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    original_data_dir = receipts_module_typed.DATA_DIR
    original_processed_dir = receipts_module_typed.PROCESSED_DATA_DIR
    original_service = receipts_module_typed._OCR_SERVICE
    original_resolver_builder = receipts_module_typed._build_resolver
    original_session_local = receipts_module_typed.SessionLocal

    receipts_module_typed.DATA_DIR = data_dir
    receipts_module_typed.PROCESSED_DATA_DIR = processed_dir
    receipts_module_typed._OCR_SERVICE = None
    receipts_module_typed.SessionLocal = TestingSession

    dummy_service = DummyOCRService(processed_dir)

    def _resolver_builder():
        return None, None

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    receipts_module_typed._build_resolver = _resolver_builder

    app = _build_test_app()
    app.dependency_overrides[receipts_module_typed._ocr_service_dependency] = (
        lambda: dummy_service
    )
    app.dependency_overrides[get_db] = _override_get_db

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/receipts/upload",
                files={
                    "file": ("sample.png", io.BytesIO(b"fake"), "image/png"),
                },
            )
            assert resp.status_code == 202

            receipts_module_typed._process_receipt_async(
                1, "receipt_1.png", dummy_service
            )

            payload = {
                "raw_text": "りんご 2個 200円",
                "resolved_food_name": "青森りんご",
                "food_id": 42,
                "confidence": 0.87,
                "note": "ユーザー修正",
            }
            manual_resp = client.post(
                "/api/v1/receipts/1/items/1/manual-resolution",
                json=payload,
            )
            assert manual_resp.status_code == 200
            updated = manual_resp.json()
            assert updated["food_name"] == "青森りんご"
            assert updated["food_id"] == 42
            resolution = updated.get("ingredient_resolution") or {}
            assert resolution.get("source") == "manual_override"
            assert resolution.get("metadata", {}).get("manual_override") is True

        with TestingSession() as session:
            record = session.query(IngredientAbstraction).one()
            assert getattr(record, "resolved_food_name") == "青森りんご"
            assert getattr(record, "food_id") == 42
    finally:
        receipts_module_typed._build_resolver = original_resolver_builder
        receipts_module_typed.DATA_DIR = original_data_dir
        receipts_module_typed.PROCESSED_DATA_DIR = original_processed_dir
        receipts_module_typed._OCR_SERVICE = original_service
        receipts_module_typed.SessionLocal = original_session_local
        app.dependency_overrides.pop(
            receipts_module_typed._ocr_service_dependency, None
        )
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
