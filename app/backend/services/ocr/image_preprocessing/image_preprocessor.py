import os
from typing import Any, Optional, Tuple

import cv2 as _cv2
import numpy as np

cv2: Any = _cv2


class EasyOCRPreprocessor:
    """EasyOCR向けに最適化されたレシート画像の前処理クラス"""

    def __init__(
        self,
        image_path: Optional[str] = None,
        image: Optional[np.ndarray] = None,
        input_dir: str = "app/data/receipt_image",
        output_dir: str = "app/data/processed_receipt_image",
    ):
        """
        Args:
            image_path: 画像ファイルのパス
            image: numpy配列の画像データ（image_pathより優先）
            input_dir: 読み込む画像のディレクトリ
            output_dir: 処理済み画像を保存するディレクトリ
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.image_path = image_path  # 元のファイル名を保持

        if image is not None:
            self.original_image = image
        elif image_path is not None:
            full_image_path = os.path.join(self.input_dir, image_path)
            self.original_image = cv2.imread(full_image_path)
            if self.original_image is None:
                raise ValueError(f"画像を読み込めません: {full_image_path}")
        else:
            raise ValueError("image_pathまたはimageのいずれかを指定してください")

        self.processed_image = self.original_image.copy()

    def resize_if_needed(
        self, target_height: int = 1500, max_height: int = 3000
    ) -> np.ndarray:
        """
        解像度を調整（EasyOCRの最適範囲: 高さ1000-2000px程度）

        Args:
            target_height: 小さい画像をリサイズする目標の高さ
            max_height: 大きすぎる画像を縮小する最大の高さ
        """
        height, width = self.processed_image.shape[:2]

        # 小さすぎる場合はアップスケール
        if height < target_height:
            scale = target_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            self.processed_image = cv2.resize(
                self.processed_image,
                (new_width, new_height),
                interpolation=cv2.INTER_CUBIC,
            )
            print(f"画像をアップスケール: {width}x{height} -> {new_width}x{new_height}")

        # 大きすぎる場合はダウンスケール
        elif height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            self.processed_image = cv2.resize(
                self.processed_image,
                (new_width, new_height),
                interpolation=cv2.INTER_AREA,
            )
            print(f"画像をダウンスケール: {width}x{height} -> {new_width}x{new_height}")

        return self.processed_image

    def grayscale(self) -> np.ndarray:
        """グレースケール化（EasyOCRはカラー画像も扱えるが、処理速度向上のため）"""
        if len(self.processed_image.shape) == 3:
            self.processed_image = cv2.cvtColor(
                self.processed_image, cv2.COLOR_BGR2GRAY
            )
        return self.processed_image

    def enhance_contrast(
        self, clip_limit: float = 2.0, tile_size: int = 8
    ) -> np.ndarray:
        """
        コントラスト強調（CLAHE: Contrast Limited Adaptive Histogram Equalization）

        Args:
            clip_limit: コントラスト制限の閾値（1.0-4.0推奨）
            tile_size: タイルサイズ（8x8推奨）
        """
        # グレースケールでない場合は変換
        if len(self.processed_image.shape) == 3:
            self.grayscale()

        clahe = cv2.createCLAHE(
            clipLimit=clip_limit, tileGridSize=(tile_size, tile_size)
        )
        self.processed_image = clahe.apply(self.processed_image)

        return self.processed_image

    def denoise_light(self, strength: int = 3) -> np.ndarray:
        """
        軽微なノイズ除去（文字を潰さない程度）

        Args:
            strength: ノイズ除去の強度（3-5推奨）
        """
        if len(self.processed_image.shape) == 3:
            # カラー画像の場合
            self.processed_image = cv2.bilateralFilter(
                self.processed_image, strength, strength * 2, strength * 2
            )
        else:
            # グレースケール画像の場合
            self.processed_image = cv2.bilateralFilter(
                self.processed_image, strength, strength * 2, strength * 2
            )

        return self.processed_image

    def correct_skew(
        self, delta: float = 1.0, limit: float = 45.0
    ) -> Tuple[np.ndarray, float]:
        """
        傾き補正

        Args:
            delta: 角度検出の精度（度）
            limit: 検出する最大角度（度）

        Returns:
            補正後の画像と検出された角度のタプル
        """
        # グレースケールでない場合は一時的に変換
        gray = self.processed_image
        if len(gray.shape) == 3:
            gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

        # エッジ検出
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # ハフ変換で直線検出
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

        if lines is None:
            print("傾きを検出できませんでした")
            return self.processed_image, 0.0

        # 角度の抽出と統計
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            # 垂直に近い線のみを考慮
            if abs(angle) < limit:
                angles.append(angle)

        if not angles:
            print("有効な角度が検出されませんでした")
            return self.processed_image, 0.0

        # 中央値を使用して傾きを推定
        angle = float(np.median(angles))

        # 小さい角度は無視（0.5度以下）
        if abs(angle) < 0.5:
            print(f"傾きが小さいため補正をスキップ: {angle:.2f}度")
            return self.processed_image, angle

        # 画像を回転
        (h, w) = self.processed_image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # 回転後の画像サイズを計算
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        # 回転行列を調整
        rotation_matrix[0, 2] += (new_w / 2) - center[0]
        rotation_matrix[1, 2] += (new_h / 2) - center[1]

        # 回転を適用
        self.processed_image = cv2.warpAffine(
            self.processed_image,
            rotation_matrix,
            (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

        return self.processed_image, angle

    def preprocess(self) -> np.ndarray:
        """
        標準的な前処理（レシート画像向け）
        - 解像度調整
        - グレースケール化
        - 軽微なノイズ除去
        - 傾き補正
        - コントラスト強調
        """
        print("=== 画像前処理を実行 ===")
        # 1. 解像度調整
        self.resize_if_needed()

        # 2. グレースケール化
        self.grayscale()

        # 3. 軽微なノイズ除去
        self.denoise_light(strength=3)

        # 4. 傾き補正
        _, angle = self.correct_skew()
        if angle != 0.0:
            print(f"傾きを補正: {angle:.2f}度")

        # 5. コントラスト強調
        self.enhance_contrast(clip_limit=2.0)

        return self.processed_image

    def save(self, output_filename: Optional[str] = None) -> None:
        """
        処理済み画像を保存

        Args:
            output_filename: 保存するファイル名（Noneの場合は元のファイル名を使用）
        """
        if output_filename is None:
            if self.image_path is None:
                raise ValueError(
                    "output_filenameを指定するか、image_pathで初期化してください"
                )
            output_filename = self.image_path

        output_path = os.path.join(self.output_dir, output_filename)
        os.makedirs(self.output_dir, exist_ok=True)
        if not cv2.imwrite(output_path, self.processed_image):
            raise IOError(f"画像を保存できませんでした: {output_path}")
        print(f"保存しました: {output_path}")

    def get_original(self) -> np.ndarray:
        """元の画像を取得"""
        return self.original_image

    def get_processed(self) -> np.ndarray:
        """処理済み画像を取得"""
        return self.processed_image

    def reset(self) -> None:
        """処理をリセットして元の画像に戻す"""
        self.processed_image = self.original_image.copy()


# 使用例
if __name__ == "__main__":
    # 基本的な使い方（元のファイル名で保存）
    preprocessor = EasyOCRPreprocessor("receipt.jpg")
    result = preprocessor.preprocess()
    preprocessor.save()  # receipt.jpg として保存される

    # numpy配列から直接処理（この場合はファイル名を指定する必要がある）
    # image_array = cv2.imread("receipt.jpg")
    # preprocessor2 = EasyOCRPreprocessor(image=image_array)
    # result = preprocessor2.preprocess()
    # preprocessor2.save("processed_receipt.jpg")
