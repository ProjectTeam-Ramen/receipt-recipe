# 開発ガイドブック

Receipt Recipe プロジェクトのチーム開発ガイドです。

## 🚀 はじめに

### 必要なツール
- **Git**: バージョン管理
- **VS Code**: 推奨エディタ
- **Docker Desktop**: コンテナ実行環境
- **uv**: Pythonパッケージマネージャー（高速）
- **GitHub アカウント**: ProjectTeam-Ramen組織メンバー

### VS Code拡張機能（推奨）
- **Dev Containers**: コンテナ内開発環境
- **Docker**: Docker管理
- **Python**: Python開発支援
- **Ruff**: Pythonリンター・フォーマッター
- **GitHub Pull Requests**: PR管理

### 初回セットアップ
```bash
# プロジェクトをクローン
git clone https://github.com/ProjectTeam-Ramen/receipt-recipe.git
cd receipt-recipe

# 自分の名前を設定（初回のみ）
git config user.name "あなたの名前"
git config user.email "あなたのメール"
```

### 開発環境の選択

このプロジェクトでは、**Dev Container環境（推奨）** または **Docker環境** のいずれかで開発できます。

#### 方法1: Dev Container環境（✅ 推奨）

**特徴:**
- VS Code内で完結した開発環境
- 依存関係が自動的にインストールされる
- 拡張機能が自動的にセットアップされる
- デバッグ機能がすぐに使える

**セットアップ手順:**
```bash
# 1. VS Codeでプロジェクトを開く
code .

# 2. VS Codeの左下の青いアイコン（><）をクリックするか、
#    コマンドパレット（Ctrl+Shift+P / Cmd+Shift+P）で以下を実行:
#    > Dev Containers: Reopen in Container

# 3. コンテナのビルドと起動が自動的に実行されます（初回は数分かかります）

# 4. コンテナが起動すると、以下が自動的に実行されます:
#    - 開発用依存関係のインストール（ruff, pytest等）
#    - VS Code拡張機能のインストール
#    - Python環境の設定
```

**Dev Container起動後の確認:**
```bash
# ターミナルを開く（Ctrl+` / Cmd+`）
# コンテナ内で実行されることを確認（プロンプトにappuser@...と表示される）

# ruffが使えることを確認
uv run ruff --version
# 出力例: ruff 0.14.0

# 依存関係を確認
uv pip list
```

#### 方法2: Docker環境（コマンドライン）

**セットアップ手順:**
```bash
# 開発環境を起動
docker-compose up --build -d

# コンテナ内に入る
docker-compose exec api bash

# 依存関係をインストール
uv sync --extra dev --frozen
```

## 🛠️ 技術スタック

### Backend
- **FastAPI**: 高速なPython Webフレームワーク
- **SQLAlchemy**: ORMライブラリ
- **SQLite**: データベース（開発環境）  
- **Pydantic**: データバリデーション

### AI/機械学習
- **PyTorch**: 機械学習フレームワーク
- **OpenCV**: 画像処理
- **Pillow**: 画像操作

### 開発・デプロイ
- **Docker**: コンテナ化
- **uv**: パッケージ管理
- **ruff**: Pythonリンター・フォーマッター（高速）
- **VS Code Dev Containers**: 統一開発環境
- **GitHub Actions**: CI/CD自動化

## 🔄 日常の作業フロー

### 作業開始時（毎回）
```bash
# 最新の状態に更新
git checkout main
git pull origin main

# 作業用ブランチを作成
git checkout -b feature/機能名
# 例: git checkout -b feature/receipt-upload

# 開発環境を起動
docker-compose up -d
```

### 開発環境の利用

#### Dev Container環境（推奨）

**起動方法:**
```bash
# VS Codeでプロジェクトを開く
code .

# 左下の青いアイコン（><）をクリック → 「Reopen in Container」
# または、コマンドパレット（Ctrl+Shift+P）で:
# > Dev Containers: Reopen in Container
```

