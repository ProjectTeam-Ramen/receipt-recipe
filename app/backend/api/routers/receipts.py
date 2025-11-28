import os
import shutil
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()

DATA_DIR = Path(os.getenv("RECEIPT_DATA_DIR", "/workspace/data/receipt_image"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# simple in-memory store for demo
RECEIPTS: Dict[int, Dict] = {}
_NEXT_RECEIPT_ID = 1


class ItemModel(BaseModel):
    item_id: int
    raw_text: str
    food_id: Optional[int] = None
    food_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[int] = None
    category: Optional[str] = None
    confidence: Optional[float] = None


def _process_receipt_async(receipt_id: int, file_path: Path):
    """Mock processing: populate one item and mark completed."""
    receipt = RECEIPTS.get(receipt_id)
    if not receipt:
        return
    # In real system: OCR, parsing, mapping
    receipt["items"] = [
        {
            "item_id": 1,
            "raw_text": "トマト 2個 200円",
            "food_id": 10,
            "food_name": "トマト",
            "quantity": 2,
            "unit": "個",
            "price": 200,
            "category": "野菜",
            "confidence": 0.95,
        }
    ]
    receipt["status"] = "completed"


@router.post("/upload", status_code=202)
async def upload_receipt(
    file: UploadFile = File(...),
    background_tasks: Optional[BackgroundTasks] = None,
    callback_url: Optional[str] = None,
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

    RECEIPTS[receipt_id] = {
        "receipt_id": receipt_id,
        "user_id": None,
        "store_name": None,
        "purchase_date": None,
        "total_amount": None,
        "tax_amount": None,
        "items": [],
        "ocr_confidence": None,
        "image_path": str(file_path),
        "status": "processing",
        "created_at": None,
        "updated_at": None,
    }

    # schedule background processing (mock)
    if background_tasks is not None:
        background_tasks.add_task(_process_receipt_async, receipt_id, file_path)
    else:
        _process_receipt_async(receipt_id, file_path)

    return {
        "receipt_id": receipt_id,
        "status": "processing",
        "message": "Receipt uploaded. Processing started.",
    }


@router.get("/{receipt_id}/status")
def receipt_status(receipt_id: int):
    r = RECEIPTS.get(receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return {
        "receipt_id": receipt_id,
        "status": r.get("status"),
        "progress": 100 if r.get("status") == "completed" else 0,
    }


@router.get("/{receipt_id}")
def get_receipt(receipt_id: int):
    r = RECEIPTS.get(receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Receipt not found")
    # present a copy without internal path
    out = r.copy()
    out.pop("image_path", None)
    return out


@router.get("/{receipt_id}/image")
def get_receipt_image(receipt_id: int):
    r = RECEIPTS.get(receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Receipt not found")
    path = r.get("image_path")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@router.patch("/{receipt_id}/items/{detail_id}")
def patch_receipt_item(receipt_id: int, detail_id: int, body: Dict):
    r = RECEIPTS.get(receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Receipt not found")
    items = r.get("items", [])
    for it in items:
        if it.get("item_id") == detail_id:
            it.update(body)
            return it
    raise HTTPException(status_code=404, detail="Item not found")
