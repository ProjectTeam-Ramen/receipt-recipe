from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.backend.api.routers.auth_routes import get_current_user
from app.backend.database import get_db
from app.backend.models import User
from app.backend.services.recommendation.data_models import (
    Ingredient,
    RecommendationRequest,
    UserParameters,
)
from app.backend.services.recommendation.data_source import (
    InventoryManager,
    RecipeDataSource,
)
from app.backend.services.recommendation.proposer_logic import RecipeProposer

router = APIRouter()


class RecommendationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recipe_id: int
    recipe_name: str
    final_score: float
    coverage_score: float
    preference_score: float
    user_preference_vector: List[float]
    user_preference_labels: List[str]
    prep_time: int
    calories: int
    is_boosted: bool
    missing_items: List[str]
    required_qty: Dict[str, float]
    req_count: int
    image_url: Optional[str] = None
    inventory_source: Optional[str] = None
    inventory_count: Optional[int] = None
    inventory_label: Optional[str] = None


def _optional_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not authorization:
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None


def _parse_inventory_payload(payload: List[Dict]) -> List[Ingredient]:
    parsed: List[Ingredient] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        quantity_raw = item.get("quantity")
        try:
            quantity = float(quantity_raw) if quantity_raw is not None else 0.0
        except Exception:
            quantity = 0.0
        expiry_raw = item.get("expiration_date")
        expiry_date: Optional[date] = None
        if isinstance(expiry_raw, str) and expiry_raw:
            try:
                expiry_date = date.fromisoformat(expiry_raw)
            except ValueError:
                expiry_date = None
        parsed.append(
            Ingredient(name=name, quantity=quantity, expiration_date=expiry_date)
        )
    return parsed


def _resolve_target_user(
    body: RecommendationRequest, current_user: Optional[User]
) -> tuple[int, bool]:
    if current_user:
        current_user_id = getattr(current_user, "user_id", None)
        if not isinstance(current_user_id, int):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ユーザー情報が正しくありません。",
            )
        if body.user_id and body.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot request recommendations for another user",
            )
        return current_user_id, True

    if not isinstance(body.user_id, int):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be an integer when unauthenticated",
        )
    return body.user_id, False


def _resolve_inventory(
    body: RecommendationRequest,
    db: Session,
    user_id: int,
    is_authenticated: bool,
) -> tuple[List[Ingredient], str]:
    if is_authenticated:
        items = InventoryManager(db_session=db).get_current_inventory(user_id)
        return items, "server"

    if not body.inventory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="在庫データが指定されていません。ログインするか inventory を指定してください。",
        )
    return _parse_inventory_payload(body.inventory), "client"


@router.post("/propose", response_model=List[RecommendationResult])
def propose_recommendations(
    body: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_optional_current_user),
):
    target_user_id, is_authenticated = _resolve_target_user(body, current_user)
    inventory_items, inventory_source = _resolve_inventory(
        body, db, target_user_id, is_authenticated
    )

    recipe_source = RecipeDataSource(db_session=db)
    recipes = recipe_source.load_and_vectorize_recipes()
    if not recipes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="レシピデータが登録されていません。",
        )

    if body.history and body.recipes:
        user_profile_vector = recipe_source.build_profile_vector_from_payload(
            body.history, body.recipes
        )
    else:
        user_profile_vector = recipe_source.create_user_profile_vector(target_user_id)

    params = UserParameters(
        max_time=body.max_time,
        max_calories=body.max_calories,
        allergies=set(body.allergies or []),
    )

    proposer = RecipeProposer(
        all_recipes=recipes,
        user_inventory=inventory_items,
        user_profile_vector=user_profile_vector,
    )

    proposals = proposer.propose(params)
    if not proposals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="現在の在庫と条件に合うレシピが見つかりません。",
        )

    inventory_count = len(inventory_items)
    inventory_label = (
        f"サーバー在庫 {inventory_count}件"
        if inventory_source == "server"
        else f"指定在庫 {inventory_count}件"
    )
    for proposal in proposals:
        proposal.setdefault("inventory_source", inventory_source)
        proposal.setdefault("inventory_count", inventory_count)
        proposal.setdefault("inventory_label", inventory_label)

    return proposals
