from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from app.backend.api.routers.auth_routes import get_current_user
from app.backend.database import get_db
from app.backend.models import (
    IngredientStatus,
    InventoryChangeSource,
    User,
    UserFood,
    UserRecipeHistory,
)
from app.backend.models.food import Food
from app.backend.models.recipe import Recipe, RecipeFood  # type: ignore[import]

router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATIC_RECIPE_HTML_DIR = _PROJECT_ROOT / "data" / "recipe-list"
STATIC_RECIPE_JSON_PATH = _PROJECT_ROOT / "data" / "recipes.json"
RECIPE_PAGES_ROUTE = "/recipe-pages"

RECIPE_FLAG_FIELDS: List[str] = [
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


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _require_int(value: Any, name: str) -> int:
    converted = _as_int(value)
    if converted is None:
        raise HTTPException(status_code=500, detail=f"{name} が不正です")
    return converted


class RecipeIngredientItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    food_id: int
    food_name: str
    quantity_g: float
    available_quantity_g: Optional[float] = None
    missing_quantity_g: Optional[float] = None


class RecipeDetailResponse(BaseModel):
    recipe_id: int
    recipe_name: str
    description: Optional[str]
    instructions: Optional[str]
    cooking_time: Optional[int]
    calories: Optional[int]
    is_japanese: bool = False
    is_western: bool = False
    is_chinese: bool = False
    is_main_dish: bool = False
    is_side_dish: bool = False
    is_soup: bool = False
    is_dessert: bool = False
    type_meat: bool = False
    type_seafood: bool = False
    type_vegetarian: bool = False
    type_composite: bool = False
    type_other: bool = False
    flavor_sweet: bool = False
    flavor_spicy: bool = False
    flavor_salty: bool = False
    texture_stewed: bool = False
    texture_fried: bool = False
    texture_stir_fried: bool = False
    ingredients: List[RecipeIngredientItem]


class CookRecipeRequest(BaseModel):
    servings: float = Field(1.0, gt=0, le=50)


class CookedIngredient(BaseModel):
    food_id: int
    food_name: str
    required_quantity_g: float
    consumed_quantity_g: float
    remaining_quantity_g: float


class CookRecipeResponse(BaseModel):
    recipe_id: int
    recipe_name: str
    servings: float
    consumed: List[CookedIngredient]


class StaticRecipeSummary(BaseModel):
    id: str
    title: str
    detail_path: str
    ingredients: List[str] = Field(default_factory=list)
    cooking_time: Optional[int] = None
    calories: Optional[int] = None


def _parse_static_recipe_entry(
    index: int, entry: object
) -> Optional[StaticRecipeSummary]:
    if not isinstance(entry, dict):
        return None
    file_name = f"{index + 1:04d}.html"
    html_path = STATIC_RECIPE_HTML_DIR / file_name
    if not html_path.exists():
        return None

    raw_ingredients = entry.get("ingredients") or []
    ingredient_names: List[str] = []
    if isinstance(raw_ingredients, list):
        for ingredient in raw_ingredients:
            name = ""
            if isinstance(ingredient, dict):
                name = str(ingredient.get("name") or "").strip()
            elif isinstance(ingredient, str):
                name = ingredient.strip()
            if name:
                ingredient_names.append(name)

    cooking_time = _as_int(entry.get("cooking_time"))
    calories = _as_int(entry.get("calories"))

    return StaticRecipeSummary(
        id=f"{index + 1:04d}",
        title=str(entry.get("name") or f"レシピ {index + 1}"),
        detail_path=f"{RECIPE_PAGES_ROUTE}/{file_name}",
        ingredients=ingredient_names,
        cooking_time=cooking_time,
        calories=calories,
    )


def _load_static_recipe_catalog() -> List[StaticRecipeSummary]:
    if not STATIC_RECIPE_HTML_DIR.exists() or not STATIC_RECIPE_JSON_PATH.exists():
        return []
    try:
        with STATIC_RECIPE_JSON_PATH.open(encoding="utf-8") as fp:
            payload = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []

    summaries: List[StaticRecipeSummary] = []
    for idx, entry in enumerate(payload):
        summary = _parse_static_recipe_entry(idx, entry)
        if summary:
            summaries.append(summary)
    return summaries


@router.get("/static-catalog", response_model=List[StaticRecipeSummary])
def list_static_recipes() -> List[StaticRecipeSummary]:
    return _load_static_recipe_catalog()


def _serialize_recipe_flags(recipe: Recipe) -> Dict[str, bool]:
    return {field: bool(getattr(recipe, field, False)) for field in RECIPE_FLAG_FIELDS}


def _optional_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    override = request.app.dependency_overrides.get(get_current_user)
    if override:
        try:
            return override()
        except TypeError:
            return override(authorization=authorization, db=db)

    if not authorization:
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None


def _record_transaction(
    db: Session,
    *,
    user_id: int,
    food_id: int,
    user_food_id: int,
    quantity_after: Decimal,
    delta_g: Decimal,
    note: Optional[str] = None,
):
    from app.backend.models import UserFoodTransaction

    transaction = UserFoodTransaction(
        user_id=user_id,
        food_id=food_id,
        user_food_id=user_food_id,
        delta_g=delta_g,
        quantity_after_g=quantity_after,
        source_type=InventoryChangeSource.RECIPE_COOK,
        note=note,
    )
    db.add(transaction)


def _record_recipe_history(
    db: Session,
    *,
    user_id: int,
    recipe_id: int,
    servings: float,
    calories_per_serving: Optional[int],
):
    total_calories: Optional[int] = None
    if calories_per_serving is not None:
        try:
            total_calories = int(round(float(calories_per_serving) * float(servings)))
        except (TypeError, ValueError):
            total_calories = None

    history_row = UserRecipeHistory(
        user_id=user_id,
        recipe_id=recipe_id,
        servings=Decimal(str(servings)),
        calories_total=total_calories,
    )
    db.add(history_row)


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
def get_recipe_detail(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_optional_current_user),
):
    recipe = _fetch_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="レシピが見つかりません。")

    items = _build_ingredient_rows(db, recipe, current_user)
    flag_values = _serialize_recipe_flags(recipe)

    return RecipeDetailResponse(
        recipe_id=_require_int(recipe.recipe_id, "recipe_id"),
        recipe_name=str(getattr(recipe, "recipe_name", "")),
        description=getattr(recipe, "description", None),
        instructions=getattr(recipe, "instructions", None),
        cooking_time=getattr(recipe, "cooking_time", None),
        calories=getattr(recipe, "calories", None),
        **flag_values,
        ingredients=items,
    )


