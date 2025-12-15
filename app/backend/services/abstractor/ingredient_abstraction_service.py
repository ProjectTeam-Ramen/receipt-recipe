from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.backend.models import IngredientAbstraction

_KATAKANA_START = ord("ァ")
_KATAKANA_END = ord("ヶ")


def _katakana_to_hiragana(text: str) -> str:
    chars = []
    for ch in text:
        code = ord(ch)
        if _KATAKANA_START <= code <= _KATAKANA_END:
            chars.append(chr(code - 0x60))
        else:
            chars.append(ch)
    return "".join(chars)


def normalize_raw_text(value: str) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = _katakana_to_hiragana(normalized)
    # collapse internal whitespace
    normalized = " ".join(normalized.split())
    return normalized


@dataclass
class AbstractionPayload:
    normalized_text: str
    resolved_food_name: str
    original_text: Optional[str] = None
    food_id: Optional[int] = None
    confidence: Optional[float] = None
    source: str = "ocr_predict"
    metadata: Optional[Dict[str, Any]] = None


class IngredientAbstractionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_normalized_text(
        self, normalized_text: str
    ) -> Optional[IngredientAbstraction]:
        if not normalized_text:
            return None
        return (
            self.db.query(IngredientAbstraction)
            .filter(IngredientAbstraction.normalized_text == normalized_text)
            .first()
        )

    def save(self, payload: AbstractionPayload) -> IngredientAbstraction:
        entity = self.get_by_normalized_text(payload.normalized_text)
        if entity is None:
            entity = IngredientAbstraction(
                normalized_text=payload.normalized_text,
                resolved_food_name=payload.resolved_food_name,
                original_text=payload.original_text,
                food_id=payload.food_id,
                confidence=payload.confidence,
                source=payload.source,
                metadata_payload=payload.metadata,
            )
            self.db.add(entity)
        else:
            entity.resolved_food_name = payload.resolved_food_name
            entity.original_text = payload.original_text or entity.original_text
            entity.food_id = payload.food_id
            entity.confidence = payload.confidence
            entity.source = payload.source
            entity.metadata_payload = payload.metadata or entity.metadata_payload

        self.db.flush()
        return entity


class IngredientAbstractionService:
    def __init__(self, db: Session):
        self.repo = IngredientAbstractionRepository(db)

    def find(self, raw_text: str) -> Optional[IngredientAbstraction]:
        normalized = normalize_raw_text(raw_text)
        if not normalized:
            return None
        return self.repo.get_by_normalized_text(normalized)

    def upsert(
        self,
        raw_text: str,
        *,
        resolved_food_name: str,
        food_id: Optional[int] = None,
        confidence: Optional[float] = None,
        source: str = "ocr_predict",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngredientAbstraction:
        normalized = normalize_raw_text(raw_text)
        if not normalized:
            raise ValueError("raw_text cannot be empty after normalization")
        payload = AbstractionPayload(
            normalized_text=normalized,
            resolved_food_name=resolved_food_name,
            original_text=raw_text,
            food_id=food_id,
            confidence=confidence,
            source=source,
            metadata=metadata,
        )
        return self.repo.save(payload)

    def resolve_ingredient(
        self,
        raw_text: str,
        top_k: int = 5,
        force_refresh: bool = False,
    ):
        normalized = normalize_raw_text(raw_text)
        if not normalized:
            raise ValueError("raw_text cannot be empty after normalization")

        # Here you would add the logic to resolve the ingredient,
        # potentially involving calling an external API or service.
        # For now, we'll just return a mock response.

        mock_response = {
            "ingredients": [
                {
                    "food_id": 1,
                    "name": "ジャガイモ",
                    "confidence": 0.98,
                    "source": "api",
                },
                {
                    "food_id": 2,
                    "name": "馬鈴薯",
                    "confidence": 0.95,
                    "source": "api",
                },
            ]
        }

        return mock_response