**Dev Containerの利点:**
- ✅ **統一された開発環境**: チーム全員が同じ環境で開発
- ✅ **自動セットアップ**: コンテナ起動時に開発ツール（ruff等）が自動インストール
- ✅ **拡張機能の自動インストール**: Python、Ruff、Docker等の拡張が自動設定
- ✅ **デバッグ機能の完全対応**: ブレークポイントやステップ実行が使える
- ✅ **ホットリロード機能**: コード変更が即座に反映される
- ✅ **Git統合**: VS Code内でGit操作が完結

**Dev Container内での作業:**
```bash
# ターミナルを開く（Ctrl+` / Cmd+`）
# コンテナ内でコマンドが実行されます

# コードのチェック
uv run ruff check .

# コードの自動修正
uv run ruff check . --fix

# フォーマット
uv run ruff format .

# テストの実行
uv run pytest

# アプリケーションの起動（通常は自動起動）
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Dev Containerの再ビルド:**

設定ファイルやDockerfileを変更した場合は、コンテナを再ビルドする必要があります。

```bash
# コマンドパレット（Ctrl+Shift+P）で:
# > Dev Containers: Rebuild Container

# または、完全に再ビルドする場合:
# > Dev Containers: Rebuild Container Without Cache
```

**安全なリポジトリ設定:**

Dev Container内でGitコマンドを初めて実行する際、以下のエラーが出る場合があります:
```
fatal: unsafe repository ('/workspace' is owned by someone else)
```

この場合、以下のコマンドを実行してください:
```bash
git config --global --add safe.directory /workspace
```

#### Docker環境（コマンドライン）
```bash
# 開発環境の起動（ホットリロード有効）
docker-compose up -d

# ログの確認
docker-compose logs -f api

# 環境の停止
docker-compose down
```

#### ローカル環境（非推奨）

**前提条件:**
- Python 3.8以上がインストールされていること
- uvがインストールされていること

```bash
# uvのインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係のインストール（開発ツール含む）
uv sync --extra dev --frozen

# アプリケーションの起動
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**注意:** ローカル環境は環境差異が発生しやすいため、Dev Container環境の使用を推奨します。

#### API確認方法
- **ルートエンドポイント**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ヘルスチェック**: http://localhost:8000/health

### コード品質チェック

#### ruffによるリンティング（自動実行）

**Dev Container環境では:**
- ファイル保存時に自動的にフォーマットが適用されます
- リアルタイムでコードの問題が表示されます
- VS Codeの拡張機能により、問題箇所に波線が表示されます

**手動でのチェック:**
```bash
# コードスタイルのチェック
uv run ruff check .

# 自動修正を適用
uv run ruff check . --fix

# コードフォーマット
uv run ruff format .

# チェックとフォーマットを一度に実行
uv run ruff check . --fix && uv run ruff format .
```

#### 開発用依存関係

**自動インストール（Dev Container）:**
Dev Containerを使用する場合、以下のツールが自動的にインストールされます:
- `ruff`: 高速リンター・フォーマッター
- `pytest`: テストフレームワーク
- `pytest-asyncio`: 非同期テスト対応
- `httpx`: HTTPクライアント（テスト用）
- `black`: コードフォーマッター
- `flake8`: リンター
- `mypy`: 型チェッカー

**手動インストール（必要な場合）:**
```bash
# 開発用パッケージをインストール
uv sync --extra dev --frozen

# 特定のパッケージのみ追加
uv pip install --system <package-name>
```

**重要な注意:**
- `uv sync --dev` は**動作しません**
- 正しいコマンドは `uv sync --extra dev --frozen` です
- `--extra dev` により、pyproject.tomlの`[project.optional-dependencies]`セクションの`dev`グループがインストールされます
- `--frozen` により、uv.lockファイルからの厳密なバージョンでインストールされます

### 作業中
```bash
# ファイルを編集後、変更を確認
git status
git diff

# Dev Container内でGitを初めて使う場合
git config --global --add safe.directory /workspace

# ruffでコードスタイルをチェック
uv run ruff check .

# 問題があれば自動修正
uv run ruff check . --fix

# コードフォーマット
uv run ruff format .

# 変更をコミット
git add .
git commit -m "feat: レシート画像アップロード機能を追加"
```

