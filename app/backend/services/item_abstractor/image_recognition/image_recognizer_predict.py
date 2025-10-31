import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

# 学習・保存したモデルのパス
model_path = 'my_food_model.pth'
# 予測したい画像
image_path = 'test_rice.jpg' 

class_names = ['00_egg', '01_rice', '02_flour'] 
num_classes = len(class_names)

model = models.resnet18(weights=None)
num_ftrs = model.fc.in_features
model.fc = nn.Linear(num_ftrs, num_classes)

model.load_state_dict(torch.load(model_path))
model.eval()

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

try:
    img = Image.open(image_path).convert('RGB')
    input_tensor = preprocess(img)
    input_batch = input_tensor.unsqueeze(0)

    with torch.no_grad():
        output = model(input_batch)

    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    
    top_prob, top_catid = torch.max(probabilities, 0)
    predicted_label = class_names[top_catid]

    print(f"画像: {image_path}")
    print(f"予測された食材名: {predicted_label}")
    print(f"確信度: {top_prob.item() * 100:.2f}%")

except FileNotFoundError:
    print(f"エラー: 画像ファイル '{image_path}' が見つかりません。")
except Exception as e:
    print(f"エラーが発生しました: {e}")