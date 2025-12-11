"""Utilities to sync the canonical food master list into the database."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

from sqlalchemy.orm import Session

from app.backend.database import SessionLocal
from app.backend.models import Food, FoodCategory

FOODLIST_RELATIVE_PATH = Path("data") / "foodlist" / "foodlist.json"


CATEGORY_LABELS: Mapping[str, str] = {
    "meat": "肉・加工肉",
    "seafood": "魚介類",
    "vegetables_fungi": "野菜・きのこ",
    "fruits": "果物",
    "dairy_eggs": "乳製品・卵",
    "soy_processed": "大豆・加工食品",
    "grains_noodles": "穀類・麺類",
    "pantry_others": "乾物・常備菜",
}


def _resolve_foodlist_path() -> Path:
    # app/backend/services -> ascend 3 levels to project root (/workspace)
    return Path(__file__).resolve().parents[3] / FOODLIST_RELATIVE_PATH


def _load_master_data() -> Dict[str, List[str]]:
    path = _resolve_foodlist_path()
    with path.open(encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):  # pragma: no cover - sanity guard
        raise ValueError("foodlist.json must define an object at the top level")
    return data


def _ensure_categories(
    session: Session, category_keys: Iterable[str]
) -> Dict[str, FoodCategory]:
    desired_names = {key: CATEGORY_LABELS.get(key, key) for key in category_keys}
    existing = (
        session.query(FoodCategory)
        .filter(FoodCategory.category_name.in_(desired_names.values()))
        .all()
    )
    categories: Dict[str, FoodCategory] = {}
    for item in existing:
        category_name = getattr(item, "category_name", None)
        if category_name:
            categories[str(category_name)] = item
    result: Dict[str, FoodCategory] = {}
    for key, display_name in desired_names.items():
        category = categories.get(display_name)
        if not category:
            category = FoodCategory(category_name=display_name)
            session.add(category)
            session.flush([category])
        result[key] = category
    return result


def sync_food_master() -> None:
    """Insert missing foods/categories so the master list is fully available."""

    data = _load_master_data()
    with SessionLocal() as session:
        categories = _ensure_categories(session, data.keys())

        desired_foods = [food_name for foods in data.values() for food_name in foods]
        if desired_foods:
            existing_foods = {
                name
                for (name,) in session.query(Food.food_name).filter(
                    Food.food_name.in_(desired_foods)
                )
            }
        else:
            existing_foods = set()

        for key, foods in data.items():
            category = categories[key]
            for food_name in foods:
                if food_name in existing_foods:
                    continue
                session.add(
                    Food(
                        food_name=food_name,
                        category_id=category.category_id,
                        is_trackable=True,
                    )
                )
        session.commit()
