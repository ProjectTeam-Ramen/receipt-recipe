from datetime import date
from decimal import Decimal
from typing import List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.backend.database import get_db
from app.backend.models import (
    Food,
    FoodCategory,
    IngredientStatus,
    User,
    UserFood,
)

from .auth_routes import get_current_user

router = APIRouter()

DEFAULT_CATEGORY_NAME = "その他"


class IngredientCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity_g: float = Field(..., gt=0, le=100000)
    purchase_date: Optional[date] = None
    expiration_date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=100)
    status: IngredientStatus = IngredientStatus.UNUSED


class IngredientResponse(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)

    user_food_id: int
    food_id: int
    food_name: str
    quantity_g: float
    purchase_date: Optional[date] = None
    expiration_date: Optional[date] = None
    status: IngredientStatus


class IngredientListResponse(BaseModel):
    total: int
    ingredients: List[IngredientResponse]


class IngredientStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status: IngredientStatus


class IngredientConsumeRequest(BaseModel):
    quantity_g: float = Field(..., gt=0, le=100000)


def _normalize(value: str) -> str:
    return value.strip()


def _get_or_create_category(db: Session, name: Optional[str]) -> FoodCategory:
    normalized = _normalize(name) if name else DEFAULT_CATEGORY_NAME
    category = (
        db.query(FoodCategory)
        .filter(func.lower(FoodCategory.category_name) == normalized.lower())
        .first()
    )
    if category:
        return category

    category = FoodCategory(category_name=normalized)
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        category = (
            db.query(FoodCategory)
            .filter(func.lower(FoodCategory.category_name) == normalized.lower())
            .first()
        )
        if category:
            return category
        raise
    db.refresh(category)
    return category


def _get_or_create_food(db: Session, name: str, category_id: int) -> Food:
    normalized = _normalize(name)
    food = (
        db.query(Food).filter(func.lower(Food.food_name) == normalized.lower()).first()
    )
    if food:
        return food

    food = Food(food_name=normalized, category_id=category_id, is_trackable=True)
    db.add(food)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        food = (
            db.query(Food)
            .filter(func.lower(Food.food_name) == normalized.lower())
            .first()
        )
        if food:
            return food
        raise
    db.refresh(food)
    return food


def _to_response(user_food: UserFood) -> IngredientResponse:
    quantity = cast(Decimal, user_food.quantity_g)
    if isinstance(quantity, Decimal):
        quantity = float(quantity)
    purchase_date = cast(Optional[date], user_food.purchase_date)
    expiration_date = cast(Optional[date], user_food.expiration_date)
    user_food_id = cast(int, user_food.user_food_id)
    food_id = cast(int, user_food.food_id)
    status_raw = user_food.status
    if isinstance(status_raw, str):
        status_value: IngredientStatus = IngredientStatus(status_raw)
    else:
        status_value = cast(IngredientStatus, status_raw)
    return IngredientResponse(
        user_food_id=user_food_id,
        food_id=food_id,
        food_name=user_food.food.food_name if user_food.food else "",
        quantity_g=quantity,
        purchase_date=purchase_date,
        expiration_date=expiration_date,
        status=status_value,
    )


@router.post(
    "/", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED
)
def create_ingredient(
    body: IngredientCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = _normalize(body.name)
    if not name:
        raise HTTPException(status_code=400, detail="食材名を入力してください。")

    category = _get_or_create_category(db, body.category)
    food = _get_or_create_food(db, name, cast(int, category.category_id))

    user_food = UserFood(
        user_id=current_user.user_id,
        food_id=food.food_id,
        quantity_g=body.quantity_g,
        purchase_date=body.purchase_date,
        expiration_date=body.expiration_date,
        status=body.status,
    )
    db.add(user_food)
    db.commit()
    db.refresh(user_food)
    return _to_response(user_food)


@router.get("/", response_model=IngredientListResponse)
def list_ingredients(
    status: Optional[IngredientStatus] = Query(
        None,
        description="絞り込み対象のステータス。指定しない場合は削除済み以外を返します。",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(UserFood)
        .filter(UserFood.user_id == current_user.user_id)
        .join(Food)
        .order_by(UserFood.expiration_date.is_(None), UserFood.expiration_date)
    )
    if status:
        query = query.filter(UserFood.status == status)
    else:
        query = query.filter(UserFood.status != IngredientStatus.DELETED)
    items = query.all()
    return IngredientListResponse(
        total=len(items),
        ingredients=[_to_response(item) for item in items],
    )


@router.patch("/{user_food_id}/status", response_model=IngredientResponse)
def update_ingredient_status(
    user_food_id: int,
    body: IngredientStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_food = (
        db.query(UserFood)
        .filter(
            UserFood.user_food_id == user_food_id,
            UserFood.user_id == current_user.user_id,
        )
        .first()
    )
    if not user_food:
        raise HTTPException(status_code=404, detail="食材が見つかりません。")

    setattr(user_food, "status", body.status)
    db.commit()
    db.refresh(user_food)
    return _to_response(user_food)


@router.post("/{user_food_id}/consume", response_model=IngredientResponse)
def consume_ingredient(
    user_food_id: int,
    body: IngredientConsumeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_food = (
        db.query(UserFood)
        .filter(
            UserFood.user_food_id == user_food_id,
            UserFood.user_id == current_user.user_id,
        )
        .first()
    )
    if not user_food:
        raise HTTPException(status_code=404, detail="食材が見つかりません。")
    status_value_raw = getattr(user_food, "status")
    status_value = (
        IngredientStatus(status_value_raw)
        if isinstance(status_value_raw, str)
        else cast(IngredientStatus, status_value_raw)
    )
    if status_value == IngredientStatus.DELETED:
        raise HTTPException(status_code=400, detail="削除済みの食材は更新できません。")

    stored_quantity = getattr(user_food, "quantity_g")
    current_quantity = (
        Decimal(str(stored_quantity)) if stored_quantity is not None else Decimal("0")
    )
    consume_quantity = Decimal(str(body.quantity_g))
    if consume_quantity > current_quantity:
        raise HTTPException(
            status_code=400, detail="在庫を超える数量は指定できません。"
        )

    remaining = current_quantity - consume_quantity
    setattr(user_food, "quantity_g", remaining)
    if remaining <= Decimal("0"):
        setattr(user_food, "status", IngredientStatus.USED)
        setattr(user_food, "quantity_g", Decimal("0"))
    elif status_value == IngredientStatus.USED:
        setattr(user_food, "status", IngredientStatus.UNUSED)

    db.commit()
    db.refresh(user_food)
    return _to_response(user_food)