### 作業完了時
```bash
# GitHubにアップロード
git push origin feature/機能名

# その後、GitHub上でプルリクエストを作成
# GitHub Actionsが自動でコード品質をチェック
```

## ⚡ よく使うGitコマンド

### 状況確認
```bash
git status           # 現在の状態を確認
git log --oneline    # コミット履歴を確認
git branch          # ブランチ一覧
```

### 変更の取り消し
```bash
git checkout .       # 未コミットの変更を取り消し
git reset HEAD~1     # 直前のコミットを取り消し（変更は保持）
```

### ブランチ操作
```bash
git checkout main           # mainブランチに移動
git checkout -b new-branch  # 新しいブランチを作成して移動
git branch -d branch-name   # ブランチを削除
```

## 📝 コミットメッセージのルール

### 基本形式
```
type: 日本語で簡潔な説明
```

### よく使うtype
- `feat`: 新機能を追加
- `fix`: バグを修正
- `docs`: ドキュメントを変更
- `style`: 見た目やフォーマットを変更
- `refactor`: コードの整理
- `test`: テストを追加・修正
- `docker`: Docker関連の設定
- `ci`: CI/CD設定の変更

### 良い例 ✅
```bash
git commit -m "feat: レシート画像アップロード機能を追加"
git commit -m "fix: 画像処理時のメモリリークを修正"
git commit -m "docs: API仕様書を更新"
git commit -m "style: ruffによるコードフォーマット適用"
git commit -m "ci: GitHub Actionsにruffリントを追加"
```

### 悪い例 ❌
```bash
git commit -m "update"           # 何を更新したかわからない
git commit -m "ちょっと修正"       # typeがない
git commit -m "FIX: バグ修正"     # 大文字はNG
```

## 🔍 プルリクエスト（PR）の作り方

### 1. GitHub上でPRを作成
1. https://github.com/ProjectTeam-Ramen/receipt-recipe にアクセス
2. 「Compare & pull request」ボタンをクリック
3. タイトルと説明を入力
4. 「Create pull request」をクリック

### 2. GitHub Actionsによる自動チェック
- **コード品質**: ruffによるリンティングが自動実行
- **自動修正**: コードスタイルの問題が検出されると自動的に修正コミットが作成される
- **チェック結果**: PRページで成功/失敗を確認
- **ローカルで修正**: エラーが出た場合は`uv run ruff check . --fix`を実行してプッシュ

**GitHub Actionsで実行される内容:**
1. `uv sync --extra dev --frozen` - 開発用依存関係をインストール
2. `uv run ruff check .` - コードスタイルをチェック
3. `uv run ruff check . --fix` - 自動修正を適用
4. `uv run ruff format .` - コードフォーマット
5. 変更があれば自動的にコミット&プッシュ

### 3. PR のタイトル例
```
feat: レシート画像アップロード機能を追加
fix: Docker環境でのuvicorn起動エラーを修正
docs: 開発ガイドとREADMEを更新
style: ruffによるコードフォーマット統一
ci: GitHub Actionsワークフロー追加
```

## 🚀 GitHub Actions

### 自動実行される処理
- **リンティング**: プルリクエスト時にruffが自動実行
- **コード品質チェック**: コーディング規約の自動検証
- **手動修正**: Actions画面から手動でコード修正を実行可能

### GitHub Actions確認方法
1. リポジトリの「Actions」タブにアクセス
2. 最新のワークフロー実行結果を確認
3. 失敗した場合はログを確認してローカルで修正

### 手動でのコード修正実行
1. 「Actions」タブ → 「Lint Fix」ワークフローを選択
2. 「Run workflow」ボタンをクリック
3. ブランチを選択して実行

## 🐛 トラブルシューティング

