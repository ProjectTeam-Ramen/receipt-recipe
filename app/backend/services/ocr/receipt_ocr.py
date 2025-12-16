from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Sequence

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


class OCRLineFilter:
    """Simple heuristic-based filter for OCR lines."""

    _numeric_only_pattern = re.compile(r"^[0-9０-９,\.\s]+$")
    _punct_only_pattern = re.compile(
        r"^[\-\=\~\^\*\+\|_\/\\#%&<>\"'`.,;:!?()\[\]\{\}\s]+$"
    )
    _japanese_pattern = re.compile(r"[ぁ-んァ-ヶ一-龥々〆〤]")
    _meaningful_pattern = re.compile(r"[A-Za-zぁ-んァ-ヶ一-龥々〆〤]")

    DEFAULT_KEYWORDS: Sequence[str] = (
        "登録番号",
        "スキャン",
        "レシート",
        "会計",
        "小計",
        "合計",
        "対象",
        "外税",
        "内税",
        "消費税",
        "税率",
        "軽減",
        "お預",
        "現金",
        "電子マネー",
        "クレジット",
        "pay",
        "買上",
        "お釣",
        "領収",
        "ポイント",
        "印は",
        "伝票",
        "株式会社",
        "有限会社",
        "取引",
        "領収書",
        "ご利用",
        "明細",
        "番号",
        "レジ",
        "店",
    )

    DEFAULT_REGEX_PATTERNS: Sequence[str] = (
        r"(?i)\btel[:\s\-]*\d",
        r"(?i)\bphone[:\s\-]*\d",
        r"(?i)\bno\.?\s*\d+",
        r"(?i)店\s*no",
        r"(?i)レシ.?ト\s*no",
        r"\d{4}[\/\-\.年]\d{1,2}[\/\-\.月]\d{1,2}",
        r"[RHrhS]\d{1,2}[\.\-]\d{1,2}[\.\-]\d{1,2}",
        r"\d{1,2}月\d{1,2}日",
        r"\d{1,2}[:時]\d{1,2}(?:[:分]|$)",
    )

    def __init__(
        self,
        *,
        min_length: int = 2,
        min_cjk_without_digits: int = 3,
        min_confidence: float = 0.2,
        keywords: Optional[Sequence[str]] = None,
        regex_patterns: Optional[Sequence[str]] = None,
    ) -> None:
        self.min_length = min_length
        self.min_cjk_without_digits = min_cjk_without_digits
        self.min_confidence = min_confidence
        self.keywords = tuple(
            unicodedata.normalize("NFKC", kw)
            for kw in (keywords or self.DEFAULT_KEYWORDS)
        )
        self.regex_patterns = [
            re.compile(pattern)
            for pattern in (regex_patterns or self.DEFAULT_REGEX_PATTERNS)
        ]

    def filter(self, lines: List["OCRLine"]) -> List["OCRLine"]:
        filtered: List["OCRLine"] = []
        for line in lines:
            if not self._should_drop(line):
                filtered.append(line)
        return filtered

    def _should_drop(self, line: "OCRLine") -> bool:
        text = line.text if line.text is not None else ""
        normalized = unicodedata.normalize("NFKC", text).strip()
        contains_digit = any(ch.isdigit() for ch in normalized)

        if self._basic_checks_fail(normalized, contains_digit, line.confidence):
            return True

        lower_normalized = normalized.lower()
        if self._matches_keywords(normalized, lower_normalized):
            return True

        if not contains_digit:
            return self._has_too_few_cjk(normalized)

        return not self._meaningful_pattern.search(normalized)

    def _basic_checks_fail(
        self,
        normalized: str,
        contains_digit: bool,
        confidence: Optional[float],
    ) -> bool:
        if not normalized:
            return True

        if len(normalized) < self.min_length and not contains_digit:
            return True

        if (
            confidence is not None
            and confidence < self.min_confidence
            and not (contains_digit and self._meaningful_pattern.search(normalized))
        ):
            return True

        if self._numeric_only_pattern.match(normalized):
            return True

        if self._punct_only_pattern.match(normalized):
            return True

        return False

    def _matches_keywords(self, normalized: str, lowered: str) -> bool:
        if any(keyword and keyword in normalized for keyword in self.keywords):
            return True

        return any(regex.search(lowered) for regex in self.regex_patterns)

    def _has_too_few_cjk(self, normalized: str) -> bool:
        cjk_count = sum(1 for ch in normalized if self._japanese_pattern.match(ch))
        return cjk_count < self.min_cjk_without_digits


@dataclass
class ReceiptOCRResult:
    lines: List[OCRLine]
    processed_image_path: Path
    text_content: str
    raw_lines: Optional[List[OCRLine]] = None


class ReceiptOCRService:
    """EasyOCR ベースのレシート OCR サービス"""

    def __init__(
        self,
        *,
        input_dir: Path,
        processed_dir: Path,
        languages: Optional[List[str]] = None,
        use_gpu: bool = False,
        line_filter: Optional[OCRLineFilter] = None,
    ) -> None:
        self.input_dir = Path(input_dir)
        self.processed_dir = Path(processed_dir)
        self.languages = languages or ["ja", "en"]
        self.use_gpu = use_gpu
        self._processor: Optional["ReceiptOCRProcessor"] = None
        self._line_filter = line_filter or OCRLineFilter()
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

        detected_lines: List[OCRLine] = []
        for idx, region in enumerate(regions):
            text_value = str(region.get("text") or "").strip()
            confidence_value = float(region.get("confidence") or 0.0)
            bbox_value = region.get("bbox") or []
            center_value = region.get("center") or []

            bbox_typed: List[List[float]] = [
                [float(point[0]), float(point[1])] for point in bbox_value
            ]
            center_typed: List[float] = [float(c) for c in center_value]

            detected_lines.append(
                OCRLine(
                    line_id=idx,
                    text=text_value,
                    confidence=confidence_value,
                    bbox=bbox_typed,
                    center=center_typed,
                )
            )

        raw_lines = list(detected_lines)
        filtered_lines = self._line_filter.filter(detected_lines)
        text_content = "\n".join(line.text for line in filtered_lines if line.text)

        return ReceiptOCRResult(
            lines=filtered_lines,
            processed_image_path=processed_path,
            text_content=text_content,
            raw_lines=raw_lines,
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
