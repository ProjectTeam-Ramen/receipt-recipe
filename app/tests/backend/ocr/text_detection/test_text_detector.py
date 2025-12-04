import json
from pathlib import Path

import cv2
import pytest

from app.backend.services.ocr.text_detection.text_detector import ReceiptOCRProcessor


@pytest.fixture
def sample_receipt_image():
    """テスト用のレシート画像パス"""
    image_path = Path("app/data/processed_receipt_image/receipt_custom.jpg")
    if not image_path.exists():
        pytest.skip(f"Test image not found: {image_path}")
    return str(image_path)


@pytest.fixture
def ocr_processor():
    """OCRプロセッサのインスタンス"""
    return ReceiptOCRProcessor(languages=["ja", "en"], gpu=False)


@pytest.fixture
def output_dir(tmp_path):
    """テスト用の出力ディレクトリ"""
    return tmp_path / "test_output"


class TestReceiptOCRProcessor:
    """ReceiptOCRProcessorのテストクラス"""

    def test_initialization(self):
        """初期化のテスト"""
        processor = ReceiptOCRProcessor(languages=["ja", "en"], gpu=False)
        assert processor.reader is not None

    def test_initialization_with_defaults(self):
        """デフォルト設定での初期化テスト"""
        processor = ReceiptOCRProcessor()
        assert processor.reader is not None

    def test_detect_text_regions(self, ocr_processor, sample_receipt_image):
        """文字領域検出のテスト"""
        text_regions = ocr_processor.detect_text_regions(sample_receipt_image)

        # 基本的な検証
        assert isinstance(text_regions, list)
        assert len(text_regions) > 0

        # 各領域の構造を検証
        for region in text_regions:
            assert "region_id" in region
            assert "bbox" in region
            assert "text" in region
            assert "confidence" in region
            assert "center" in region

            # bboxは4点の座標
            assert len(region["bbox"]) == 4
            assert all(len(point) == 2 for point in region["bbox"])

            # centerは2次元座標
            assert len(region["center"]) == 2

            # 信頼度は0-1の範囲
            assert 0 <= region["confidence"] <= 1

    def test_detect_text_regions_file_not_found(self, ocr_processor):
        """存在しないファイルのテスト"""
        with pytest.raises(FileNotFoundError):
            ocr_processor.detect_text_regions("nonexistent_image.jpg")

    def test_extract_character_regions(self, ocr_processor, sample_receipt_image):
        """文字分割のテスト"""
        character_data = ocr_processor.extract_character_regions(
            sample_receipt_image, padding=2
        )

        # 基本的な検証
        assert isinstance(character_data, list)
        assert len(character_data) > 0

        # 各文字情報の構造を検証
        for char_info in character_data:
            assert "char_id" in char_info
            assert "region_id" in char_info
            assert "char" in char_info
            assert "char_index_in_region" in char_info
            assert "bbox" in char_info
            assert "center" in char_info
            assert "confidence" in char_info
            assert "image_shape" in char_info

            # bboxは4要素 [x_min, y_min, x_max, y_max]
            assert len(char_info["bbox"]) == 4

            # centerは2次元座標
            assert len(char_info["center"]) == 2

            # image_shapeは3要素 [height, width, channels]
            assert len(char_info["image_shape"]) == 3

    def test_save_character_images(
        self, ocr_processor, sample_receipt_image, output_dir
    ):
        """文字画像保存のテスト"""
        metadata = ocr_processor.save_character_images(
            sample_receipt_image, output_dir, padding=2
        )

        # メタデータの検証
        assert "source_image" in metadata
        assert "total_characters" in metadata
        assert "characters" in metadata
        assert metadata["total_characters"] > 0

        # 出力ディレクトリの検証
        assert output_dir.exists()

        # メタデータファイルの検証
        metadata_path = output_dir / "metadata.json"
        assert metadata_path.exists()

        with open(metadata_path, "r", encoding="utf-8") as f:
            loaded_metadata = json.load(f)
            assert loaded_metadata == metadata

        # 文字画像ファイルの検証
        char_images = list(output_dir.glob("char_*.png"))
        assert len(char_images) > 0

        # 各画像ファイルが読み込めることを確認
        for img_path in char_images[:5]:  # 最初の5枚をチェック
            img = cv2.imread(str(img_path))
            assert img is not None
            assert img.size > 0

    def test_visualize_regions(self, ocr_processor, sample_receipt_image, output_dir):
        """可視化のテスト"""
        output_dir.mkdir(parents=True, exist_ok=True)
        visualization_path = output_dir / "visualization.jpg"

        # 可視化を実行
        result_image = ocr_processor.visualize_regions(
            sample_receipt_image, visualization_path
        )

        # 返り値の検証
        assert result_image is not None
        assert isinstance(result_image, type(cv2.imread(sample_receipt_image)))

        # 出力ファイルの検証
        assert visualization_path.exists()

        # 出力画像が読み込めることを確認
        saved_image = cv2.imread(str(visualization_path))
        assert saved_image is not None
        assert saved_image.shape == result_image.shape

    def test_visualize_regions_without_saving(
        self, ocr_processor, sample_receipt_image
    ):
        """保存なしの可視化テスト"""
        result_image = ocr_processor.visualize_regions(sample_receipt_image)

        assert result_image is not None
        assert isinstance(result_image, type(cv2.imread(sample_receipt_image)))

    def test_calculate_center(self):
        """中心座標計算のテスト"""
        bbox = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
        center = ReceiptOCRProcessor._calculate_center(bbox)

        assert len(center) == 2
        assert center[0] == 5.0  # x座標
        assert center[1] == 5.0  # y座標

    def test_padding_parameter(self, ocr_processor, sample_receipt_image):
        """パディングパラメータのテスト"""
        # パディング無し
        chars_no_padding = ocr_processor.extract_character_regions(
            sample_receipt_image, padding=0
        )

        # パディングあり
        chars_with_padding = ocr_processor.extract_character_regions(
            sample_receipt_image, padding=5
        )

        # 文字数は同じはず
        assert len(chars_no_padding) == len(chars_with_padding)

        # パディングありの方が画像サイズが大きいはず
        for no_pad, with_pad in zip(chars_no_padding, chars_with_padding):
            bbox_no_pad = no_pad["bbox"]
            bbox_with_pad = with_pad["bbox"]

            width_no_pad = bbox_no_pad[2] - bbox_no_pad[0]
            width_with_pad = bbox_with_pad[2] - bbox_with_pad[0]

            height_no_pad = bbox_no_pad[3] - bbox_no_pad[1]
            height_with_pad = bbox_with_pad[3] - bbox_with_pad[1]

            assert width_with_pad >= width_no_pad
            assert height_with_pad >= height_no_pad


class TestReceiptOCRProcessorIntegration:
    """統合テスト"""

    def test_full_workflow(self, sample_receipt_image, output_dir):
        """完全なワークフローのテスト"""
        # 1. プロセッサの初期化
        processor = ReceiptOCRProcessor(languages=["ja", "en"], gpu=False)

        # 2. 文字領域の検出
        text_regions = processor.detect_text_regions(sample_receipt_image)
        assert len(text_regions) > 0

        # 3. 文字レベルへの分割
        character_data = processor.extract_character_regions(sample_receipt_image)
        assert len(character_data) > 0

        # 4. 文字画像の保存
        metadata = processor.save_character_images(sample_receipt_image, output_dir)
        assert metadata["total_characters"] == len(character_data)

        # 5. 可視化
        viz_path = output_dir / "visualization.jpg"
        processor.visualize_regions(sample_receipt_image, viz_path)
        assert viz_path.exists()

        # 最終検証
        assert (output_dir / "metadata.json").exists()
        assert len(list(output_dir.glob("char_*.png"))) > 0
