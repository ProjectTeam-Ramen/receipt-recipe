from decimal import Decimal

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backend.database import Base
from app.backend.models import User
from app.backend.models.recipe import Recipe, UserRecipeHistory
from app.backend.services.recommendation.data_source import (
    FEATURE_DIMENSIONS,
    RecipeDataSource,
)


def _setup_inmemory_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def test_create_user_profile_vector_reflects_history():
    engine, SessionLocal = _setup_inmemory_db()
    try:
        with SessionLocal() as session:
            user = User(
                user_id=1,
                username="vector-user",
                email="vector@example.com",
                password_hash="hashed",
            )
            recipe = Recipe(
                recipe_id=10,
                recipe_name="和風テスト",
                is_japanese=True,
                cooking_time=15,
                calories=300,
            )
            session.add_all([user, recipe])
            session.flush()

            session.add(
                UserRecipeHistory(
                    user_id=user.user_id,
                    recipe_id=recipe.recipe_id,
                    servings=Decimal("1.0"),
                )
            )
            session.commit()

            source = RecipeDataSource(db_session=session)
            source.load_and_vectorize_recipes()
            vector = source.create_user_profile_vector(int(getattr(user, "user_id")))

        idx = FEATURE_DIMENSIONS.index("is_japanese")
        assert vector[idx] == pytest.approx(1.0)
        assert np.count_nonzero(vector) == 1
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_build_profile_vector_from_payload():
    source = RecipeDataSource()
    history = [
        {
            "recipe_id": 42,
            "completed_at": "2025-12-01T09:00:00Z",
            "servings": 2,
        }
    ]
    recipes_payload = [
        {
            "id": 42,
            "features": {
                feature: (1 if feature == "is_western" else 0)
                for feature in FEATURE_DIMENSIONS
            },
        }
    ]

    vector = source.build_profile_vector_from_payload(history, recipes_payload)
    idx = FEATURE_DIMENSIONS.index("is_western")
    assert vector[idx] == pytest.approx(1.0)
    assert np.count_nonzero(vector) == 1