### Docker関連
```bash
# コンテナの完全な再ビルド
docker-compose down --rmi all --volumes --remove-orphans
docker-compose up --build

# コンテナ内でのデバッグ
docker-compose exec api bash

# ログの確認
docker-compose logs api
```

### Dev Container関連
```bash
# VS Code でDev Container が起動しない場合
# 1. Docker Desktop が起動していることを確認
# 2. VS Code の Dev Containers 拡張機能をインストール
# 3. コマンドパレット > "Dev Containers: Rebuild Container"

# コンテナ内でのデバッグ
# VS Code のターミナル（Ctrl+`）はコンテナ内で実行される
```

### uv・ruff関連
```bash
# キャッシュのクリア
uv cache clean

# 依存関係の再インストール（正しいコマンド）
uv sync --extra dev --frozen --reinstall

# ruffが見つからない場合（Dev Containerを再ビルド）
# コマンドパレット > "Dev Containers: Rebuild Container"

# または手動でインストール
uv sync --extra dev --frozen

# ruffの設定確認
uv run ruff check . --show-settings  # 現在の設定を表示

# ruffのバージョン確認
uv run ruff --version
```

**よくある問題:**
- `uv sync --dev` は動作しません → `uv sync --extra dev --frozen` を使用
- `ruff: command not found` → `uv run ruff` を使用するか、Dev Containerを再ビルド
- Dev Container内でruffが見つからない → Dockerfileの設定を確認し、コンテナを再ビルド

### GitHub Actions関連
```bash
# ローカルでGitHub Actionsと同じチェックを実行
uv run ruff check .

# 修正を適用
uv run ruff check . --fix

# フォーマットも適用
uv run ruff format .

# 設定ファイルを確認
cat pyproject.toml  # [tool.ruff]セクションを確認
cat .github/workflows/lint.yml  # ワークフロー設定を確認
```

**GitHub Actionsのトラブルシューティング:**
- ワークフローが失敗する場合、ローカルで同じコマンドを実行して問題を確認
- `Failed to spawn: ruff` エラー → `.github/workflows/lint.yml`で`uv sync --extra dev --frozen`が実行されているか確認
- 自動修正コミットが作成されない → PRの権限設定を確認

## 📁 プロジェクト構造

```
receipt-recipe/
├── .github/                # GitHub設定
│   └── workflows/         # GitHub Actionsワークフロー
│       └── lint.yml       # ruffリンティング設定
├── .devcontainer/          # VS Code Dev Container設定
│   └── devcontainer.json  # コンテナ設定ファイル
├── app/                    # FastAPIアプリケーション
│   ├── __init__.py        # メインアプリケーション
│   └── ...
├── docker-compose.yml     # 基本Docker設定
├── docker-compose.override.yml  # 開発環境設定
├── docker-compose.gpu.yml # GPU環境設定
├── Dockerfile            # Dockerイメージ定義
├── pyproject.toml        # Python プロジェクト設定（ruff設定含む）
├── uv.lock              # 依存関係ロックファイル
├── README.md            # プロジェクト概要
└── CONTRIBUTING.md      # この開発ガイド
```

## 🔧 Dev Container設定の詳細

### 自動セットアップの仕組み

Dev Containerは、以下のファイルによって自動的に構成されます:

**1. `.devcontainer/devcontainer.json`**
```json
{
  "dockerComposeFile": [
    "../docker-compose.yml",
    "../docker-compose.override.yml"
  ],
  "service": "api",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "charliermarsh.ruff",
        // その他の拡張機能
      ],
      "settings": {
        "editor.formatOnSave": true,
        // その他の設定
      }
    }
  }
}
```

**2. `docker-compose.override.yml`**
```yaml
services:
  api:
    build:
      args:
        INSTALL_DEV: "true"  # 開発用依存関係をインストール
```

**3. `Dockerfile`**
```dockerfile
ARG INSTALL_DEV=false

RUN if [ "$INSTALL_DEV" = "true" ]; then \
    uv sync --extra dev --frozen; \
    else \
    uv sync --frozen; \
    fi
