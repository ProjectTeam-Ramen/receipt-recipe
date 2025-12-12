import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

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


def _process_receipt_async(
    receipt_id: int,
    filename: str,
    ocr_service: ReceiptOCRService,
):
    receipt = RECEIPTS.get(receipt_id)
    if not receipt:
        return
    try:
        result = ocr_service.process(filename)
        receipt["items"] = []
        for idx, line in enumerate(result.lines, start=1):
            receipt["items"].append(
                {
                    "item_id": idx,
                    "raw_text": line.text,
                    "bbox": line.bbox,
                    "center": line.center,
                    "confidence": line.confidence,
                    "food_id": None,
                    "food_name": None,
                    "quantity": None,
                    "unit": None,
                    "price": None,
                    "category": None,
                }
            )

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
        receipt["processed_image_path"] = str(result.processed_image_path)
        receipt["ocr_confidence"] = (
            sum(line.confidence for line in result.lines) / len(result.lines)
            if result.lines
            else None
        )
        receipt["status"] = "completed"
        receipt["error"] = None
        receipt["text_content"] = result.text_content
    except Exception as exc:  # pragma: no cover - runtime dependency on EasyOCR
        logger.exception("OCR processing failed for receipt %s", receipt_id)
        receipt["status"] = "failed"
        receipt["error"] = str(exc)
    finally:
        receipt["updated_at"] = datetime.utcnow().isoformat()


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

    now = datetime.utcnow().isoformat()

    RECEIPTS[receipt_id] = {
        "receipt_id": receipt_id,
        "user_id": None,
        "store_name": None,
        "purchase_date": None,
        "total_amount": None,
        "tax_amount": None,
        "items": [],
        "text_lines": [],
        "text_content": "",
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


@router.get("/{receipt_id}/status")
def receipt_status(receipt_id: int):
    r = _get_receipt_or_404(receipt_id)
    return {
        "receipt_id": receipt_id,
        "status": r.get("status"),
        "progress": 100 if r.get("status") == "completed" else 0,
        "error": r.get("error"),
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
    r = _get_receipt_or_404(receipt_id)
    items = r.get("items", [])
    for it in items:
        if it.get("item_id") == detail_id:
            it.update(body)
            r["updated_at"] = datetime.utcnow().isoformat()
            _update_text_snapshot(r)
            return it
    raise HTTPException(status_code=404, detail="Item not found")
