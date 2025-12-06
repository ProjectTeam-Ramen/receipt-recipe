"""Utilities to sync recipe master data from JSON into the database."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session, joinedload

from app.backend.database import SessionLocal
from app.backend.models import Food
from app.backend.models.recipe import Recipe, RecipeFood  # type: ignore[import]

RECIPES_JSON_REL_PATH = Path("data") / "recipes.json"


@dataclass(frozen=True)
class _IngredientRow:
    name: str
    quantity_g: Optional[Decimal]


@dataclass(frozen=True)
class _RecipeRow:
    name: str
    cooking_time: Optional[int]
    calories: Optional[int]
    ingredients: Sequence[_IngredientRow]


def _resolve_json_path() -> Path:
    return Path(__file__).resolve().parents[3] / RECIPES_JSON_REL_PATH


def _load_recipe_rows() -> List[_RecipeRow]:
    path = _resolve_json_path()
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as fp:
        try:
            payload = json.load(fp)
        except json.JSONDecodeError:
            return []

    if not isinstance(payload, list):
        return []

    rows: List[_RecipeRow] = []
    for entry in payload:
        maybe_row = _parse_recipe_entry(entry)
        if maybe_row:
            rows.append(maybe_row)

    return rows


def _parse_recipe_entry(entry: object) -> Optional[_RecipeRow]:
    if not isinstance(entry, dict):
        return None

    name = str(entry.get("name") or "").strip()
    if not name:
        return None

    cooking_time_value = _safe_int(entry.get("cooking_time"))
    calories_value = _safe_int(entry.get("calories"))

    ingredients_raw = entry.get("ingredients") or []
    if not isinstance(ingredients_raw, list):
        return None

    ingredients: List[_IngredientRow] = []
    for ingredient in ingredients_raw:
        parsed = _parse_ingredient_entry(ingredient)
        if parsed:
            ingredients.append(parsed)

    if not ingredients:
        return None

    return _RecipeRow(
        name=name,
        cooking_time=cooking_time_value,
        calories=calories_value,
        ingredients=ingredients,
    )


def _parse_ingredient_entry(entry: object) -> Optional[_IngredientRow]:
    if not isinstance(entry, dict):
        return None
    raw_name = str(entry.get("name") or "").strip()
    if not raw_name:
        return None
    raw_quantity = entry.get("quantity_g")
    return _IngredientRow(name=raw_name, quantity_g=_safe_decimal(raw_quantity))


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(round(float(value), 2)))
    except (TypeError, ValueError, ArithmeticError):
        return None


_QUANTITY_REGEX = re.compile(r"([0-9]+(?:\.[0-9]+)?)")


def _estimate_quantity(token: str) -> Decimal:
    match = _QUANTITY_REGEX.search(token)
    if match:
        value = float(match.group(1))
        lowered = token.lower()
        if "kg" in lowered:
            grams = value * 1000
        elif "g" in lowered or "ｇ" in token:
            grams = value
        elif "ml" in lowered:
            grams = value
        elif "大さじ" in token:
            grams = value * 15
        elif "小さじ" in token:
            grams = value * 5
        elif any(
            unit in token
            for unit in [
                "本",
                "個",
                "枚",
                "玉",
                "束",
                "袋",
                "丁",
                "缶",
                "尾",
                "切れ",
                "杯",
                "片",
            ]
        ):
            grams = value * 100
        else:
            grams = value * 50
    else:
        grams = 100.0
    return Decimal(str(round(grams, 2)))


def _normalize_ingredient_name(token: str) -> str:
    token = token.replace("　", " ")
    token = re.sub(r"\(.*?\)", "", token)
    token = re.sub(r"\[.*?\]", "", token)
    token = token.replace("（", "(").replace("）", ")")
    token = token.strip(" ・,，。.")
    parts = token.split()
    return parts[0].strip() if parts else token


def _map_ingredients(
    ingredients: Sequence[_IngredientRow], food_lookup: Dict[str, Food]
) -> List[Tuple[int, Decimal]]:
    mapped: List[Tuple[int, Decimal]] = []
    for ingredient in ingredients:
        name = _normalize_ingredient_name(ingredient.name)
        food = food_lookup.get(name)
        if not food:
            continue  # 非トラッキング食材(調味料など)はスキップ
        food_id = getattr(food, "food_id", None)
        if not isinstance(food_id, int):
            continue
        quantity = ingredient.quantity_g
        if quantity is None:
            quantity = _estimate_quantity(ingredient.name)
        mapped.append((food_id, quantity))
    return mapped


def _refresh_food_lookup(session: Session) -> Dict[str, Food]:
    foods = session.query(Food).all()
    lookup: Dict[str, Food] = {}
    for food in foods:
        name = getattr(food, "food_name", None)
        if isinstance(name, str):
            lookup[name] = food
    return lookup


def _sync_recipe_foods(
    session: Session,
    recipe: Recipe,
    mapped_ingredients: Iterable[Tuple[int, Decimal]],
):
    session.query(RecipeFood).filter(RecipeFood.recipe_id == recipe.recipe_id).delete()
    for ingredient in mapped_ingredients:
        food_id, quantity = ingredient
        session.add(
            RecipeFood(
                recipe_id=recipe.recipe_id,
                food_id=food_id,
                quantity_g=quantity,
            )
        )


def sync_recipe_master() -> None:
    rows = _load_recipe_rows()
    if not rows:
        return

    with SessionLocal() as session:
        food_lookup = _refresh_food_lookup(session)
        existing = {
            recipe.recipe_name: recipe
            for recipe in session.query(Recipe)
            .options(joinedload(Recipe.recipe_foods))
            .all()
        }

        for row in rows:
            mapped_ingredients = _map_ingredients(row.ingredients, food_lookup)
            recipe = existing.get(row.name)
            if not recipe:
                recipe = Recipe(
                    recipe_name=row.name,
                    description=f"{row.name}のレシピ",
                    cooking_time=row.cooking_time or 30,
                    calories=row.calories,
                    image_url=None,
                )
                session.add(recipe)
                session.flush([recipe])
                existing[row.name] = recipe
            else:
                if row.cooking_time is not None:
                    recipe.cooking_time = row.cooking_time
                elif getattr(recipe, "cooking_time", None) is None:
                    recipe.cooking_time = 30

                if row.calories is not None:
                    recipe.calories = row.calories

            if not mapped_ingredients:
                continue

            _sync_recipe_foods(session, recipe, mapped_ingredients)

        session.commit()
