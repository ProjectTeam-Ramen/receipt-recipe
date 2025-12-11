import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

# --- 1. 設定 ---
model_path = "/workspace/app/backend/services/item_abstractor/image_recognition/my_food_model.pth"
image_path = "/workspace/app/backend/services/item_abstractor/image_recognition/tomato.jpeg"  # ここに予測したい画像ファイル#
data_dir = "./dataset/train"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
"""
if os.path.exists(data_dir):
    class_names = sorted([d.name for d in os.scandir(data_dir) if d.is_dir()])
    num_classes = len(class_names)
else:
    num_classes = 77
    class_names = [str(i) for i in range(num_classes)]
"""
num_classes = 77
class_names = [str(i) for i in range(num_classes)]


# --- 2. モデルのロード ---
model = models.resnet18(weights=None)
num_ftrs = model.fc.in_features
model.fc = nn.Linear(num_ftrs, num_classes)
model.load_state_dict(torch.load(model_path, map_location=device))
model.to(device)
model.eval()

# --- 3. 画像の前処理 ---
preprocess = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)

# --- 4. 予測の実行 ---
try:
    img = Image.open(image_path).convert("RGB")
    input_tensor = preprocess(img)
    input_batch = input_tensor.unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(input_batch)

    # 確率計算
    probabilities = torch.nn.functional.softmax(output[0], dim=0)

    # ★全77食材のデータを辞書として内部保存する（ここが重要）
    # 例: {'00_ジャガイモ': 0.001, ... '03_牛肉': 0.836, ...}
    all_results_dict = {}
    for i in range(len(class_names)):
        all_results_dict[class_names[i]] = probabilities[i].item()
    # ★画面表示（print）は行いません。
    # この時点で all_results_dict にすべてのデータが入っています。
    # 後続の処理でこの変数を利用してください。

except FileNotFoundError:
    print(f"エラー: 画像ファイル '{image_path}' が見つかりません。")
except Exception as e:
    print(f"エラーが発生しました: {e}")
    all_results_dict = {}

# 結果を出力
print("予測結果:")
for class_name, probability in sorted(
    all_results_dict.items(), key=lambda x: x[1], reverse=True
):
    print(f"{class_name}: {probability:.4f}")