@router.post("/{recipe_id}/cook", response_model=CookRecipeResponse)
def cook_recipe(
    recipe_id: int,
    body: CookRecipeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = _fetch_recipe(db, recipe_id)

    multiplier = Decimal(str(body.servings or 1))
    if multiplier <= Decimal("0"):
        raise HTTPException(
            status_code=400, detail="servings は正の数で指定してください。"
        )

    recipe_foods = getattr(recipe, "recipe_foods", []) or []
    if not recipe_foods:
        raise HTTPException(status_code=400, detail="材料情報が登録されていません。")

    requirements: Dict[int, Decimal] = {}
    food_lookup: Dict[int, Food] = {}
    for rf in recipe_foods:
        food_id = _as_int(getattr(rf, "food_id", None))
        if food_id is None or not rf.food:
            continue
        required = Decimal(str(rf.quantity_g or 0)) * multiplier
        requirements[food_id] = required
        food_lookup[food_id] = rf.food

    if not requirements:
        raise HTTPException(status_code=400, detail="消費対象の食材がありません。")

    user_id = _require_int(current_user.user_id, "user_id")
    stock_map = _lock_user_stocks(db, user_id, list(requirements.keys()))
    _validate_stock_sufficiency(stock_map, requirements, food_lookup)

    recipe_id_int = _require_int(recipe.recipe_id, "recipe_id")
    consumed_rows = _consume_ingredients(
        db,
        current_user,
        stock_map,
        requirements,
        food_lookup,
        servings=body.servings,
        recipe_id=recipe_id_int,
    )

    _record_recipe_history(
        db,
        user_id=user_id,
        recipe_id=recipe_id_int,
        servings=body.servings,
        calories_per_serving=getattr(recipe, "calories", None),
    )

    db.commit()

    return CookRecipeResponse(
        recipe_id=recipe_id_int,
        recipe_name=str(getattr(recipe, "recipe_name", "")),
        servings=body.servings,
        consumed=consumed_rows,
    )


def _fetch_recipe(db: Session, recipe_id: int) -> Recipe:
    recipe = (
        db.query(Recipe)
        .options(joinedload(Recipe.recipe_foods).joinedload(RecipeFood.food))
        .filter(Recipe.recipe_id == recipe_id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="レシピが見つかりません。")
    return recipe


def _build_ingredient_rows(
    db: Session, recipe: Recipe, current_user: Optional[User]
) -> List[RecipeIngredientItem]:
    recipe_foods = getattr(recipe, "recipe_foods", []) or []
    if not recipe_foods:
        return []

    stock_lookup = _build_stock_lookup(db, current_user, recipe_foods)
    items: List[RecipeIngredientItem] = []

    for rf in recipe_foods:
        if not rf.food:
            continue
        food_id = _as_int(rf.food_id)
        if food_id is None:
            continue
        required_quantity = Decimal(str(rf.quantity_g or 0))
        available: Optional[float] = None
        missing: Optional[float] = None
        if stock_lookup:
            stock = stock_lookup.get(food_id)
            if stock:
                stock_quantity = Decimal(str(stock.quantity_g or 0))
                available = float(stock_quantity)
                shortage = required_quantity - stock_quantity
                missing = float(shortage) if shortage > Decimal("0") else 0.0
            else:
                missing = float(required_quantity)
        items.append(
            RecipeIngredientItem(
                food_id=food_id,
                food_name=str(rf.food.food_name),
                quantity_g=float(required_quantity),
                available_quantity_g=available,
                missing_quantity_g=missing,
            )
        )
    return items


def _build_stock_lookup(
    db: Session, current_user: Optional[User], recipe_foods: List[RecipeFood]
) -> Dict[int, UserFood]:
    if not current_user:
        return {}
    food_ids = [
        fid for fid in (_as_int(rf.food_id) for rf in recipe_foods) if fid is not None
    ]
    if not food_ids:
        return {}
    user_id = _require_int(current_user.user_id, "user_id")
    stocks = (
        db.query(UserFood)
        .filter(
            UserFood.user_id == user_id,
            UserFood.food_id.in_(food_ids),
            UserFood.status != IngredientStatus.DELETED,
        )
        .all()
    )
    lookup: Dict[int, UserFood] = {}
    for stock in stocks:
        fid = _as_int(stock.food_id)
        if fid is not None:
            lookup[fid] = stock
    return lookup


def _lock_user_stocks(
    db: Session, user_id: int, food_ids: List[int]
) -> Dict[int, UserFood]:
    if not food_ids:
        return {}
    stocks = (
        db.query(UserFood)
        .filter(
            UserFood.user_id == user_id,
            UserFood.food_id.in_(food_ids),
            UserFood.status != IngredientStatus.DELETED,
        )
        .with_for_update()
        .all()
    )
    locked: Dict[int, UserFood] = {}
    for stock in stocks:
        fid = _as_int(stock.food_id)
        if fid is not None:
            locked[fid] = stock
    return locked


def _validate_stock_sufficiency(
    stock_map: Dict[int, UserFood],
    requirements: Dict[int, Decimal],
    food_lookup: Dict[int, Food],
):
    missing: List[str] = []
    for food_id, required_quantity in requirements.items():
        stock = stock_map.get(food_id)
        available = Decimal(str(stock.quantity_g or 0)) if stock else Decimal("0")
        if available < required_quantity:
            food_name = str(food_lookup[food_id].food_name)
            shortage = required_quantity - available
            missing.append(f"{food_name} ({float(shortage):.1f}g不足)")
    if missing:
        raise HTTPException(
            status_code=400, detail="在庫が足りません: " + ", ".join(missing)
        )


def _consume_ingredients(
    db: Session,
    current_user: User,
    stock_map: Dict[int, UserFood],
    requirements: Dict[int, Decimal],
    food_lookup: Dict[int, Food],
    *,
    servings: float,
    recipe_id: int,
) -> List[CookedIngredient]:
    consumed_rows: List[CookedIngredient] = []
    note = f"cook recipe #{recipe_id} x {servings}"
    user_id = _require_int(current_user.user_id, "user_id")

    for food_id, required_quantity in requirements.items():
        stock = stock_map.get(food_id)
        if not stock:
            continue
        current_quantity = Decimal(str(stock.quantity_g or 0))
        remaining = current_quantity - required_quantity
        setattr(stock, "quantity_g", remaining)
        if remaining <= Decimal("0"):
            setattr(stock, "status", IngredientStatus.USED)
            setattr(stock, "quantity_g", Decimal("0"))
            remaining = Decimal("0")
        elif str(stock.status) == IngredientStatus.USED.value:
            setattr(stock, "status", IngredientStatus.UNUSED)

        stock_food_id = _require_int(stock.food_id, "food_id")
        stock_user_food_id = _require_int(stock.user_food_id, "user_food_id")

        _record_transaction(
            db,
            user_id=user_id,
            food_id=stock_food_id,
            user_food_id=stock_user_food_id,
            quantity_after=Decimal(str(stock.quantity_g or 0)),
            delta_g=required_quantity * Decimal("-1"),
            note=note,
        )

        consumed_rows.append(
            CookedIngredient(
                food_id=food_id,
                food_name=str(food_lookup[food_id].food_name),
                required_quantity_g=float(required_quantity),
                consumed_quantity_g=float(required_quantity),
                remaining_quantity_g=float(remaining),
            )
        )

    return consumed_rows
