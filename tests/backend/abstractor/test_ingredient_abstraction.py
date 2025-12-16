from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.backend.database import Base
from app.backend.models import Food, FoodCategory
from app.backend.services.abstractor.ingredient_abstraction_service import (
    IngredientAbstractionService,
    normalize_raw_text,
)
from app.backend.services.abstractor.ingredient_name_resolver import (
    IngredientNameResolver,
    Prediction,
    PredictionProvider,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def populated_db(db_session: Session) -> Session:
    category = FoodCategory(category_name="テストカテゴリ")
    db_session.add(category)
    db_session.flush()
    foods = [
        Food(
            food_name="じゃがいも", category_id=category.category_id, is_trackable=True
        ),
        Food(food_name="たまねぎ", category_id=category.category_id, is_trackable=True),
    ]
    db_session.add_all(foods)
    db_session.commit()
    return db_session


class DummyPredictor(PredictionProvider):
    def __init__(self, predictions: list[Prediction]):
        self.predictions = predictions
        self.called = False

    def predict(self, query: str, top_k: int = 5) -> list[Prediction]:  # type: ignore[override]
        self.called = True
        return self.predictions


def test_normalize_raw_text_handles_katakana():
    assert normalize_raw_text("ジャガイモ") == normalize_raw_text("じゃがいも")


def test_resolver_uses_cache_when_available(populated_db: Session):
    service = IngredientAbstractionService(populated_db)
    service.upsert("ジャガイモ", resolved_food_name="ジャガイモ", confidence=0.9)
    populated_db.commit()

    predictor = DummyPredictor([])
    resolver = IngredientNameResolver(populated_db, predictor=predictor)

    result = resolver.resolve("ジャガイモ")

    assert result.cached is True
    assert predictor.called is False
    assert result.resolved_food_name == "ジャガイモ"


def test_resolver_creates_mapping(populated_db: Session):
    predictions = [
        Prediction(label="0", probability=0.9, index=0, food_name="ジャガイモ"),
        Prediction(label="1", probability=0.05, index=1, food_name="米"),
    ]
    predictor = DummyPredictor(predictions)
    resolver = IngredientNameResolver(populated_db, predictor=predictor)

    result = resolver.resolve("未知の食材")

    assert result.cached is False
    assert result.resolved_food_name == "ジャガイモ"
    stored = IngredientAbstractionService(populated_db).find("未知の食材")
    assert stored is not None
    assert getattr(stored, "resolved_food_name") == "ジャガイモ"
    assert predictor.called is True


def test_resolver_uses_local_lookup_before_predictor(populated_db: Session):
    predictor = DummyPredictor([])
    resolver = IngredientNameResolver(populated_db, predictor=predictor)

    result = resolver.resolve("じゃがいも 2個 200円")

    assert result.resolved_food_name == "じゃがいも"
    assert result.source == "normalized_lookup"
    assert predictor.called is False


def test_resolver_fuzzy_matches_when_close(populated_db: Session):
    predictor = DummyPredictor([])
    resolver = IngredientNameResolver(populated_db, predictor=predictor)

    result = resolver.resolve("ためねぎ 3コ")

    assert result.resolved_food_name == "たまねぎ"
    assert result.source == "fuzzy_lookup"
    assert predictor.called is False


def test_resolver_fallback_when_predictions_missing(populated_db: Session):
    predictor = DummyPredictor([])
    resolver = IngredientNameResolver(populated_db, predictor=predictor)

    result = resolver.resolve("未知のXX食材")

    assert result.source.startswith("fallback:")
    assert result.resolved_food_name
    assert predictor.called is True
