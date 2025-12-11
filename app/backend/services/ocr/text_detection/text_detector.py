import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import cv2
import easyocr
import numpy as np

logger = logging.getLogger(__name__)


class ReceiptOCRProcessor:
    """レシート画像からOCRを使用して文字領域を検出・分割するクラス"""

    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = False):
        """
        Args:
            languages: 認識する言語リスト
            gpu: GPU使用の有無（デフォルトはFalse、CPU使用）
        """
        if languages is None:
            languages = ["ja", "en"]

        try:
            self.reader = easyocr.Reader(
                languages,
                gpu=gpu,
                verbose=False,  # ログを抑制
            )
            logger.info(f"EasyOCR initialized with languages: {languages}, GPU: {gpu}")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise

    def detect_text_regions(self, image_path: Union[str, Path]) -> List[Dict]:
        """
        画像から文字領域を検出

        Args:
            image_path: 画像ファイルパス

        Returns:
            検出された文字領域情報のリスト
        """
        image_path = str(image_path)

        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        try:
            result = self.reader.readtext(image_path)
        except Exception as e:
            logger.error(f"Failed to read text from {image_path}: {e}")
            raise

        text_regions = []
        for idx, (bbox, text, confidence) in enumerate(result):
            # bboxは4点の座標 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            bbox_points = [
                [float(p[0]), float(p[1])] for p in bbox
            ]  # numpy型を回避し型を明確化
            region_info = {
                "region_id": idx,
                "bbox": bbox_points,
                "text": text,
                "confidence": float(confidence),
                "center": self._calculate_center(bbox_points),
            }
            text_regions.append(region_info)

        logger.info(f"Detected {len(text_regions)} text regions")
        return text_regions

    def extract_character_regions(
        self, image_path: Union[str, Path], padding: int = 2
    ) -> List[Dict]:
        """
        文字領域を一文字レベルに分割

        Args:
            image_path: 画像ファイルパス
            padding: 文字切り出し時のパディングピクセル数

        Returns:
            一文字ごとの情報リスト
        """
        image_path = str(image_path)
        image = cv2.imread(image_path)

        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        text_regions = self.detect_text_regions(image_path)

        character_data = []
        char_global_id = 0

        for region in text_regions:
            bbox = region["bbox"]
            text = region["text"]

            # バウンディングボックスから領域を切り出し
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            x_min, x_max = int(min(x_coords)), int(max(x_coords))
            y_min, y_max = int(min(y_coords)), int(max(y_coords))

            # 領域の幅を文字数で分割
            region_width = x_max - x_min
            num_chars = len(text)

            if num_chars == 0:
                continue

            char_width = region_width / num_chars

            for char_idx, char in enumerate(text):
                char_x_min = max(0, int(x_min + char_idx * char_width - padding))
                char_x_max = min(
                    image.shape[1], int(x_min + (char_idx + 1) * char_width + padding)
                )
                char_y_min = max(0, y_min - padding)
                char_y_max = min(image.shape[0], y_max + padding)

                # 文字画像を切り出し
                char_image = image[char_y_min:char_y_max, char_x_min:char_x_max]

                if char_image.size == 0:
                    logger.warning(
                        f"Empty char image for char_id={char_global_id}, "
                        f"bbox=[{char_x_min}, {char_y_min}, {char_x_max}, {char_y_max}]"
                    )
                    continue

                char_info = {
                    "char_id": char_global_id,
                    "region_id": region["region_id"],
                    "char": char,
                    "char_index_in_region": char_idx,
                    "bbox": [char_x_min, char_y_min, char_x_max, char_y_max],
                    "center": [
                        float((char_x_min + char_x_max) / 2),
                        float((char_y_min + char_y_max) / 2),
                    ],
                    "confidence": region["confidence"],
                    "image_shape": list(char_image.shape),
                }

                character_data.append(char_info)
                char_global_id += 1

        logger.info(f"Extracted {len(character_data)} characters")
        return character_data

    def save_character_images(
        self,
        image_path: Union[str, Path],
        output_dir: Union[str, Path],
        padding: int = 2,
    ) -> Dict:
        """
        一文字ごとの画像を保存

        Args:
            image_path: 入力画像パス
            output_dir: 出力ディレクトリ
            padding: パディングピクセル数

        Returns:
            処理結果の概要情報
        """
        image_path = str(image_path)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        character_data = self.extract_character_regions(image_path, padding)

        # 文字画像を保存
        for char_info in character_data:
            bbox = char_info["bbox"]
            char_image = image[bbox[1] : bbox[3], bbox[0] : bbox[2]]

            if char_image.size == 0:
                logger.warning(f"Skipping empty char image: {char_info['char_id']}")
                continue

            filename = f"char_{char_info['char_id']:04d}.png"
            save_path = output_path / filename

            success = cv2.imwrite(str(save_path), char_image)
            if not success:
                logger.warning(f"Failed to save image: {save_path}")
                continue

            char_info["image_path"] = str(save_path)

        # メタデータを保存
        metadata = {
            "source_image": image_path,
            "total_characters": len(character_data),
            "characters": character_data,
        }

        metadata_path = output_path / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(character_data)} character images to {output_dir}")
        return metadata

    def visualize_regions(
        self,
        image_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
    ) -> np.ndarray:
        """
        検出された文字領域を可視化

        Args:
            image_path: 入力画像パス
            output_path: 出力画像パス (Noneの場合は保存しない)

        Returns:
            可視化された画像
        """
        image_path = str(image_path)
        image = cv2.imread(image_path)

        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        text_regions = self.detect_text_regions(image_path)

        # 文字領域を描画
        for region in text_regions:
            bbox = region["bbox"]
            points = np.array(bbox, dtype=np.int32)
            cv2.polylines(image, [points], True, (0, 255, 0), 2)

            # テキストと信頼度を表示
            text = f"{region['text']} ({region['confidence']:.2f})"
            cv2.putText(
                image,
                text,
                tuple(points[0]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )

        if output_path:
            output_path = str(output_path)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(output_path, image)
            logger.info(f"Saved visualization to {output_path}")

        return image

    @staticmethod
    def _calculate_center(bbox: List[List[float]]) -> List[float]:
        """バウンディングボックスの中心座標を計算"""
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        return [float(sum(x_coords) / 4), float(sum(y_coords) / 4)]
