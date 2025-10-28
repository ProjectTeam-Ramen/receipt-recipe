# セットアップガイド

Receipt Recipe プロジェクトの開発環境セットアップ手順です。

## 📋 目次

- [必要なツール](#必要なツール)
- [事前準備（初回のみ）](#事前準備初回のみ)
- [初回セットアップ](#初回セットアップステップバイステップ)
- [開発環境の動作確認](#開発環境の動作確認)
- [トラブルシューティング](#トラブルシューティング初回セットアップ)
- [環境のリセット方法](#環境のリセット方法)

## 必要なツール

- **Git**: バージョン管理
- **VS Code**: 推奨エディタ
- **Docker Desktop**: コンテナ実行環境
- **GitHub アカウント**: ProjectTeam-Ramen組織メンバー

## 事前準備（初回のみ）

### 1. Docker Desktopのインストール

#### Windows/Mac

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/)をダウンロード
2. インストーラーを実行
3. 再起動後、Docker Desktopを起動
4. 設定画面で「Resources」→「WSL Integration」（Windowsの場合）を確認

#### Ubuntu (Linux)

```bash
# Docker Engineのインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# ユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# 再ログイン（またはログアウト→ログイン）
newgrp docker

# Docker Composeのインストール
sudo apt-get update
sudo apt-get install docker-compose-plugin

# インストール確認
docker --version
docker compose version
```

### 2. VS Codeのインストールと拡張機能

#### VS Codeのインストール

1. [VS Code公式サイト](https://code.visualstudio.com/)からダウンロード
2. インストーラーを実行

#### 必須拡張機能のインストール

VS Codeを起動後、以下の拡張機能をインストールしてください。

1. **Dev Containers** (必須)
   - 拡張機能タブ（Ctrl+Shift+X）で「Dev Containers」を検索
   - 「Dev Containers」（Microsoft製）をインストール

2. **Docker** (推奨)
   - 「Docker」（Microsoft製）を検索してインストール

3. **その他の拡張機能**（Dev Container起動後に自動インストールされます）
   - Python
   - Ruff
   - GitHub Pull Requests

#### 拡張機能インストール確認

```
拡張機能タブ（左側のアイコン）で「@installed」と検索して、
Dev ContainersとDockerがインストールされていることを確認
```

### 3. Gitの初期設定

```bash
# ユーザー名とメールアドレスを設定
git config --global user.name "あなたの名前"
git config --global user.email "あなたのメールアドレス"

# 設定確認
git config --global --list
```

## 初回セットアップ（ステップバイステップ）

### Step 1: プロジェクトのクローン

```bash
# ターミナル（またはコマンドプロンプト）を開く
# Windows: PowerShellまたはコマンドプロンプト
# Mac/Linux: ターミナル

# 作業用ディレクトリに移動
cd ~/Documents  # または好きな場所

# プロジェクトをクローン
git clone https://github.com/ProjectTeam-Ramen/receipt-recipe.git

# プロジェクトディレクトリに移動
cd receipt-recipe
```

### Step 2: VS Codeでプロジェクトを開く

```bash
# コマンドラインから開く
code .

# または、VS Codeを起動して
# File → Open Folder → receipt-recipe を選択
```

### Step 3: Dev Containerで開く

#### 方法1: 自動プロンプトから（推奨）

VS Codeがプロジェクトを開いた際、右下に以下のようなポップアップが表示される場合があります:

```
Folder contains a Dev Container configuration file.
Reopen in Container
```

→ 「**Reopen in Container**」をクリック

#### 方法2: コマンドパレットから

1. `Ctrl+Shift+P` (Windows/Linux) または `Cmd+Shift+P` (Mac) を押す
2. 「**Dev Containers: Reopen in Container**」を検索して選択
3. Enterキーを押す

#### 方法3: 左下のアイコンから

1. VS Code左下の青いアイコン（`><`）をクリック
2. 「**Reopen in Container**」を選択

### Step 4: コンテナのビルドと起動（初回は5-10分かかります）

Dev Containerが起動すると、以下の処理が自動的に実行されます:

```
📦 1. Dockerイメージのビルド
   ├─ ベースイメージのダウンロード (nvcr.io/nvidia/pytorch:22.07-py3)
   ├─ システムパッケージのインストール
   ├─ Python依存関係のインストール (uv sync --extra dev)
   └─ PyTorch Geometric CUDA拡張のインストール (CUDA 11.7対応)

🔧 2. VS Code拡張機能のインストール
   ├─ Python拡張機能
   ├─ Ruff拡張機能
   ├─ Docker拡張機能
   └─ その他の開発ツール

⚙️ 3. 環境設定の適用
   ├─ エディタ設定（フォーマット、リンティング）
   ├─ Python interpreter設定
   └─ デバッガー設定

✅ 4. MySQLデータベースの起動
   └─ docker-compose.override.ymlに基づいて起動
```

**重要: CUDA環境について**
- このプロジェクトは計算機サーバーの **CUDA 11.7** 環境に最適化されています
- PyTorch Geometric の拡張パッケージ (torch-scatter, torch-sparse など) は自動的に CUDA 11.7 対応版がインストールされます
- GPU を使用しない場合でも、ビルドは正常に完了します

#### ビルド進行状況の確認

- 右下の「Starting Dev Container (show log)」をクリックするとログが表示されます
- ログで進捗状況を確認できます

#### ビルド完了の確認

- VS Code左下に「**Dev Container: receipt-recipe**」と表示される
- ターミナル（Ctrl+`）を開くと、プロンプトが `appuser@xxxxx:/workspace$` になっている

### Step 5: Git Safe Directoryの設定（初回のみ）

Dev Container内で初めてGitコマンドを実行する際、以下のエラーが出る場合があります:

```bash
fatal: unsafe repository ('/workspace' is owned by someone else)
```

これは、コンテナ内とホストでファイルの所有者が異なるために発生します。

#### 解決方法

ターミナル（Ctrl+`）で以下のコマンドを実行:

```bash
git config --global --add safe.directory /workspace
```

#### 確認

```bash
# 設定が追加されたことを確認
git config --global --list | grep safe.directory
# 出力: safe.directory=/workspace

# Git操作ができることを確認
git status
```

## 開発環境の動作確認

### ターミナルを開く

```bash
# Ctrl+` (バッククォート) でターミナルを開く
# または、View → Terminal
```

### 環境確認コマンド

```bash
# 1. Pythonのバージョン確認
python --version
# 出力例: Python 3.8.13

# 2. uvが使えることを確認
uv --version
# 出力例: uv 0.x.x

# 3. ruffが使えることを確認
uv run ruff --version
# 出力例: ruff 0.0.289

# 4. インストールされているパッケージを確認
uv pip list

# 5. MySQLデータベースへの接続確認
mysql -h db -u user -ppassword receipt_recipe
# 成功すれば mysql> プロンプトが表示される
# 終了: exit
```

### APIサーバーの起動確認

```bash
# アプリケーションを起動
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# ブラウザで以下にアクセス:
# http://localhost:8000
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/health (ヘルスチェック)
```

## トラブルシューティング（初回セットアップ）

### 🔴 Docker Desktopが起動しない

#### Windows

```
エラー: WSL 2 installation is incomplete
解決方法:
1. Windows Update を実行
2. WSL 2をインストール: wsl --install
3. 再起動
4. Docker Desktopを再起動
```

#### Mac

```
エラー: Docker Desktop failed to start
解決方法:
1. Docker Desktopを完全終了
2. 再起動
3. システム設定でDocker Desktopに必要な権限を付与
```

### 🔴 Dev Container extension がインストールできない

```bash
# VS Codeを最新版に更新
# Help → Check for Updates

# 拡張機能を手動でインストール
# 拡張機能タブ (Ctrl+Shift+X) で
# "ms-vscode-remote.remote-containers" を検索してインストール
```

### 🔴 Dev Containerのビルドが失敗する

#### エラー: "permission denied"

```bash
# Dockerグループにユーザーを追加 (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Docker Desktopを再起動 (Windows/Mac)
```

#### エラー: "Failed to download image"

```bash
# インターネット接続を確認
# プロキシ設定が必要な場合は、Docker設定で追加

# Docker Desktopの設定:
# Settings → Resources → Network → Manual proxy configuration
```

#### エラー: "Out of disk space"

```bash
# 不要なDockerリソースを削除
docker system prune -a --volumes

# ビルドキャッシュを削除
docker builder prune -a
```

### 🔴 MySQL接続エラー

#### エラー: "Can't connect to MySQL server"

```bash
# MySQLコンテナの状態確認
docker compose ps

# MySQLコンテナが起動していない場合
docker compose up db -d

# ログ確認
docker compose logs db

# ヘルスチェック確認
docker compose exec db mysqladmin ping -h localhost
```

### 🔴 uv や ruff が見つからない

```bash
# Dev Containerを再ビルド
# コマンドパレット (Ctrl+Shift+P) → "Dev Containers: Rebuild Container"

# または、依存関係を手動でインストール
uv sync --extra dev --frozen
```

## 環境のリセット方法

開発環境を完全にリセットしたい場合:

```bash
# VS CodeでDev Containerを閉じる
# コマンドパレット → "Dev Containers: Reopen Folder Locally"

# ターミナルで以下を実行
docker compose down --volumes --remove-orphans
docker system prune -a --volumes

# プロジェクトディレクトリで再度VS Codeを開く
code .

# Dev Containerで再度開く
# コマンドパレット → "Dev Containers: Reopen in Container"
```

## 次のステップ

セットアップが完了したら、[CONTRIBUTING.md](../CONTRIBUTING.md) を読んで開発フローを確認してください。

## 参考リンク

- [環境構築詳細ドキュメント](./environment.md)
- [Docker Documentation](https://docs.docker.com/)
- [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
- [uv Documentation](https://docs.astral.sh/uv/)

---

**最終更新日**: 2025年10月16日