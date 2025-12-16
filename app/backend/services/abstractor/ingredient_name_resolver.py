from __future__ import annotations

import difflib
import json
import logging
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, cast

from sqlalchemy.orm import Session

from app.backend.models import Food
from app.backend.services.abstractor.ingredient_abstraction_service import (
    IngredientAbstractionService,
    normalize_raw_text,
)
from app.backend.services.item_abstractor.image_recognition.image_recognizer_predict import (  # noqa: PLC0415
    get_top_predictions,
    predict_image,
)

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
LABEL_FILE = (
    Path(__file__).resolve().parents[1]
    / "item_abstractor"
    / "image_recognition"
    / "食材番号対応表.txt"
)

NUMBER_PATTERN = re.compile(r"[0-9０-９.,]+")
UNIT_PATTERN = re.compile(
    r"(個|本|袋|缶|玉|匹|枚|杯|皿|g|kg|グラム|ℓ|l|ml|cc|円|￥|パック|本体|％|%|割|本体価格)"
)


@dataclass
class Prediction:
    label: str
    probability: float
    index: Optional[int] = None
    food_name: Optional[str] = None

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "probability": self.probability,
            "index": self.index,
            "food_name": self.food_name,
        }


class PredictionProvider(Protocol):
    def predict(self, query: str, top_k: int = 5) -> List[Prediction]: ...


@dataclass
class FoodLookupEntry:
    food_id: int
    food_name: str


@dataclass
class LocalMatch:
    food_name: str
    normalized_token: str
    food_id: Optional[int]
    confidence: float
    source: str
    metadata: Dict[str, Any]


class FoodLabelMapper:
    def __init__(self, mapping_path: Path = LABEL_FILE):
        if not mapping_path.exists():
            raise FileNotFoundError(f"Food label file not found: {mapping_path}")
        self.mapping_path = mapping_path
        self.labels = self._load_labels(mapping_path)
        self.normalized_lookup = {
            normalize_raw_text(name): idx for idx, name in enumerate(self.labels)
        }

    @staticmethod
    def _load_labels(path: Path) -> List[str]:
        with path.open(encoding="utf-8") as fp:
            return [line.strip() for line in fp if line.strip()]

    def get_name(self, index: Optional[int]) -> Optional[str]:
        if index is None:
            return None
        if 0 <= index < len(self.labels):
            return self.labels[index]
        return None

    def resolve_label(self, label: str) -> Optional[int]:
        if not label:
            return None
        label_str = str(label).strip()
        if label_str.isdigit():
            idx = int(label_str)
            if 0 <= idx < len(self.labels):
                return idx
        normalized = normalize_raw_text(label_str)
        return self.normalized_lookup.get(normalized)


class GoogleImagePredictionProvider:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
        label_mapper: Optional[FoodLabelMapper] = None,
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = search_engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        if not self.api_key or not self.search_engine_id:
            raise RuntimeError(
                "GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID must be set to run predictions."
            )
        self.label_mapper = label_mapper or FoodLabelMapper()

    def predict(self, query: str, top_k: int = 5) -> List[Prediction]:
        query = (query or "").strip()
        if not query:
            raise ValueError("Query must not be empty")
        image_urls = self._fetch_image_urls(query, num=10)
        if not image_urls:
            raise RuntimeError("Image search returned no results")

        aggregate, successful = self._aggregate_predictions(image_urls)
        if successful == 0:
            raise RuntimeError("All image downloads or predictions failed")

        averaged = {k: v / successful for k, v in aggregate.items()}
        top_items = get_top_predictions(averaged, top_k)
        predictions: List[Prediction] = []
        for label, score in top_items:
            idx = self.label_mapper.resolve_label(label)
            predictions.append(
                Prediction(
                    label=str(label),
                    probability=score,
                    index=idx,
                    food_name=self.label_mapper.get_name(idx),
                )
            )
        return predictions

    def _aggregate_predictions(
        self, image_urls: Sequence[str]
    ) -> tuple[Dict[str, float], int]:
        aggregate: Dict[str, float] = {}
        successful = 0
        for url in image_urls:
            try:
                image_path = self._download_image(url)
            except Exception as exc:  # pragma: no cover - network
                logger.debug("Failed to download image %s: %s", url, exc)
                continue
            try:
                probs = predict_image(image_path)
            except Exception as exc:  # pragma: no cover - model/prediction
                logger.debug("Prediction failed for image %s: %s", image_path, exc)
            else:
                successful += 1
                for k, v in probs.items():
                    aggregate[k] = aggregate.get(k, 0.0) + float(v)
            finally:
                try:
                    image_path.unlink(missing_ok=True)
                except Exception:
                    logger.debug("Failed to delete temp image %s", image_path)
        return aggregate, successful

    def _fetch_image_url(self, query: str) -> Optional[str]:
        # kept for backward compatibility but prefer _fetch_image_urls
        urls = self._fetch_image_urls(query, num=1)
        return urls[0] if urls else None

    def _fetch_image_urls(self, query: str, num: int = 10) -> List[str]:
        params = {
            "q": query,
            "key": self.api_key,
            "cx": self.search_engine_id,
            "searchType": "image",
            "num": num,
            "safe": "off",
        }
        url = f"{GOOGLE_SEARCH_URL}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            raise RuntimeError(f"Google API error: {exc.code} {exc.reason}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - network
            raise RuntimeError("Failed to contact Google Custom Search API") from exc
        items = payload.get("items", []) if isinstance(payload, dict) else []
        urls: List[str] = []
        for item in items:
            link = item.get("link") if isinstance(item, dict) else None
            if link:
                urls.append(link)
                if len(urls) >= num:
                    break
        return urls

    def _download_image(self, url: str) -> Path:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; IngredientResolver/1.0)"}
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                content = response.read()
        except Exception as exc:  # pragma: no cover - network
            raise RuntimeError(f"Failed to download image: {exc}") from exc

        suffix = Path(urllib.parse.urlparse(url).path).suffix or ".jpg"
        fd, temp_path = tempfile.mkstemp(prefix="ingredient_resolver_", suffix=suffix)
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(content)
        return Path(temp_path)


