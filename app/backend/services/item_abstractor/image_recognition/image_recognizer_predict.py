import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

# --- 1. 設定 ---
# ステップ2で学習・保存したモデルのパス
model_path = 'my_food_model.pth'
# 予測したい画像
image_path = 'test_rice.jpg' 

# ★重要：学習時と全く同じクラス名を、同じ順番で定義する
# （ステップ1のフォルダ構成 '00_egg', '01_rice', '02_flour' に対応）
class_names = ['00_egg', '01_rice', '02_flour'] 
num_classes = len(class_names)

# --- 2. モデルのロード ---
# まず、学習時と同じモデルの「構造」を定義する
model = models.resnet18(weights=None) # 重みはロードするので None
num_ftrs = model.fc.in_features
model.fc = nn.Linear(num_ftrs, num_classes) # 最終層を学習時と同じクラス数に差し替える

# 学習済みの「重み」をロードする
model.load_state_dict(torch.load(model_path))
model.eval() # 評価モードに設定

# --- 3. 画像の前処理 ---
# 学習時の 'val'（検証用）と同じ前処理を行う
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# --- 4. 予測の実行 ---
try:
    img = Image.open(image_path).convert('RGB')
    input_tensor = preprocess(img)
    input_batch = input_tensor.unsqueeze(0) # バッチ次元 [1, 3, 224, 224] を追加

    with torch.no_grad():
        output = model(input_batch)

    # 確率に変換
    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    
    # 最も確率の高いクラスを取得
    top_prob, top_catid = torch.max(probabilities, 0)
    predicted_label = class_names[top_catid]

    print(f"画像: {image_path}")
    print(f"予測された食材名: {predicted_label}")
    print(f"確信度: {top_prob.item() * 100:.2f}%")

except FileNotFoundError:
    print(f"エラー: 画像ファイル '{image_path}' が見つかりません。")
except Exception as e:
    print(f"エラーが発生しました: {e}")