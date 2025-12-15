from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.api.routers.auth_routes import get_current_user
from app.backend.database import get_db
from app.backend.models import User
from app.backend.services.abstractor.ingredient_name_resolver import (
    IngredientNameResolver,
)

router = APIRouter()


class ResolveRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)
    force_refresh: bool = False
    top_k: int = Field(5, ge=1, le=10)


class ResolveResponse(BaseModel):
    normalized_text: str
    resolved_food_name: str
    food_id: Optional[int] = None
    confidence: Optional[float] = None
    source: str
    cached: bool
    metadata: Optional[Dict[str, Any]] = None


@router.post("/resolve", response_model=ResolveResponse)
def resolve_ingredient_name(
    body: ResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        resolver = IngredientNameResolver(db)
        result = resolver.resolve(
            body.raw_text,
            force_refresh=body.force_refresh,
            top_k=body.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    if not result.cached:
        db.commit()
    return ResolveResponse(
        normalized_text=result.normalized_text,
        resolved_food_name=result.resolved_food_name,
        food_id=result.food_id,
        confidence=result.confidence,
        source=result.source,
        cached=result.cached,
        metadata=result.metadata,
    )
