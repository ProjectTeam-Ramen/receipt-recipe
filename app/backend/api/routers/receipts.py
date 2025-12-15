import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.backend.database import SessionLocal, get_db
from app.backend.models import Food, IngredientAbstraction
from app.backend.services.abstractor.ingredient_abstraction_service import (
    IngredientAbstractionService,
)
from app.backend.services.abstractor.ingredient_name_resolver import (
    IngredientNameResolver,
    ResolutionOutcome,
)
from app.backend.services.ocr.receipt_ocr import ReceiptOCRService

router = APIRouter()

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("RECEIPT_DATA_DIR", "/workspace/data/receipt_image"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROCESSED_DATA_DIR = Path(
    os.getenv("PROCESSED_RECEIPT_DATA_DIR", "/workspace/data/processed_receipt_image")
)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

OCR_LANGUAGES = [
    lang.strip()
    for lang in os.getenv("OCR_LANGUAGES", "ja,en").split(",")
    if lang.strip()
]
OCR_USE_GPU = os.getenv("OCR_USE_GPU", "0").lower() in {"1", "true", "yes"}

INGREDIENT_RESOLUTION_ENABLED = os.getenv(
    "ENABLE_INGREDIENT_RESOLUTION", "1"
).lower() not in {"0", "false", "no"}

_OCR_SERVICE: Optional[ReceiptOCRService] = None


def _get_ocr_service() -> ReceiptOCRService:
    global _OCR_SERVICE
    if _OCR_SERVICE is None:
        _OCR_SERVICE = ReceiptOCRService(
            input_dir=DATA_DIR,
            processed_dir=PROCESSED_DATA_DIR,
            languages=OCR_LANGUAGES or ["ja", "en"],
            use_gpu=OCR_USE_GPU,
        )
    return _OCR_SERVICE


def _ocr_service_dependency() -> ReceiptOCRService:
    return _get_ocr_service()


# simple in-memory store for demo
RECEIPTS: Dict[int, Dict] = {}
_NEXT_RECEIPT_ID = 1


def _build_resolver() -> Tuple[Optional[IngredientNameResolver], Optional[Any]]:
    """Create IngredientNameResolver + DB session while handling failures gracefully."""

    if not INGREDIENT_RESOLUTION_ENABLED:
        return None, None

    try:
        db = SessionLocal()
    except Exception as exc:  # pragma: no cover - database misconfiguration
        logger.warning(
            "Ingredient resolution disabled: failed to init DB session (%s)", exc
        )
        return None, None

    try:
        resolver = IngredientNameResolver(db)
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.info("Ingredient resolver unavailable: %s", exc)
        db.close()
        return None, None

    return resolver, db


class ItemModel(BaseModel):
    item_id: int
    raw_text: str
    bbox: Optional[list] = None
    center: Optional[list] = None
    food_id: Optional[int] = None
    food_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[int] = None
    category: Optional[str] = None
    confidence: Optional[float] = None


class ManualResolutionPayload(BaseModel):
    resolved_food_name: str = Field(..., min_length=1)
    food_id: Optional[int] = Field(None, ge=1)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    note: Optional[str] = Field(None, max_length=200)
    raw_text: Optional[str] = Field(None, min_length=1)


class FoodOption(BaseModel):
    food_id: int
    food_name: str


def _get_receipt_or_404(receipt_id: int) -> Dict:
    receipt = RECEIPTS.get(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


def _update_text_snapshot(receipt: Dict) -> None:
    items = receipt.get("items", [])
    receipt["text_content"] = "\n".join(
        str(item.get("raw_text") or "").strip()
        for item in items
        if item.get("raw_text")
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _process_receipt_async(
    receipt_id: int,
    filename: str,
    ocr_service: ReceiptOCRService,
):
    receipt = RECEIPTS.get(receipt_id)
    if not receipt:
        return
    resolver: Optional[IngredientNameResolver] = None
    db_session: Optional[Any] = None
    needs_commit = False
    try:
        resolver, db_session = _build_resolver()
        result = ocr_service.process(filename)
        receipt["items"] = []
        for idx, line in enumerate(result.lines, start=1):
            item, requires_commit = _build_item_from_line(idx, line, resolver)
            needs_commit = needs_commit or requires_commit
            receipt["items"].append(item)

        receipt["text_lines"] = [
            {
                "line_id": line.line_id,
                "text": line.text,
                "confidence": line.confidence,
                "bbox": line.bbox,
                "center": line.center,
            }
            for line in result.lines
        ]
        raw_lines = getattr(result, "raw_lines", None) or []
        receipt["raw_text_lines"] = [
            {
                "line_id": line.line_id,
                "text": line.text,
                "confidence": line.confidence,
                "bbox": line.bbox,
                "center": line.center,
            }
            for line in raw_lines
        ]
        receipt["processed_image_path"] = str(result.processed_image_path)
        receipt["ocr_confidence"] = (
            sum(line.confidence for line in result.lines) / len(result.lines)
            if result.lines
            else None
        )
        receipt["status"] = "completed"
        receipt["error"] = None
        receipt["text_content"] = result.text_content
        receipt["raw_text_content"] = "\n".join(
            line.text for line in raw_lines if line.text
        )

        if needs_commit and db_session is not None:
            try:
                db_session.commit()
            except Exception as exc:  # pragma: no cover - database specific
                logger.warning("Failed to commit ingredient resolutions: %s", exc)
                try:
                    db_session.rollback()
                except Exception:
                    logger.debug("Rollback failed after commit error")
    except Exception as exc:  # pragma: no cover - runtime dependency on EasyOCR
        logger.exception("OCR processing failed for receipt %s", receipt_id)
        receipt["status"] = "failed"
        receipt["error"] = str(exc)
    finally:
        receipt["updated_at"] = _utc_now_iso()
        if db_session is not None:
            try:
                db_session.close()
            except Exception:
                logger.debug("Failed to close DB session after OCR processing")


def _build_item_from_line(
    idx: int,
    line: Any,
    resolver: Optional[IngredientNameResolver],
) -> Tuple[Dict[str, Any], bool]:
    text_value = getattr(line, "text", "") or ""
    resolution: Optional[ResolutionOutcome] = None
    requires_commit = False
    if resolver and text_value.strip():
        try:
            resolution = resolver.resolve(text_value)
        except Exception as exc:
            logger.debug(
                "Ingredient resolution failed for line '%s': %s",
                text_value,
                exc,
            )
        else:
            if resolution and not resolution.cached:
                requires_commit = True

    item = {
        "item_id": idx,
        "raw_text": text_value,
        "bbox": line.bbox,
        "center": line.center,
        "confidence": line.confidence,
        "food_id": resolution.food_id if resolution else None,
        "food_name": resolution.resolved_food_name if resolution else None,
        "quantity": None,
        "unit": None,
        "price": None,
        "category": None,
        "ingredient_resolution": _serialize_resolution(resolution),
    }
    return item, requires_commit


def _serialize_resolution(
    resolution: Optional[ResolutionOutcome],
) -> Optional[Dict[str, Any]]:
    if not resolution:
        return None
    return {
        "resolved_food_name": resolution.resolved_food_name,
        "normalized_text": resolution.normalized_text,
        "food_id": resolution.food_id,
        "confidence": resolution.confidence,
        "source": resolution.source,
        "cached": resolution.cached,
        "metadata": resolution.metadata,
    }


@router.post("/upload", status_code=202)
async def upload_receipt(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    callback_url: Optional[str] = None,
    ocr_service: ReceiptOCRService = Depends(_ocr_service_dependency),
):
    global _NEXT_RECEIPT_ID
    filename_val = file.filename or "file"
    ext = Path(filename_val).suffix or ".jpg"
    receipt_id = _NEXT_RECEIPT_ID
    _NEXT_RECEIPT_ID += 1

    filename = f"receipt_{receipt_id}{ext}"
    file_path = DATA_DIR / filename
    # save file
    with file_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    now = _utc_now_iso()

    RECEIPTS[receipt_id] = {
        "receipt_id": receipt_id,
        "user_id": None,
        "store_name": None,
        "purchase_date": None,
        "total_amount": None,
        "tax_amount": None,
        "items": [],
        "text_lines": [],
        "raw_text_lines": [],
        "text_content": "",
        "raw_text_content": "",
        "ocr_confidence": None,
        "image_path": str(file_path),
        "processed_image_path": None,
        "status": "processing",
        "created_at": now,
        "updated_at": now,
        "error": None,
    }

    # schedule background processing
    background_tasks.add_task(
        _process_receipt_async,
        receipt_id,
        filename,
        ocr_service,
    )

    return {
        "receipt_id": receipt_id,
        "status": "processing",
        "message": "Receipt uploaded. Processing started.",
    }


@router.get("/food-options", response_model=List[FoodOption])
def list_food_options(
    query: Optional[str] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 500))
    stmt = db.query(Food)
    if query := (query or "").strip():
        stmt = stmt.filter(Food.food_name.ilike(f"%{query}%"))
    foods = stmt.order_by(Food.food_name.asc()).limit(limit).all()
    options: List[FoodOption] = []
    for food in foods:
        food_id_val = getattr(food, "food_id", None)
        food_name_val = getattr(food, "food_name", None)
        if food_id_val is None:
            continue
        options.append(
            FoodOption(
                food_id=int(food_id_val),
                food_name=food_name_val or str(food_id_val),
            )
        )
    return options


@router.get("/{receipt_id}/status")
def receipt_status(receipt_id: int):
    r = _get_receipt_or_404(receipt_id)
    return {
        "receipt_id": receipt_id,
        "status": r.get("status"),
        "progress": 100 if r.get("status") == "completed" else 0,
        "error": r.get("error"),
        "updated_at": r.get("updated_at"),
    }


@router.get("/{receipt_id}")
def get_receipt(receipt_id: int):
    r = _get_receipt_or_404(receipt_id)
    # present a copy without internal path
    out = r.copy()
    out.pop("image_path", None)
    return out


@router.get("/{receipt_id}/image")
def get_receipt_image(receipt_id: int):
    r = _get_receipt_or_404(receipt_id)
    path = r.get("image_path")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@router.get("/{receipt_id}/text")
def get_receipt_text(receipt_id: int, format: str = "json"):
    r = _get_receipt_or_404(receipt_id)
    text = r.get("text_content") or ""
    if format == "plain":
        return PlainTextResponse(text, media_type="text/plain")
    return {
        "receipt_id": receipt_id,
        "text": text,
        "status": r.get("status"),
        "line_count": len([line for line in text.splitlines() if line.strip()]),
        "updated_at": r.get("updated_at"),
    }


@router.patch("/{receipt_id}/items/{detail_id}")
def patch_receipt_item(receipt_id: int, detail_id: int, body: Dict):
    receipt = _get_receipt_or_404(receipt_id)
    item = _get_receipt_item(receipt, detail_id)
    manual_payload = body.pop("manual_resolution", None)
    parsed_manual: Optional[ManualResolutionPayload] = None
    if manual_payload:
        try:
            parsed_manual = ManualResolutionPayload(**manual_payload)
        except ValidationError as exc:  # pragma: no cover - bad payload
            raise HTTPException(status_code=400, detail=exc.errors()) from exc

    item.update(body)
    if parsed_manual:
        resolution = _persist_manual_resolution(item.get("raw_text", ""), parsed_manual)
        item["food_name"] = resolution.resolved_food_name
        item["food_id"] = resolution.food_id
        item["ingredient_resolution"] = _serialize_resolution(resolution)

    receipt["updated_at"] = datetime.utcnow().isoformat()
    _update_text_snapshot(receipt)
    return item


@router.post("/{receipt_id}/items/{detail_id}/manual-resolution")
def apply_manual_resolution(
    receipt_id: int,
    detail_id: int,
    payload: ManualResolutionPayload,
    db: Session = Depends(get_db),
):
    receipt = _get_receipt_or_404(receipt_id)
    item = _get_receipt_item(receipt, detail_id)

    if payload.raw_text:
        text_value = payload.raw_text.strip()
        if not text_value:
            raise HTTPException(status_code=400, detail="raw_text must not be blank")
        item["raw_text"] = text_value

    resolution = _persist_manual_resolution(
        item.get("raw_text", ""), payload, db_session=db
    )
    item["food_name"] = resolution.resolved_food_name
    item["food_id"] = resolution.food_id
    item["ingredient_resolution"] = _serialize_resolution(resolution)

    receipt["updated_at"] = datetime.utcnow().isoformat()
    _update_text_snapshot(receipt)
    return item


def _get_receipt_item(receipt: Dict, detail_id: int) -> Dict[str, Any]:
    for it in receipt.get("items", []):
        if it.get("item_id") == detail_id:
            return it
    raise HTTPException(status_code=404, detail="Item not found")


def _persist_manual_resolution(
    raw_text: str,
    payload: ManualResolutionPayload,
    db_session: Optional[Session] = None,
) -> ResolutionOutcome:
    text_value = (raw_text or "").strip()
    if not text_value:
        raise HTTPException(status_code=400, detail="raw_text must not be empty")

    owns_session = db_session is None
    session: Optional[Session] = db_session
    if session is None:
        try:
            session = SessionLocal()
        except Exception as exc:  # pragma: no cover - database misconfiguration
            raise HTTPException(
                status_code=503, detail="Failed to connect to database"
            ) from exc

    _ensure_abstraction_table(session)
    service = IngredientAbstractionService(session)
    metadata: Dict[str, Any] = {"manual_override": True}
    if payload.note:
        metadata["note"] = payload.note

    confidence = payload.confidence if payload.confidence is not None else 0.99

    entity = None
    resolution_fields: Dict[str, Any] = {}
    try:
        entity = service.upsert(
            text_value,
            resolved_food_name=payload.resolved_food_name,
            food_id=payload.food_id,
            confidence=confidence,
            source="manual_override",
            metadata=metadata,
        )
        session.commit()
        resolution_fields = _extract_resolution_fields(entity)
    except HTTPException:
        if owns_session and session is not None:
            session.rollback()
        raise
    except Exception as exc:
        if owns_session and session is not None:
            session.rollback()
        logger.exception("Failed to save manual correction: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to save correction"
        ) from exc
    finally:
        if owns_session and session is not None:
            session.close()

    resolved_attr = resolution_fields.get("resolved_food_name")
    normalized_attr = resolution_fields.get("normalized_text")
    food_id_attr = resolution_fields.get("food_id")
    confidence_attr = resolution_fields.get("confidence")
    source_attr = resolution_fields.get("source")
    metadata_attr = resolution_fields.get("metadata")

    confidence_value = float(confidence_attr) if confidence_attr is not None else None

    return ResolutionOutcome(
        resolved_food_name=resolved_attr or payload.resolved_food_name,
        normalized_text=normalized_attr or text_value,
        food_id=int(food_id_attr) if food_id_attr is not None else None,
        confidence=confidence_value,
        source=source_attr or "manual_override",
        cached=False,
        metadata=metadata_attr,
    )


def _ensure_abstraction_table(session: Optional[Session]) -> None:
    if session is None:
        return
    try:
        bind = session.get_bind()
        if bind is None:
            return
        IngredientAbstraction.__table__.create(bind=bind, checkfirst=True)
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.debug("Skipping table ensure due to error: %s", exc)


def _extract_resolution_fields(entity: Optional[Any]) -> Dict[str, Any]:
    if entity is None:
        return {}
    return {
        "resolved_food_name": getattr(entity, "resolved_food_name", None),
        "normalized_text": getattr(entity, "normalized_text", None),
        "food_id": getattr(entity, "food_id", None),
        "confidence": getattr(entity, "confidence", None),
        "source": getattr(entity, "source", "manual_override"),
        "metadata": getattr(entity, "metadata_payload", None),
    }
