# 開発環境構築ドキュメント

## 目次

1. [概要](#概要)
2. [システム要件](#システム要件)
3. [ベースイメージ](#ベースイメージ)
4. [システムライブラリ](#システムライブラリ)
5. [Pythonパッケージ](#pythonパッケージ)
6. [Docker構成](#docker構成)
7. [環境変数](#環境変数)
8. [セットアップ手順](#セットアップ手順)
9. [トラブルシューティング](#トラブルシューティング)

---

## 概要

このプロジェクトは、レシート画像から料理レシピを生成するAIアプリケーションです。
開発環境はDockerコンテナベースで構築されており、GPU対応のPyTorchを含む深層学習環境を提供します。

### 主要機能
- OCR（光学文字認識）によるレシート解析
- 深層学習を用いた画像処理
- 自然言語処理（形態素解析）
- Webスクレイピング
- RESTful API（FastAPI）
- MySQL データベース連携

---

## システム要件

### ホストマシン
- **OS**: Ubuntu 20.04.4 LTS 以降
- **GPU**: NVIDIA GPU（CUDA 11.7 対応）
- **GPU Driver**: NVIDIA Driver 515.x 以降
- **Docker**: 20.10 以降
- **Docker Compose**: 2.0 以降
- **NVIDIA Container Toolkit**: インストール済み

### リソース要件
- **CPU**: 4コア以上推奨
- **RAM**: 16GB以上推奨
- **GPU VRAM**: 8GB以上推奨
- **ディスク**: 50GB以上の空き容量

---

## ベースイメージ

### 使用イメージ
```dockerfile
nvcr.io/nvidia/pytorch:22.07-py3
```

### イメージ詳細
- **PyTorch**: 1.12.0
- **torchvision**: 0.13.0
- **CUDA**: 11.7
- **cuDNN**: 8.5.0
- **Python**: 3.8.13
- **Ubuntu**: 20.04

### 選定理由
計算機サーバーのCUDA 11.7ドライバとの互換性を確保するため、このイメージを選定しました。

---

## システムライブラリ

### 基本ツール
```bash
git               # バージョン管理
curl              # HTTPクライアント
wget              # ファイルダウンロード
gnupg             # 暗号化ツール
```

### ビルドツール
```bash
build-essential   # C/C++コンパイラ等
libssl-dev        # OpenSSL開発ライブラリ
libffi-dev        # Foreign Function Interface
pkg-config        # コンパイル設定管理
```

### OpenCV関連
```bash
libgl1-mesa-glx   # OpenGL実装
libglib2.0-0      # GLibライブラリ
libsm6            # X11 Session Management
libxext6          # X11拡張ライブラリ
libxrender-dev    # X Renderingライブラリ
libgomp1          # OpenMP実装
```

### OCR（光学文字認識）
```bash
tesseract-ocr     # OCRエンジン本体
tesseract-ocr-jpn # 日本語言語データ
poppler-utils     # PDFユーティリティ
```

### 形態素解析
```bash
mecab             # 形態素解析エンジン
libmecab-dev      # MeCab開発ライブラリ
mecab-ipadic-utf8 # IPA辞書（UTF-8）
```

### Webスクレイピング
```bash
chromium-browser      # Chromiumブラウザ
chromium-chromedriver # WebDriverインターフェース
```

### データベース
```bash
default-libmysqlclient-dev # MySQL C APIライブラリ
default-mysql-client       # MySQLクライアント
```

### ロケール・タイムゾーン
```bash
locales           # ロケール設定
TZ=Asia/Tokyo     # 日本時間
LANG=ja_JP.UTF-8  # 日本語UTF-8
```

---

## Pythonパッケージ

### OCR・画像処理
```toml
pytesseract>=0.3.10   # Tesseract Pythonラッパー
opencv-python>=4.8.0  # OpenCV Pythonバインディング
Pillow>=10.0.0        # 画像処理ライブラリ
numpy>=1.24.0         # 数値計算
pdf2image>=1.16.0     # PDF→画像変換
```

### 深層学習・AI
```toml
# torch>=2.0.0 (ベースイメージに含まれるため除外)
# torchvision>=0.15.0 (同上)
transformers>=4.30.0      # HuggingFace Transformers
torch-geometric>=2.3.0    # グラフニューラルネットワーク
scikit-learn>=1.3.0       # 機械学習ライブラリ
pandas>=2.0.0             # データ分析
scipy>=1.10.0             # 科学技術計算
```

**PyTorch Geometric の CUDA 対応について:**
- `torch-geometric` 本体は `pyproject.toml` に記載されていますが、
- CUDA 依存の拡張パッケージ (`torch-scatter`, `torch-sparse`, `torch-cluster`, `torch-spline-conv`) は、
- 計算機サーバーの CUDA 11.7 環境との互換性を確保するため、
- Dockerfile 内で PyTorch 1.12.0 + CUDA 11.7 用のプリビルドホイールから明示的に再インストールされます。
- データソース: https://data.pyg.org/whl/torch-1.12.0+cu117.html

### データベース
```toml
pymysql>=1.1.0       # MySQL Pythonドライバ
sqlalchemy>=2.0.0    # SQLツールキット/ORM
alembic>=1.11.0      # データベースマイグレーション
```

### 自然言語処理・スクレイピング
```toml
mecab-python3>=1.0.6      # MeCab Pythonバインディング
unidic-lite>=1.0.8        # UniDic軽量版
beautifulsoup4>=4.12.0    # HTMLパーサー
lxml>=4.9.0               # XMLパーサー
selenium>=4.10.0          # ブラウザ自動化
webdriver-manager>=3.8.0  # WebDriver管理
requests>=2.31.0          # HTTPライブラリ
```

### API・Web
```toml
fastapi>=0.100.0                      # Webフレームワーク
uvicorn[standard]>=0.23.0             # ASGIサーバー
pydantic>=2.0.0                       # データバリデーション
pydantic-settings>=2.0.0              # 設定管理
python-multipart>=0.0.6               # マルチパート解析
python-jose[cryptography]>=3.3.0      # JWT処理
passlib[bcrypt]>=1.7.4                # パスワードハッシュ
httpx>=0.24.0                         # 非同期HTTPクライアント
```

### 非同期処理・タスク管理
```toml
celery>=5.3.0  # 分散タスクキュー
redis>=4.6.0   # インメモリデータストア
```

### その他ユーティリティ
```toml
python-dotenv>=1.0.0      # 環境変数管理
click>=8.1.0              # CLIツール
python-dateutil>=2.8.0    # 日付処理
```

### 開発ツール（dev依存）
```toml
pytest>=7.4.0           # テストフレームワーク
pytest-asyncio>=0.21.0  # 非同期テスト
pytest-cov>=4.1.0       # カバレッジ測定
black>=23.7.0           # コードフォーマッター
flake8>=6.1.0           # リンター
mypy>=1.5.0             # 型チェッカー
isort>=5.12.0           # import整理
ruff>=0.0.289           # 高速リンター
```

---

## Docker構成

### マルチステージビルド

#### Stage 1: builder
```dockerfile
FROM nvcr.io/nvidia/pytorch:22.07-py3 AS builder
```
- uvのインストール
- 仮想環境の作成
- 依存関係の同期（キャッシュマウント活用）
- **PyTorch Geometric と CUDA 11.7 対応拡張パッケージのインストール**
  - torch-scatter, torch-sparse, torch-cluster, torch-spline-conv を
  - PyTorch 1.12.0 + CUDA 11.7 用のプリビルドホイールからインストール
  - データソース: https://data.pyg.org/whl/torch-1.12.0+cu117.html

#### Stage 2: final
```dockerfile
FROM nvcr.io/nvidia/pytorch:22.07-py3
```
- システムライブラリのインストール
- アプリケーションコードのコピー
- 依存関係のインストール
- 非ルートユーザー(appuser)の作成

### docker-compose構成

#### 開発環境（docker-compose.override.yml）
```yaml
services:
  api:
    # アプリケーションコンテナ
    - ボリュームマウント: .:/workspace
    - 開発用依存関係インストール
    - 起動コマンド: tail -f /dev/null
  
  db:
    # MySQLコンテナ
    - イメージ: mysql:8.0
    - ポート公開: 3306
    - ヘルスチェック有効
```

#### GPU環境（docker-compose.gpu.yml）
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

#### 本番環境（docker-compose.prod.yml）
```yaml
services:
  api:
    - 本番用起動コマンド: uvicorn
    - ヘルスチェック: /health エンドポイント
    - 再起動ポリシー: unless-stopped
  
  db:
    - 永続化ボリューム: mysql_data
```

---

## 環境変数

### 必須環境変数

```bash
# データベース接続
DATABASE_URL=mysql+pymysql://user:password@db:3306/receipt_recipe

# Python設定
PYTHONPATH=/workspace
PYTHONUNBUFFERED=1

# GPU設定
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

### オプション環境変数

```bash
# ログレベル（本番環境）
LOG_LEVEL=info

# MySQL設定
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=receipt_recipe
MYSQL_USER=user
MYSQL_PASSWORD=password
```

### ロケール・タイムゾーン

```bash
TZ=Asia/Tokyo
LANG=ja_JP.UTF-8
LANGUAGE=ja_JP:ja
LC_ALL=ja_JP.UTF-8
```

---

## セットアップ手順

### 1. 前提条件の確認

```bash
# NVIDIA Driverのバージョン確認
nvidia-smi

# Docker & Docker Composeのバージョン確認
docker --version
docker compose version

# NVIDIA Container Toolkitの確認
docker run --rm --gpus all nvidia/cuda:11.7.0-base-ubuntu20.04 nvidia-smi
```

### 2. プロジェクトのクローン

```bash
git clone <repository-url>
cd receipt-recipe
```

### 3. 環境変数ファイルの作成

```bash
# .envファイルを作成
cat > .env << 'EOF'
DATABASE_URL=mysql+pymysql://user:password@db:3306/receipt_recipe
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=receipt_recipe
MYSQL_USER=user
MYSQL_PASSWORD=password
EOF
```

### 4. uvによる依存関係ロックファイルの生成

```bash
# uvがインストールされていない場合
curl -LsSf https://astral.sh/uv/install.sh | sh

# ロックファイルの生成
uv lock
```

### 5. 開発環境の起動（CPU環境）

```bash
# コンテナのビルドと起動
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build

# ログ確認
docker compose logs -f
```

### 6. 開発環境の起動（GPU環境）

```bash
# GPU対応でビルドと起動
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.gpu.yml up -d --build

# GPU認識確認
docker compose exec api nvidia-smi
```

### 7. VS Code Dev Containerでの起動

```bash
# VS Codeで開く
code .

# Command Palette (Ctrl+Shift+P) から
# "Dev Containers: Reopen in Container" を実行
```

### 8. データベースの初期化

```bash
# コンテナ内で実行
docker compose exec api bash

# データベース接続確認
mysql -h db -u user -ppassword receipt_recipe

# Alembicマイグレーション（初期化）
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 9. アプリケーションの起動

```bash
# 開発サーバーの起動
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# ブラウザで確認
# http://localhost:8000
# http://localhost:8000/docs (Swagger UI)
```

---

## トラブルシューティング

### 1. GPUが認識されない

**症状**: `nvidia-smi`が失敗する

**解決方法**:
```bash
# NVIDIA Container Toolkitの再インストール
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 2. MySQLに接続できない

**症状**: `Can't connect to MySQL server`

**解決方法**:
```bash
# MySQLコンテナの状態確認
docker compose ps db

# ヘルスチェック確認
docker compose exec db mysqladmin ping -h localhost

# ログ確認
docker compose logs db

# 接続テスト
docker compose exec api mysql -h db -u user -ppassword receipt_recipe
```

### 3. 依存関係のインストールエラー

**症状**: `uv sync`が失敗する

**解決方法**:
```bash
# キャッシュをクリア
rm -rf ~/.cache/uv

# ロックファイルを再生成
rm uv.lock
uv lock

# コンテナを再ビルド
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 4. ポート競合

**症状**: `port is already allocated`

**解決方法**:
```bash
# 使用中のポートを確認
sudo lsof -i :8000
sudo lsof -i :3306

# docker-compose.override.ymlのポート変更
# ports:
#   - "8001:8000"  # ホスト側を変更
#   - "3307:3306"
```

### 5. ディスク容量不足

**症状**: `no space left on device`

**解決方法**:
```bash
# 未使用のDockerリソースを削除
docker system prune -a --volumes

# ビルドキャッシュを削除
docker builder prune -a

# 容量確認
df -h
docker system df
```

### 6. メモリ不足

**症状**: コンテナがOOM Killedされる

**解決方法**:
```yaml
# docker-compose.override.ymlに追加
services:
  api:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
```

### 7. Chromeドライバーエラー

**症状**: `selenium.common.exceptions.WebDriverException`

**解決方法**:
```bash
# コンテナ内でChromiumのバージョン確認
chromium-browser --version

# webdriver-managerで自動ダウンロード
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
```

### 8. MeCabの辞書エラー

**症状**: `No such file or directory: /usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ipadic-neologd`

**解決方法**:
```bash
# 辞書パスの確認
mecab -D

# unidic-liteを使用（推奨）
import unidic_lite
import MeCab
tagger = MeCab.Tagger(unidic_lite.DICDIR)
```

---

## 本番環境デプロイ

### 1. イメージのビルド

```bash
# 本番用イメージのビルド
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
```

### 2. 環境変数の設定

```bash
# 本番用.envファイル
cat > .env.prod << 'EOF'
DATABASE_URL=mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@db:3306/${MYSQL_DATABASE}
MYSQL_ROOT_PASSWORD=<STRONG_PASSWORD>
MYSQL_DATABASE=receipt_recipe
MYSQL_USER=<DB_USER>
MYSQL_PASSWORD=<STRONG_DB_PASSWORD>
LOG_LEVEL=warning
EOF
```

### 3. デプロイ

```bash
# GPU環境でデプロイ
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gpu.yml up -d

# ヘルスチェック
curl http://localhost:8000/health
```

### 4. 監視・ログ

```bash
# ログ監視
docker compose -f docker-compose.prod.yml logs -f

# リソース監視
docker stats

# GPU監視
watch -n 1 nvidia-smi
```

---

## 参考リンク

- [NVIDIA PyTorch Container](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch)
- [uv Documentation](https://docs.astral.sh/uv/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

---

**最終更新日**: 2025年10月16日  
**バージョン**: 1.0.0