```

### Dev Containerの起動フロー

1. **コンテナのビルド**: Dockerfileに基づいてイメージを構築
2. **環境変数の設定**: `INSTALL_DEV=true`により開発モードを指定
3. **依存関係のインストール**: `uv sync --extra dev --frozen`を実行
4. **VS Code拡張機能のインストール**: Python、Ruff等の拡張を自動インストール
5. **設定の適用**: フォーマット、リンティングの設定を適用
6. **開発環境の準備完了**: ターミナルとエディタが使用可能に

### 本番環境との違い

| 項目 | Dev Container（開発） | 本番環境 |
|------|----------------------|----------|
| 依存関係 | 開発ツール含む（ruff, pytest等） | 本番用のみ |
| Docker Compose | `docker-compose.override.yml`使用 | `docker-compose.prod.yml`使用 |
| `INSTALL_DEV` | `true` | `false` |
| uvコマンド | `uv sync --extra dev --frozen` | `uv sync --frozen` |
| ホットリロード | 有効 | 無効 |

### 必要なファイル
- `.devcontainer/devcontainer.json`: VS Code Dev Container設定
- `docker-compose.override.yml`: 開発環境用のビルド設定（`INSTALL_DEV=true`）
- `Dockerfile`: 環境に応じた依存関係インストール

### Dev Container使用時の利点
- **統一開発環境**: チーム全員が同じ環境で開発
- **自動拡張機能**: Python、Docker、Ruff関連の拡張が自動インストール  
- **デバッグ対応**: VS Codeのデバッガーが完全動作
- **インテリセンス**: コード補完とエラー検出
- **ターミナル統合**: コンテナ内で直接コマンド実行
- **依存関係の自動管理**: コンテナビルド時にruff等が自動インストール

## 📋 現在の開発状況

### ✅ 完了項目
- [x] プロジェクト基本構成
- [x] Docker環境構築
- [x] FastAPI基本実装
- [x] uv による依存関係管理
- [x] ruff による自動コード品質管理
- [x] GitHub Actions CI/CD設定
- [x] 開発環境のホットリロード
- [x] Dev Container設定

### 🔄 開発中
- [ ] レシート画像アップロード機能
- [ ] OCR（文字認識）機能
- [ ] AI レシピ提案システム
- [ ] データベース設計・実装

### 📅 今後の予定
- [ ] フロントエンド実装
- [ ] ユーザー認証システム
- [ ] 本番環境デプロイ設定

## 📞 サポート

### 開発環境のトラブル
- **Dev Container が起動しない** 
  - Docker Desktop が起動しているか確認
  - Dev Containers 拡張機能がインストールされているか確認
  - コマンドパレット > "Dev Containers: Rebuild Container"を実行
  
- **Python拡張機能が動作しない** 
  - Dev Container内で開発しているか確認（左下の青いアイコンで確認）
  - コンテナを再ビルド
  
- **ホットリロードが効かない** 
  - `docker-compose.override.yml`の設定確認
  - コンテナを再起動: `docker-compose restart api`
  
- **ruffが動作しない** 
  - Dev Containerを再ビルド（推奨）
  - または手動インストール: `uv sync --extra dev --frozen`
  - `uv run ruff --version`でインストール確認
  
- **GitHub Actionsが失敗** 
  - ローカルで`uv run ruff check .`を実行して問題を確認
  - `.github/workflows/lint.yml`で`uv sync --extra dev --frozen`が使われているか確認
  - 修正後、`uv run ruff check . --fix`を実行してコミット
  
- **Git操作でエラー（unsafe repository）**
  ```bash
  git config --global --add safe.directory /workspace
  ```

## 📚 更新履歴

- **2025/10/08**: Dev Container詳細設定を追加、開発環境セットアップ手順を大幅更新、uvコマンド修正（`--dev` → `--extra dev --frozen`）
- **2025/10/07**: Docker環境構築完了、技術スタック決定、ruff・GitHub Actions導入
- **2025/10/03**: 初版作成
- プロジェクトの成長に合わせて随時更新予定