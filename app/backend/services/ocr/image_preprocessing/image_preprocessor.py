import os
from typing import Any, Optional, Tuple

import cv2 as _cv2
import numpy as np

cv2: Any = _cv2


class ReceiptPreprocessor:
    """レシート画像の前処理を行うクラス"""

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

        if image is not None:
            self.original_image = image
        elif image_path is not None:
            full_image_path = os.path.join(self.input_dir, image_path)
            self.original_image = cv2.imread(full_image_path)
            if self.original_image is None:
                raise ValueError("元の画像が初期化されていません")
        else:
            raise ValueError("image_pathまたはimageのいずれかを指定してください")

        self.processed_image = self.original_image.copy()

    def grayscale(self) -> np.ndarray:
        """グレースケール化"""
        if len(self.processed_image.shape) == 3:
            self.processed_image = cv2.cvtColor(
                self.processed_image, cv2.COLOR_BGR2GRAY
            )
        return self.processed_image

    def binarize(
        self, method: str = "adaptive", block_size: int = 15, c: int = 10
    ) -> np.ndarray:
        """
        二値化処理

        Args:
            method: 'adaptive' (適応的閾値処理) or 'otsu' (大津の二値化)
            block_size: 適応的閾値処理のブロックサイズ（奇数）
            c: 適応的閾値処理の定数
        """
        # グレースケールでない場合は変換
        if len(self.processed_image.shape) == 3:
            self.grayscale()

        if method == "adaptive":
            if block_size % 2 == 0:
                raise ValueError("block_sizeは奇数である必要があります")
            self.processed_image = cv2.adaptiveThreshold(
                self.processed_image,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block_size,
                c,
            )
        elif method == "otsu":
            _, self.processed_image = cv2.threshold(
                self.processed_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        else:
            raise ValueError("methodは'adaptive'または'otsu'を指定してください")

        return self.processed_image

    def denoise(self, method: str = "bilateral", strength: int = 9) -> np.ndarray:
        """
        ノイズ除去

        Args:
            method: 'bilateral' (バイラテラルフィルタ), 'gaussian' (ガウシアンフィルタ),
                   'median' (メディアンフィルタ), 'morphology' (モルフォロジー変換)
            strength: フィルタの強度（カーネルサイズ）
        """
        if method == "bilateral":
            # エッジを保持しながらノイズ除去（カラー画像対応）
            if len(self.processed_image.shape) == 3:
                self.processed_image = cv2.bilateralFilter(
                    self.processed_image, strength, 75, 75
                )
            else:
                # グレースケールの場合は一時的にカラーに変換
                temp = cv2.cvtColor(self.processed_image, cv2.COLOR_GRAY2BGR)
                temp = cv2.bilateralFilter(temp, strength, 75, 75)
                self.processed_image = cv2.cvtColor(temp, cv2.COLOR_BGR2GRAY)

        elif method == "gaussian":
            # ガウシアンぼかし
            self.processed_image = cv2.GaussianBlur(
                self.processed_image, (strength, strength), 0
            )

        elif method == "median":
            # メディアンフィルタ
            self.processed_image = cv2.medianBlur(self.processed_image, strength)

        elif method == "morphology":
            # モルフォロジー変換（二値化画像用）
            kernel = np.ones((3, 3), np.uint8)
            # オープニング: ノイズ除去
            self.processed_image = cv2.morphologyEx(
                self.processed_image, cv2.MORPH_OPEN, kernel, iterations=1
            )
            # クロージング: 小さな穴を埋める
            self.processed_image = cv2.morphologyEx(
                self.processed_image, cv2.MORPH_CLOSE, kernel, iterations=1
            )

        else:
            raise ValueError(
                "methodは'bilateral', 'gaussian', 'median', 'morphology'のいずれかを指定してください"
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
        # グレースケールでない場合は変換
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

    def preprocess(
        self,
        denoise_method: str = "bilateral",
        binarize_method: str = "adaptive",
        correct_skew: bool = True,
    ) -> np.ndarray:
        """
        全ての前処理を順次実行

        Args:
            denoise_method: ノイズ除去の方法
            binarize_method: 二値化の方法
            correct_skew: 傾き補正を行うかどうか

        Returns:
            前処理済みの画像
        """
        # 1. グレースケール化
        self.grayscale()

        # 2. ノイズ除去（二値化前）
        self.denoise(method=denoise_method, strength=5)

        # 3. 傾き補正（二値化前に行う方が精度が高い）
        if correct_skew:
            _, angle = self.correct_skew()
            import logging

            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)
            logger.info(f"検出された傾き: {angle:.2f}度")

        # 4. 二値化
        self.binarize(method=binarize_method)

        # 5. ノイズ除去（二値化後、モルフォロジー変換）
        self.denoise(method="morphology")

        return self.processed_image

    def save(self, output_filename: str) -> None:
        """処理済み画像を保存"""
        output_path = os.path.join(self.output_dir, output_filename)
        os.makedirs(
            self.output_dir, exist_ok=True
        )  # ディレクトリが存在しない場合は作成
        if not cv2.imwrite(output_path, self.processed_image):
            raise IOError(f"画像を保存できませんでした: {output_path}")

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
    # 方法1: 簡単な使い方（全処理を一括実行）
    preprocessor = ReceiptPreprocessor("receipt.jpg")
    result = preprocessor.preprocess()
    preprocessor.save("receipt_processed.jpg")

    # 方法2: 各処理を個別に実行
    preprocessor2 = ReceiptPreprocessor("receipt.jpg")
    preprocessor2.grayscale()
    preprocessor2.denoise(method="bilateral", strength=9)
    _, angle = preprocessor2.correct_skew()
    print(f"傾き: {angle:.2f}度")
    preprocessor2.binarize(method="adaptive")
    preprocessor2.denoise(method="morphology")
    preprocessor2.save("receipt_custom.jpg")

    # 方法3: numpy配列から直接処理
    # image_array = np.array(...)  # 何らかの方法で取得した画像配列
    # preprocessor3 = ReceiptPreprocessor(image=image_array)
    # result = preprocessor3.preprocess()
