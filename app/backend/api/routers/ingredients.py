from datetime import date
from decimal import Decimal
from typing import List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.backend.database import get_db
from app.backend.models import (
    Food,
    IngredientStatus,
    InventoryChangeSource,
    User,
    UserFood,
    UserFoodTransaction,
)

from .auth_routes import get_current_user

router = APIRouter()


class IngredientCreateRequest(BaseModel):
    food_id: int = Field(..., gt=0)
    quantity_g: float = Field(..., gt=0, le=100000)
    purchase_date: Optional[date] = None
    expiration_date: Optional[date] = None


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


def _record_inventory_transaction(
    db: Session,
    *,
    user: User,
    user_food: UserFood,
    delta_g: Decimal,
    source_type: InventoryChangeSource,
    note: Optional[str] = None,
    source_reference: Optional[str] = None,
):
    quantity_after = getattr(user_food, "quantity_g", None)
    quantity_after_decimal = (
        Decimal(str(quantity_after)) if quantity_after is not None else Decimal("0")
    )
    delta_decimal = delta_g if isinstance(delta_g, Decimal) else Decimal(str(delta_g))
    transaction = UserFoodTransaction(
        user_id=user.user_id,
        food_id=user_food.food_id,
        user_food_id=user_food.user_food_id,
        delta_g=delta_decimal,
        quantity_after_g=quantity_after_decimal,
        source_type=source_type,
        note=note,
        source_reference=source_reference,
    )
    db.add(transaction)


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
    food = (
        db.query(Food)
        .filter(Food.food_id == body.food_id, Food.is_trackable.is_(True))
        .first()
    )
    if not food:
        raise HTTPException(status_code=404, detail="指定された食材が存在しません。")

    user_food = (
        db.query(UserFood)
        .filter(
            UserFood.user_id == current_user.user_id,
            UserFood.food_id == food.food_id,
            UserFood.status != IngredientStatus.DELETED,
        )
        .first()
    )

    delta = Decimal(str(body.quantity_g))

    if user_food:
        current_quantity = Decimal(str(user_food.quantity_g or 0))
        updated_quantity = current_quantity + delta
        setattr(user_food, "quantity_g", updated_quantity)
        if body.purchase_date:
            setattr(user_food, "purchase_date", body.purchase_date)
        if body.expiration_date:
            setattr(user_food, "expiration_date", body.expiration_date)
        status_value_raw = getattr(user_food, "status")
        if isinstance(status_value_raw, str):
            status_value = IngredientStatus(status_value_raw)
        else:
            status_value = cast(IngredientStatus, status_value_raw)
        if updated_quantity > Decimal("0") and status_value == IngredientStatus.USED:
            setattr(user_food, "status", IngredientStatus.UNUSED)
    else:
        user_food = UserFood(
            user_id=current_user.user_id,
            food_id=food.food_id,
            quantity_g=delta,
            purchase_date=body.purchase_date,
            expiration_date=body.expiration_date,
            status=IngredientStatus.UNUSED,
        )
        db.add(user_food)
        db.flush()

    _record_inventory_transaction(
        db,
        user=current_user,
        user_food=user_food,
        delta_g=delta,
        source_type=InventoryChangeSource.MANUAL_ADD,
    )
    db.commit()
    db.refresh(user_food)
    return _to_response(user_food)


@router.get("/", response_model=IngredientListResponse)
def list_ingredients(
    status: Optional[IngredientStatus] = Query(
        None,
        description="絞り込み対象のステータス。指定しない場合は未使用(available) のみを返します。",
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
        # デフォルトでは未使用の食材のみを返す（残量0gになった used は非表示）
        query = query.filter(UserFood.status == IngredientStatus.UNUSED)
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
    if remaining <= Decimal("0"):
        setattr(user_food, "quantity_g", Decimal("0"))
        setattr(user_food, "status", IngredientStatus.USED)
    else:
        setattr(user_food, "quantity_g", remaining)
        setattr(user_food, "status", IngredientStatus.USED)

    _record_inventory_transaction(
        db,
        user=current_user,
        user_food=user_food,
        delta_g=consume_quantity * Decimal("-1"),
        source_type=InventoryChangeSource.MANUAL_CONSUME,
    )

    db.commit()
    db.refresh(user_food)
    return _to_response(user_food)


@router.delete("/{user_food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    user_food_id: int,
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
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    stored_quantity = getattr(user_food, "quantity_g", Decimal("0"))
    current_quantity = Decimal(str(stored_quantity or "0"))
    setattr(user_food, "status", IngredientStatus.DELETED)
    setattr(user_food, "quantity_g", Decimal("0"))

    if current_quantity != Decimal("0"):
        _record_inventory_transaction(
            db,
            user=current_user,
            user_food=user_food,
            delta_g=current_quantity * Decimal("-1"),
            source_type=InventoryChangeSource.ADJUSTMENT,
            note="manual delete",
        )

    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
