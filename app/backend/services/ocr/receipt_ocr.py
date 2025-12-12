from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from app.backend.services.ocr.image_preprocessing.image_preprocessor import (
    EasyOCRPreprocessor,
)

if TYPE_CHECKING:  # pragma: no cover
    from app.backend.services.ocr.text_detection.text_detector import (
        ReceiptOCRProcessor,
    )

logger = logging.getLogger(__name__)


@dataclass
class OCRLine:
    line_id: int
    text: str
    confidence: float
    bbox: List[List[float]]
    center: List[float]


@dataclass
class ReceiptOCRResult:
    lines: List[OCRLine]
    processed_image_path: Path
    text_content: str


class ReceiptOCRService:
    """EasyOCR ベースのレシート OCR サービス"""

    def __init__(
        self,
        *,
        input_dir: Path,
        processed_dir: Path,
        languages: Optional[List[str]] = None,
        use_gpu: bool = False,
    ) -> None:
        self.input_dir = Path(input_dir)
        self.processed_dir = Path(processed_dir)
        self.languages = languages or ["ja", "en"]
        self.use_gpu = use_gpu
        self._processor: Optional["ReceiptOCRProcessor"] = None
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def process(self, filename: str) -> ReceiptOCRResult:
        if not filename:
            raise ValueError("filename must be provided")

        preprocessor = EasyOCRPreprocessor(
            image_path=filename,
            input_dir=str(self.input_dir),
            output_dir=str(self.processed_dir),
        )
        preprocessor.preprocess()
        processed_filename = f"{Path(filename).stem}_processed.png"
        preprocessor.save(processed_filename)
        processed_path = self.processed_dir / processed_filename

        processor = self._get_processor()
        regions = processor.detect_text_regions(processed_path)

        lines: List[OCRLine] = []
        for idx, region in enumerate(regions):
            text_value = str(region.get("text") or "").strip()
            confidence_value = float(region.get("confidence") or 0.0)
            bbox_value = region.get("bbox") or []
            center_value = region.get("center") or []

            bbox_typed: List[List[float]] = [
                [float(point[0]), float(point[1])] for point in bbox_value
            ]
            center_typed: List[float] = [float(c) for c in center_value]

            lines.append(
                OCRLine(
                    line_id=idx,
                    text=text_value,
                    confidence=confidence_value,
                    bbox=bbox_typed,
                    center=center_typed,
                )
            )

        text_content = "\n".join(line.text for line in lines if line.text)

        return ReceiptOCRResult(
            lines=lines,
            processed_image_path=processed_path,
            text_content=text_content,
        )

    def _get_processor(self):
        if self._processor is None:
            logger.info(
                "Initializing EasyOCR reader (languages=%s, gpu=%s)",
                self.languages,
                self.use_gpu,
            )
            from app.backend.services.ocr.text_detection.text_detector import (
                ReceiptOCRProcessor,
            )

            self._processor = ReceiptOCRProcessor(
                languages=self.languages,
                gpu=self.use_gpu,
            )
        return self._processor
