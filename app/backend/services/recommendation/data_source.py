from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from sqlalchemy.orm import Session, joinedload

from app.backend.database import SessionLocal
from app.backend.models import Food, IngredientStatus, UserFood, UserRecipeHistory
from app.backend.models import (
    Recipe as RecipeModel,  # type: ignore[attr-defined]
)
from app.backend.models import (
    RecipeFood as RecipeFoodModel,  # type: ignore[attr-defined]
)

from .data_models import Ingredient, Recipe

# レシピ特徴ベクトルの次元定義 (18次元)
FEATURE_DIMENSIONS = [
    "is_japanese",
    "is_western",
    "is_chinese",
    "is_main_dish",
    "is_side_dish",
    "is_soup",
    "is_dessert",
    "type_meat",
    "type_seafood",
    "type_vegetarian",
    "type_composite",
    "type_other",
    "flavor_sweet",
    "flavor_spicy",
    "flavor_salty",
    "texture_stewed",
    "texture_fried",
    "texture_stir_fried",
]


class RecipeDataSource:
    """レシピマスター、特徴ベクトル、ユーザー行動履歴を取得・加工する"""

    def __init__(self, db_session: Optional[Session] = None):
        self.session = db_session
        self._recipe_vector_map: Dict[int, np.ndarray] = {}

    def _ensure_recipe_vectors(self) -> None:
        if not self._recipe_vector_map:
            self.load_and_vectorize_recipes()

    def load_and_vectorize_recipes(self) -> List[Recipe]:
        session = self.session or SessionLocal()
        should_close = self.session is None
        try:
            recipes_query = (
                session.query(RecipeModel)
                .options(
                    joinedload(RecipeModel.recipe_foods).joinedload(
                        RecipeFoodModel.food
                    )
                )
                .all()
            )
        finally:
            if should_close:
                session.close()

        recipes: List[Recipe] = []
        for record in recipes_query:
            req_qty: Dict[str, float] = {}
            for rf in getattr(record, "recipe_foods", []) or []:
                food = getattr(rf, "food", None)
                name = getattr(food, "food_name", None)
                if not isinstance(name, str):
                    continue
                quantity = getattr(rf, "quantity_g", 0) or 0
                req_qty[name] = float(quantity)

            vector = np.zeros(len(FEATURE_DIMENSIONS), dtype=np.float64)
            for idx, field in enumerate(FEATURE_DIMENSIONS):
                if bool(getattr(record, field, False)):
                    vector[idx] = 1.0
            recipe_obj = Recipe(
                id=getattr(record, "recipe_id"),
                name=getattr(record, "recipe_name", ""),
                prep_time=getattr(record, "cooking_time", None) or 30,
                calories=getattr(record, "calories", None) or 0,
                req_qty=req_qty,
                feature_vector=vector,
                image_url=getattr(record, "image_url", None),
            )
            recipes.append(recipe_obj)
            if isinstance(recipe_obj.id, int):
                self._recipe_vector_map[recipe_obj.id] = vector

        return recipes

    def _build_vector_from_history_items(
        self,
        history_items: Sequence[Tuple[int, Optional[datetime], Optional[float]]],
        vector_lookup: Dict[int, np.ndarray],
    ) -> np.ndarray:
        dimension = len(FEATURE_DIMENSIONS)
        profile = np.zeros(dimension, dtype=np.float64)
        if not history_items:
            return profile

        now = datetime.now(timezone.utc)
        total_weight = 0.0
        for recipe_id, completed_at, servings in history_items:
            vector = vector_lookup.get(recipe_id)
            if vector is None:
                continue

            timestamp = completed_at or now
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            else:
                timestamp = timestamp.astimezone(timezone.utc)

            days = max((now - timestamp).total_seconds() / (60 * 60 * 24), 0.0)
            weight = float(np.exp(-0.05 * days))
            if servings is not None:
                try:
                    weight *= max(float(servings), 0.1)
                except (TypeError, ValueError):
                    pass
            profile += vector * weight
            total_weight += weight

        if total_weight <= 0:
            return np.zeros(dimension, dtype=np.float64)
        return profile / total_weight

    def create_user_profile_vector(
        self, user_id: int, history_limit: int = 200
    ) -> np.ndarray:
        self._ensure_recipe_vectors()
        session = self.session or SessionLocal()
        should_close = self.session is None
        try:
            history_rows = (
                session.query(UserRecipeHistory)
                .filter(UserRecipeHistory.user_id == user_id)
                .order_by(UserRecipeHistory.cooked_at.desc())
                .limit(history_limit)
                .all()
            )
        finally:
            if should_close:
                session.close()

        history_items: List[Tuple[int, Optional[datetime], Optional[float]]] = []
        for row in history_rows:
            rid = getattr(row, "recipe_id", None)
            if not isinstance(rid, int):
                continue
            cooked_at = getattr(row, "cooked_at", None)
            servings_value = getattr(row, "servings", None)
            servings_float: Optional[float] = None
            if servings_value is not None:
                try:
                    servings_float = float(servings_value)
                except (TypeError, ValueError):
                    servings_float = None
            history_items.append((rid, cooked_at, servings_float))

        return self._build_vector_from_history_items(
            history_items, self._recipe_vector_map
        )

    def _vectorize_single_payload(
        self, record: Dict[str, Any], dimension: int
    ) -> Optional[Tuple[int, np.ndarray]]:
        recipe_id_raw = record.get("id")
        if not isinstance(recipe_id_raw, (int, str)):
            return None
        try:
            recipe_id_int = int(recipe_id_raw)
        except (TypeError, ValueError):
            return None

        features: Dict[str, Any] = {}
        raw_features = record.get("features")
        if isinstance(raw_features, dict):
            features = raw_features

        vector = np.zeros(dimension, dtype=np.float64)
        for idx, field in enumerate(FEATURE_DIMENSIONS):
            value = features.get(field)
            normalized = 0.0
            if isinstance(value, (int, float)):
                normalized = 1.0 if float(value) else 0.0
            elif isinstance(value, str):
                try:
                    normalized = 1.0 if float(value) else 0.0
                except ValueError:
                    normalized = 1.0 if value else 0.0
            elif value:
                normalized = 1.0
            vector[idx] = normalized
        return recipe_id_int, vector

    def _vectorize_recipe_payload(
        self, recipes_payload: List[Dict[str, Any]]
    ) -> Dict[int, np.ndarray]:
        dimension = len(FEATURE_DIMENSIONS)
        vector_lookup: Dict[int, np.ndarray] = {}
        for record in recipes_payload:
            if not isinstance(record, dict):
                continue
            parsed = self._vectorize_single_payload(record, dimension)
            if not parsed:
                continue
            recipe_id_int, vector = parsed
            vector_lookup[recipe_id_int] = vector
        return vector_lookup

    def _parse_history_payload(
        self, history: List[Dict[str, Any]]
    ) -> List[Tuple[int, Optional[datetime], Optional[float]]]:
        parsed: List[Tuple[int, Optional[datetime], Optional[float]]] = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            recipe_id_raw = entry.get("recipe_id")
            if not isinstance(recipe_id_raw, (int, str)):
                continue
            try:
                recipe_id_int = int(recipe_id_raw)
            except (TypeError, ValueError):
                continue

            timestamp = entry.get("completed_at") or entry.get("cooked_at")
            completed_at: Optional[datetime] = None
            if isinstance(timestamp, str) and timestamp:
                try:
                    completed_at = datetime.fromisoformat(
                        timestamp.replace("Z", "+00:00")
                    )
                except ValueError:
                    completed_at = None

            servings_raw = entry.get("servings")
            servings_value: Optional[float] = None
            if isinstance(servings_raw, (int, float, str)):
                try:
                    servings_value = float(servings_raw)
                except (TypeError, ValueError):
                    servings_value = None

            parsed.append((recipe_id_int, completed_at, servings_value))
        return parsed

    def build_profile_vector_from_payload(
        self, history: List[Dict[str, Any]], recipes_payload: List[Dict[str, Any]]
    ) -> np.ndarray:
        vector_lookup = self._vectorize_recipe_payload(recipes_payload)
        history_items = self._parse_history_payload(history)
        return self._build_vector_from_history_items(history_items, vector_lookup)


class InventoryManager:
    """データベースの在庫を直接参照して Ingredient リストを構築する"""

    def __init__(self, db_session: Optional[Session] = None):
        self.session = db_session

    def get_current_inventory(self, user_id: int = 1) -> List[Ingredient]:
        session = self.session or SessionLocal()
        should_close = self.session is None
        try:
            inventory = (
                session.query(UserFood)
                .join(Food)
                .filter(
                    UserFood.user_id == user_id,
                    UserFood.status != IngredientStatus.DELETED,
                )
                .all()
            )
        finally:
            if should_close:
                session.close()

        items: List[Ingredient] = []
        for record in inventory:
            food = getattr(record, "food", None)
            name = getattr(food, "food_name", None)
            if not isinstance(name, str):
                continue
            quantity = getattr(record, "quantity_g", 0) or 0
            expiry = getattr(record, "expiration_date", None)
            items.append(
                Ingredient(name=name, quantity=float(quantity), expiration_date=expiry)
            )
        return items
