import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
import torchvision.models as models
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
import os
import time

# --- 1. 基本設定 ---
# データセットのパス（ステップ1で作成したフォルダの親フォルダ）
data_dir = "./dataset"
# 保存するモデルのファイル名
model_save_path = "my_food_model.pth"

# 学習のパラメータ
batch_size = 16
num_epochs = 10  # エポック数（データセットを何周学習するか）
learning_rate = 0.001

# --- 2. データの準備（前処理と読み込み） ---

# 画像の前処理
data_transforms = {
    "train": transforms.Compose(
        [
            transforms.RandomResizedCrop(224),  # 学習時はランダムにクロップ
            transforms.RandomHorizontalFlip(),  # ランダムに左右反転
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    ),
    "val": transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),  # 検証時は中央をクロップ
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    ),
}

# ImageFolderを使ってデータセットを読み込み
image_datasets = {
    x: ImageFolder(os.path.join(data_dir, x), data_transforms[x])
    for x in ["train", "val"]
}
# DataLoaderを作成
dataloaders = {
    x: DataLoader(image_datasets[x], batch_size=batch_size, shuffle=True, num_workers=0)
    for x in ["train", "val"]
}

dataset_sizes = {x: len(image_datasets[x]) for x in ["train", "val"]}
# ★重要：クラス名（フォルダ名）を取得
class_names = image_datasets["train"].classes
num_classes = len(class_names)

print(f"学習を開始します。対象クラス: {', '.join(class_names)}")

# デバイスの指定 (GPUが利用可能ならGPUを使う)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# --- 3. モデルの定義（転移学習） ---
# ResNet-18をベースモデルとして使用
model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)

# ★重要：ResNetの最後の全結合層を、今回のクラス数（num_classes）に差し替える
num_ftrs = model.fc.in_features
model.fc = nn.Linear(num_ftrs, num_classes)

model = model.to(device)  # モデルをGPUへ送る

# --- 4. 損失関数と最適化手法の定義 ---
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=learning_rate, momentum=0.9)

# --- 5. 学習ループ ---
start_time = time.time()

for epoch in range(num_epochs):
    print(f"Epoch {epoch + 1}/{num_epochs}")
    print("-" * 10)

    for phase in ["train", "val"]:
        if phase == "train":
            model.train()  # 学習モード
        else:
            model.eval()  # 評価モード

        running_loss = 0.0
        running_corrects = 0

        # データローダーからバッチサイズ分データを取り出す
        for inputs, labels in dataloaders[phase]:
            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()  # 勾配をリセット

            # 学習時のみ勾配計算を有効にする
            with torch.set_grad_enabled(phase == "train"):
                outputs = model(inputs)
                _, preds = torch.max(outputs, 1)  # 最も確率の高いクラスを予測
                loss = criterion(outputs, labels)

                # 学習時のみバックプロパゲーション（誤差逆伝播）
                if phase == "train":
                    loss.backward()
                    optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)

        epoch_loss = running_loss / dataset_sizes[phase]
        epoch_acc = running_corrects.double() / dataset_sizes[phase]

        print(f"{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}")

# --- 6. モデルの保存 ---
torch.save(model.state_dict(), model_save_path)
print(f"\n学習が完了しました。モデルを {model_save_path} に保存しました。")
print(f"学習時間: {(time.time() - start_time) / 60:.2f} 分")
