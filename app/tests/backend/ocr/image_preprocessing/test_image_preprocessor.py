import os

import cv2
import numpy as np
import pytest

from app.backend.services.ocr.image_preprocessing.image_preprocessor import (
    ReceiptPreprocessor,
)


@pytest.fixture
def sample_image(tmp_path):
    """サンプル画像を生成して一時ディレクトリに保存"""
    image = np.full((100, 100, 3), 255, dtype=np.uint8)  # 白い画像
    image_path = tmp_path / "sample.jpg"
    getattr(cv2, "imwrite")(str(image_path), image)
    return str(image_path)


def test_grayscale(sample_image):
    """グレースケール化のテスト"""
    preprocessor = ReceiptPreprocessor(image_path=sample_image)
    processed = preprocessor.grayscale()
    assert len(processed.shape) == 2, "グレースケール化に失敗しました"


def test_binarize(sample_image):
    """二値化処理のテスト"""
    preprocessor = ReceiptPreprocessor(image_path=sample_image)
    preprocessor.grayscale()
    processed = preprocessor.binarize(method="adaptive", block_size=15, c=10)
    assert processed is not None, "二値化処理に失敗しました"
    unique_values = np.unique(processed).tolist()
    assert unique_values in [[0, 255], [255]], "二値化が正しく行われていません"


def test_denoise(sample_image):
    """ノイズ除去のテスト"""
    preprocessor = ReceiptPreprocessor(image_path=sample_image)
    preprocessor.grayscale()
    processed = preprocessor.denoise(method="bilateral", strength=9)
    assert processed is not None, "ノイズ除去に失敗しました"


def test_correct_skew(sample_image):
    """傾き補正のテスト"""
    preprocessor = ReceiptPreprocessor(image_path=sample_image)
    preprocessor.grayscale()
    processed, angle = preprocessor.correct_skew()
    assert processed is not None, "傾き補正に失敗しました"
    assert abs(angle) <= 45, "検出された角度が不正です"


def test_preprocess(sample_image):
    """全体の前処理のテスト"""
    preprocessor = ReceiptPreprocessor(image_path=sample_image)
    processed = preprocessor.preprocess()
    assert processed is not None, "前処理に失敗しました"


def test_save(sample_image, tmp_path):
    """画像保存のテスト"""
    preprocessor = ReceiptPreprocessor(
        image_path=sample_image, output_dir=str(tmp_path)
    )
    preprocessor.preprocess()
    output_path = tmp_path / "processed.jpg"
    preprocessor.save(output_filename="processed.jpg")
    assert os.path.exists(output_path), "画像の保存に失敗しました"


def test_reset(sample_image):
    """リセット機能のテスト"""
    preprocessor = ReceiptPreprocessor(image_path=sample_image)
    preprocessor.grayscale()
    preprocessor.reset()
    assert np.array_equal(preprocessor.get_original(), preprocessor.get_processed()), (
        "リセットに失敗しました"
    )
