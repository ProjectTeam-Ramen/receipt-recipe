from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.backend.api.routers import receipts as receipts_module
from app.backend.api.routers.receipts import router as receipts_router


class DummyOCRService:
    def __init__(self, processed_dir: Path) -> None:
        self.processed_dir = processed_dir

    def process(self, filename: str):
        lines = [
            SimpleNamespace(
                line_id=0,
                text="りんご 2個 200円",
                confidence=0.92,
                bbox=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
                center=[0.5, 0.5],
            ),
            SimpleNamespace(
                line_id=1,
                text="牛乳 1本 150円",
                confidence=0.88,
                bbox=[[0.0, 1.0], [1.0, 1.0], [1.0, 2.0], [0.0, 2.0]],
                center=[0.5, 1.5],
            ),
        ]
        processed_path = self.processed_dir / f"{Path(filename).stem}_processed.png"
        return SimpleNamespace(
            lines=lines,
            processed_image_path=processed_path,
            text_content="\n".join(line.text for line in lines),
        )


def _build_test_app():
    app = FastAPI()
    app.include_router(receipts_router, prefix="/api/v1/receipts")
    return app


def test_receipt_upload_and_text_edit(tmp_path):
    data_dir = tmp_path / "receipt_image"
    processed_dir = tmp_path / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    original_data_dir = receipts_module.DATA_DIR
    original_processed_dir = receipts_module.PROCESSED_DATA_DIR
    original_service = receipts_module._OCR_SERVICE

    receipts_module.DATA_DIR = data_dir
    receipts_module.PROCESSED_DATA_DIR = processed_dir
    receipts_module._OCR_SERVICE = None

    dummy_service = DummyOCRService(processed_dir)

    app = _build_test_app()
    app.dependency_overrides[receipts_module._ocr_service_dependency] = (
        lambda: dummy_service
    )

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/receipts/upload",
                files={
                    "file": ("sample.png", io.BytesIO(b"fake"), "image/png"),
                },
            )
            assert resp.status_code == 202

            receipts_module._process_receipt_async(1, "receipt_1.png", dummy_service)

            status = client.get("/api/v1/receipts/1/status")
            assert status.status_code == 200
            assert status.json()["status"] == "completed"

            text_resp = client.get("/api/v1/receipts/1/text")
            assert text_resp.status_code == 200
            assert "りんご" in text_resp.json()["text"]

            patch_resp = client.patch(
                "/api/v1/receipts/1/items/1",
                json={"raw_text": "バナナ 3本 300円"},
            )
            assert patch_resp.status_code == 200

            plain_resp = client.get("/api/v1/receipts/1/text?format=plain")
            assert plain_resp.status_code == 200
            assert "バナナ" in plain_resp.text
    finally:
        receipts_module.DATA_DIR = original_data_dir
        receipts_module.PROCESSED_DATA_DIR = original_processed_dir
        receipts_module._OCR_SERVICE = original_service
