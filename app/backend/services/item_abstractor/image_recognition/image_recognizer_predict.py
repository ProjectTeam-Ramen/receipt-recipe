from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Sequence, Tuple, cast

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from torch import Tensor

MODEL_PATH = Path(
    "/workspace/app/backend/services/item_abstractor/image_recognition/my_food_model.pth"
)
DATASET_DIR = Path("./dataset/train")
DEFAULT_NUM_CLASSES = 77

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_model: torch.nn.Module | None = None


def _load_class_names() -> List[str]:
    if DATASET_DIR.exists():
        return sorted([entry.name for entry in DATASET_DIR.iterdir() if entry.is_dir()])
    return [str(i) for i in range(DEFAULT_NUM_CLASSES)]


CLASS_NAMES: List[str] = _load_class_names()
NUM_CLASSES = len(CLASS_NAMES)

_preprocess = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)


def _load_model() -> torch.nn.Module:
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"モデルファイルが見つかりません: {MODEL_PATH}")
        model = models.resnet18(weights=None)
        num_ftrs = model.fc.in_features
        model.fc = nn.Linear(num_ftrs, NUM_CLASSES)
        state = torch.load(MODEL_PATH, map_location=_device)
        model.load_state_dict(state)
        model.to(_device)
        model.eval()
        _model = model
    return _model


def predict_image(image_path: str | Path) -> Dict[str, float]:
    """画像1枚を推論し、クラス名→確率の辞書を返す"""

    model = _load_model()
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"画像ファイルが見つかりません: {path}")

    img = Image.open(path).convert("RGB")
    input_tensor = cast(Tensor, _preprocess(img))
    input_batch = input_tensor.unsqueeze(0).to(_device)

    with torch.no_grad():
        output = model(input_batch)

    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    return {CLASS_NAMES[i]: probabilities[i].item() for i in range(NUM_CLASSES)}


def get_top_predictions(
    probabilities: Dict[str, float], top_k: int = 5
) -> List[Tuple[str, float]]:
    """確率辞書から上位top_kの結果を返す"""

    sorted_items = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    return sorted_items[: top_k if top_k > 0 else len(sorted_items)]


def _print_summary(results: Sequence[Tuple[str, float]]) -> None:
    for label, score in results:
        print(f"{label}: {score:.4f}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Food image recognizer")
    parser.add_argument("image", help="推論したい画像ファイルへのパス")
    parser.add_argument("--top", type=int, default=5, help="表示する上位件数")
    args = parser.parse_args(argv)

    probabilities = predict_image(args.image)
    top_items = get_top_predictions(probabilities, args.top)
    print("予測結果 (top {}):".format(len(top_items)))
    _print_summary(top_items)


if __name__ == "__main__":
    main()
