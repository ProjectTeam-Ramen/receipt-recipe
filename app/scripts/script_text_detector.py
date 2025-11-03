import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

# text_detector.pyへのパスを追加
text_detector_path = (
    Path(__file__).parent.parent / "backend" / "services" / "ocr" / "text_detection"
)
sys.path.insert(0, str(text_detector_path))

if not text_detector_path.exists():
    raise ImportError(f"Text detector module path does not exist: {text_detector_path}")

from text_detector import ReceiptOCRProcessor  # type: ignore  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def process_receipt_images(
    input_dir: str = "/workspace/app/data/processed_receipt_image",
    output_dir: str = "/workspace/app/data/detected_texts",
    image_extensions: Optional[List[str]] = None,
    line_threshold: int = 20,
) -> None:
    """
    レシート画像を処理してテキスト検出結果を保存

    Args:
        input_dir: 入力画像ディレクトリ
        output_dir: 出力ディレクトリ
        image_extensions: 処理する画像ファイルの拡張子リスト
        line_threshold: 行を分けるY座標の閾値（ピクセル）
    """
    if image_extensions is None:
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return

    # 出力ディレクトリを作成
    output_path.mkdir(parents=True, exist_ok=True)

    # 画像ファイルを取得
    image_files = []
    for ext in image_extensions:
        image_files.extend(input_path.glob(f"*{ext}"))
        image_files.extend(input_path.glob(f"*{ext.upper()}"))

    if not image_files:
        logger.warning(f"No image files found in {input_dir}")
        return

    logger.info(f"Found {len(image_files)} image(s) to process")

    # OCRプロセッサを初期化
    processor = ReceiptOCRProcessor(languages=["ja", "en"], gpu=False)

    # 各画像を処理
    for image_file in image_files:
        try:
            logger.info(f"Processing: {image_file.name}")

            # 画像ごとの出力ディレクトリ構造
            image_base_dir = output_path / image_file.stem
            characters_dir = image_base_dir / "characters"

            # ベースディレクトリを作成
            image_base_dir.mkdir(parents=True, exist_ok=True)

            # テキスト検出と文字画像の保存（charactersディレクトリ内）
            metadata = processor.save_character_images(
                image_path=image_file, output_dir=characters_dir, padding=2
            )

            # metadata.jsonをcharactersと同列に移動
            old_metadata_path = characters_dir / "metadata.json"
            new_metadata_path = image_base_dir / "metadata.json"

            if old_metadata_path.exists():
                # メタデータを読み込み
                with open(old_metadata_path, "r", encoding="utf-8") as f:
                    metadata_content = json.load(f)

                # 新しい場所に保存
                with open(new_metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata_content, f, ensure_ascii=False, indent=2)

                # 古いファイルを削除
                old_metadata_path.unlink()

                # 文字をY座標でソートして行ごとに分ける
                characters = metadata_content.get("characters", [])

                # centerフィールドを使用してソート
                sorted_chars = sorted(
                    characters,
                    key=lambda x: (
                        x["center"][1],  # Y座標
                        x["center"][0],  # X座標
                    ),
                )

                # 行ごとにグループ化
                lines = []
                current_line = []
                prev_y = None

                for char_info in sorted_chars:
                    char_text = char_info.get("char", "")
                    char_y = char_info["center"][1]

                    if prev_y is None:
                        current_line.append(char_text)
                        prev_y = char_y
                    else:
                        y_diff = abs(char_y - prev_y)

                        if y_diff <= line_threshold:
                            current_line.append(char_text)
                        else:
                            if current_line:
                                lines.append("".join(current_line))
                            current_line = [char_text]
                            prev_y = char_y

                # 最後の行を追加
                if current_line:
                    lines.append("".join(current_line))

                # 改行で結合してテキストファイルに保存
                combined_text = "\n".join(lines)
                text_output_path = image_base_dir / "detected_text.txt"
                with open(text_output_path, "w", encoding="utf-8") as f:
                    f.write(combined_text)

                logger.info(f"Detected {len(lines)} lines")

            # 可視化画像を保存
            vis_output_path = image_base_dir / "visualization.png"
            processor.visualize_regions(
                image_path=image_file, output_path=vis_output_path
            )

            logger.info(
                f"Completed: {image_file.name} - "
                f"{metadata['total_characters']} characters detected"
            )

        except Exception as e:
            logger.error(f"Failed to process {image_file.name}: {e}", exc_info=True)
            continue

    logger.info(f"Processing complete. Results saved to {output_dir}")


if __name__ == "__main__":
    process_receipt_images()
