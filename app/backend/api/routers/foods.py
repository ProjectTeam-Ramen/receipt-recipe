from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.database import get_db
from app.backend.models import Food, FoodCategory, User

from .auth_routes import get_current_user

router = APIRouter()


class FoodResponse(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    food_id: int
    food_name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None


class FoodListResponse(BaseModel):
    total: int
    foods: List[FoodResponse]


@router.get("/", response_model=FoodListResponse)
def list_foods(
    q: Optional[str] = Query(None, description="部分一致検索ワード"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = (
        db.query(Food, FoodCategory)
        .join(FoodCategory, Food.category_id == FoodCategory.category_id, isouter=True)
        .filter(Food.is_trackable.is_(True))
    )
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.filter(func.lower(Food.food_name).like(like))

    items = query.order_by(Food.food_name.asc()).limit(limit).all()

    foods = [
        FoodResponse(
            food_id=food.food_id,
            food_name=food.food_name,
            category_id=category.category_id if category else None,
            category_name=category.category_name if category else None,
        )
        for food, category in items
    ]
    return FoodListResponse(total=len(foods), foods=foods)
