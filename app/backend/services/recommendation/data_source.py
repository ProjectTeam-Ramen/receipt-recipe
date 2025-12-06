from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session, joinedload

from app.backend.database import SessionLocal
from app.backend.models import (
    Food,
    IngredientStatus,
    UserFood,
)
from app.backend.models import (
    Recipe as RecipeModel,  # type: ignore[attr-defined]
)
from app.backend.models import (
    RecipeFood as RecipeFoodModel,  # type: ignore[attr-defined]
)

from .data_models import Ingredient, Recipe

# 最終的なレシピ特徴ベクトルの次元定義 (18次元) - 定数として保持
FEATURE_DIMENSIONS = [
    "和食",
    "洋食",
    "中華",
    "主菜",
    "副菜",
    "汁物",
    "デザート",
    "肉類",
    "魚介類",
    "ベジタリアン",
    "複合",
    "その他",
    "辛味",
    "甘味",
    "酸味",
    "煮込み",
    "揚げ物",
    "炒め物",
]


class RecipeDataSource:
    """レシピマスター、特徴ベクトル、ユーザー行動履歴を取得・加工する"""

    def __init__(self, db_session: Optional[Session] = None):
        self.session = db_session
        self._recipe_vector_map: Dict[int, np.ndarray] = {}

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

    def create_user_profile_vector(self, user_id: int) -> np.ndarray:
        # 履歴テーブルが未実装のため、ゼロベクトルを返す
        return np.zeros(len(FEATURE_DIMENSIONS), dtype=np.float64)


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