@dataclass
class ResolutionOutcome:
    resolved_food_name: str
    normalized_text: str
    food_id: Optional[int]
    confidence: Optional[float]
    source: str
    cached: bool
    metadata: Optional[Dict[str, Any]]


class IngredientNameResolver:
    def __init__(
        self,
        db: Session,
        *,
        predictor: Optional[PredictionProvider] = None,
        label_mapper: Optional[FoodLabelMapper] = None,
    ) -> None:
        self.db = db
        self.label_mapper = label_mapper or FoodLabelMapper()
        self.predictor = predictor or self._build_default_predictor()
        self.abstraction_service = IngredientAbstractionService(db)
        self._food_lookup: Dict[str, FoodLookupEntry] = self._build_food_lookup()

    def _build_default_predictor(self) -> Optional[PredictionProvider]:
        try:
            return GoogleImagePredictionProvider(label_mapper=self.label_mapper)
        except RuntimeError as exc:
            logger.warning("Prediction provider unavailable: %s", exc)
            return None

    def _build_food_lookup(self) -> Dict[str, FoodLookupEntry]:
        lookup: Dict[str, FoodLookupEntry] = {}
        foods: Sequence[Food] = self.db.query(Food).all()
        for food in foods:
            food_name = getattr(food, "food_name", None)
            normalized = normalize_raw_text(food_name) if food_name else ""
            if normalized and normalized not in lookup:
                lookup[normalized] = FoodLookupEntry(
                    food_id=food.food_id,  # type: ignore[attr-defined]
                    food_name=food_name or normalized,
                )
        return lookup

    def _food_entry_for_name(
        self, food_name: Optional[str]
    ) -> Optional[FoodLookupEntry]:
        if not food_name:
            return None
        normalized = normalize_raw_text(food_name)
        return self._food_lookup.get(normalized)

    def _match_food_locally(self, raw_text: str) -> Optional[LocalMatch]:
        normalized_raw = normalize_raw_text(raw_text)
        candidates = self._generate_candidate_tokens(normalized_raw)

        for candidate in candidates:
            entry = self._food_lookup.get(candidate)
            if entry:
                confidence = 0.85 if candidate == normalized_raw else 0.65
                return LocalMatch(
                    food_name=entry.food_name,
                    normalized_token=candidate,
                    food_id=entry.food_id,
                    confidence=confidence,
                    source="normalized_lookup",
                    metadata={
                        "strategy": "food_lookup",
                        "matched_token": candidate,
                    },
                )

        for candidate in candidates:
            label_idx = self.label_mapper.resolve_label(candidate)
            if label_idx is None:
                continue
            label_name = self.label_mapper.get_name(label_idx)
            if not label_name:
                continue
            entry = self._food_entry_for_name(label_name)
            return LocalMatch(
                food_name=label_name,
                normalized_token=normalize_raw_text(label_name),
                food_id=entry.food_id if entry else None,
                confidence=0.55,
                source="label_mapper",
                metadata={
                    "strategy": "label_mapper",
                    "matched_token": candidate,
                    "label_index": label_idx,
                },
            )
        return None

    def _fuzzy_match_food(self, raw_text: str) -> Optional[LocalMatch]:
        normalized_raw = normalize_raw_text(raw_text)
        candidates = self._generate_candidate_tokens(normalized_raw)
        dictionary = list(self._food_lookup.keys())
        if not dictionary:
            return None

        for candidate in candidates:
            matches = difflib.get_close_matches(candidate, dictionary, n=1, cutoff=0.78)
            if not matches:
                continue
            matched_token = matches[0]
            entry = self._food_lookup.get(matched_token)
            if not entry:
                continue
            return LocalMatch(
                food_name=entry.food_name,
                normalized_token=matched_token,
                food_id=entry.food_id,
                confidence=0.5,
                source="fuzzy_lookup",
                metadata={
                    "strategy": "difflib",
                    "matched_token": matched_token,
                    "distance_token": candidate,
                },
            )
        return None

    @staticmethod
    def _generate_candidate_tokens(normalized_text: str) -> List[str]:
        tokens: List[str] = []
        base = (normalized_text or "").strip()
        if base:
            tokens.append(base)

        stripped_numbers = NUMBER_PATTERN.sub(" ", base)
        stripped_units = UNIT_PATTERN.sub(" ", stripped_numbers)
        cleaned = stripped_units.replace("　", " ")
        for token in cleaned.split():
            if token and token not in tokens:
                tokens.append(token)

        for segment in re.split(r"[／/・,、]", base):
            token = segment.strip()
            if token and token not in tokens:
                tokens.append(token)

        return tokens

    def resolve(
        self,
        raw_text: str,
        *,
        force_refresh: bool = False,
        top_k: int = 5,
    ) -> ResolutionOutcome:
        if not raw_text or not raw_text.strip():
            raise ValueError("raw_text must not be empty")
        if not force_refresh:
            existing = self.abstraction_service.find(raw_text)
        else:
            existing = None
        if existing:
            return self._build_outcome_from_entity(existing, cached=True)

        local_match = self._match_food_locally(raw_text)
        if local_match:
            entity = self.abstraction_service.upsert(
                raw_text,
                resolved_food_name=local_match.food_name,
                food_id=local_match.food_id,
                confidence=local_match.confidence,
                source=local_match.source,
                metadata=local_match.metadata,
            )
            return self._build_outcome_from_entity(entity, cached=False)

        fuzzy_match = self._fuzzy_match_food(raw_text)
        if fuzzy_match:
            entity = self.abstraction_service.upsert(
                raw_text,
                resolved_food_name=fuzzy_match.food_name,
                food_id=fuzzy_match.food_id,
                confidence=fuzzy_match.confidence,
                source=fuzzy_match.source,
                metadata=fuzzy_match.metadata,
            )
            return self._build_outcome_from_entity(entity, cached=False)

        predictions = self._predict(raw_text, top_k=top_k)
        best = self._select_best_prediction(predictions)
        if not best:
            return self._fallback_resolution(raw_text, reason="no_predictions")

        resolved_name = best.food_name or self._infer_name_from_label(best.label)
        if not resolved_name:
            return self._fallback_resolution(raw_text, reason="prediction_without_name")

        entry = self._food_entry_for_name(resolved_name)
        food_id = entry.food_id if entry else None
        metadata = {"predictions": [p.to_metadata() for p in predictions]}

        entity = self.abstraction_service.upsert(
            raw_text,
            resolved_food_name=resolved_name,
            food_id=food_id,
            confidence=best.probability,
            source="image_predictor",
            metadata=metadata,
        )
        return self._build_outcome_from_entity(entity, cached=False)

    @staticmethod
    def _infer_name_from_label(label: str) -> Optional[str]:
        if not label:
            return None
        label = str(label).strip()
        if not label:
            return None
        if label.isdigit():
            return None
        return label

    def _fallback_resolution(self, raw_text: str, *, reason: str) -> ResolutionOutcome:
        normalized = normalize_raw_text(raw_text)
        resolved_name = normalized or raw_text.strip() or "不明な食材"
        entity = self.abstraction_service.upsert(
            raw_text,
            resolved_food_name=resolved_name,
            food_id=None,
            confidence=0.3,
            source=f"fallback:{reason}",
            metadata={"reason": reason},
        )
        return self._build_outcome_from_entity(entity, cached=False)

    @staticmethod
    def _build_outcome_from_entity(entity: Any, *, cached: bool) -> ResolutionOutcome:
        resolved_food_name = cast(str, getattr(entity, "resolved_food_name", ""))
        normalized_text = cast(str, getattr(entity, "normalized_text", ""))
        food_id = cast(Optional[int], getattr(entity, "food_id", None))
        raw_confidence = cast(Optional[Decimal], getattr(entity, "confidence", None))
        confidence = float(raw_confidence) if raw_confidence is not None else None
        source = cast(str, getattr(entity, "source", "unknown"))
        metadata = cast(
            Optional[Dict[str, Any]], getattr(entity, "metadata_payload", None)
        )
        return ResolutionOutcome(
            resolved_food_name=resolved_food_name,
            normalized_text=normalized_text,
            food_id=food_id,
            confidence=confidence,
            source=source,
            cached=cached,
            metadata=metadata,
        )

    @staticmethod
    def _select_best_prediction(
        predictions: Sequence[Prediction],
    ) -> Optional[Prediction]:
        for prediction in predictions:
            if prediction.food_name:
                return prediction
        return predictions[0] if predictions else None

    def _predict(self, raw_text: str, *, top_k: int) -> Sequence[Prediction]:
        if not self.predictor:
            raise RuntimeError(
                "予測器が構成されていません。GOOGLE_API_KEY と GOOGLE_SEARCH_ENGINE_ID を設定するか、"
                "カスタム PredictionProvider を注入してください。"
            )
        return self.predictor.predict(raw_text, top_k=top_k)
