from app.backend.services.ocr.receipt_ocr import OCRLine, OCRLineFilter


def make_line(text: str, confidence: float = 0.9, line_id: int = 0) -> OCRLine:
    return OCRLine(
        line_id=line_id,
        text=text,
        confidence=confidence,
        bbox=[],
        center=[],
    )


def test_filter_removes_known_keywords():
    filterer = OCRLineFilter()
    lines = [
        make_line("小計 1,234"),
        make_line("蒼天の水2L富士山 188"),
        make_line("*印は軽減税率"),
    ]

    filtered = filterer.filter(lines)

    assert len(filtered) == 1
    assert filtered[0].text == "蒼天の水2L富士山 188"


def test_filter_drops_low_confidence_noise_without_digits():
    filterer = OCRLineFilter(min_confidence=0.5)
    noisy = make_line(":町n", confidence=0.1, line_id=1)
    valid = make_line("ミンティアブリーズ 198", confidence=0.8, line_id=2)

    filtered = filterer.filter([noisy, valid])

    assert len(filtered) == 1
    assert filtered[0].line_id == 2


def test_filter_keeps_text_without_digits_if_rich_in_cjk():
    filterer = OCRLineFilter()
    line_without_digits = make_line("レジ袋粉", confidence=0.9, line_id=3)

    filtered = filterer.filter([line_without_digits])

    assert filtered == [line_without_digits]


def test_filter_drops_numeric_only_line():
    filterer = OCRLineFilter()
    numeric = make_line("1108", confidence=0.9, line_id=4)
    valid = make_line("アーモンドチョコレート 248", confidence=0.9, line_id=5)

    filtered = filterer.filter([numeric, valid])

    assert len(filtered) == 1
    assert filtered[0].line_id == 5
