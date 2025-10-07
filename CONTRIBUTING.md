# 開発ガイドブック

Receipt Recipe プロジェクトのチーム開発ガイドです。

## 🚀 はじめに

### 必要なツール
- **Git**: バージョン管理
- **VS Code**: 推奨エディタ
- **Docker Desktop**: コンテナ実行環境
- **uv**: Pythonパッケージマネージャー（高速）
- **GitHub アカウント**: ProjectTeam-Ramen組織メンバー

### 初回セットアップ
```bash
# プロジェクトをクローン
git clone https://github.com/ProjectTeam-Ramen/receipt-recipe.git
cd receipt-recipe

# 自分の名前を設定（初回のみ）
git config user.name "あなたの名前"
git config user.email "あなのメール"

# 開発環境の起動
docker-compose up --build -d
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
- **VS Code Dev Containers**: 統一開発環境

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

#### Docker環境（推奨）
```bash
# 開発環境の起動（ホットリロード有効）
docker-compose up -d

# ログの確認
docker-compose logs -f api

# 環境の停止
docker-compose down
```

#### ローカル環境
```bash
# 依存関係のインストール
uv sync

# アプリケーションの起動
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

#### API確認方法
- **ルートエンドポイント**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ヘルスチェック**: http://localhost:8000/health

### 作業中
```bash
# ファイルを編集後、変更を確認
git status
git diff

# 変更をコミット
git add .
git commit -m "feat: レシート画像アップロード機能を追加"
```

### 作業完了時
```bash
# GitHubにアップロード
git push origin feature/機能名

# その後、GitHub上でプルリクエストを作成
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

### 良い例 ✅
```bash
git commit -m "feat: レシート画像アップロード機能を追加"
git commit -m "fix: 画像処理時のメモリリークを修正"
git commit -m "docs: API仕様書を更新"
git commit -m "docker: CUDA対応のベースイメージに変更"
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

### 2. PR のタイトル例
```
feat: レシート画像アップロード機能を追加
fix: Docker環境でのuvicorn起動エラーを修正
docs: 開発ガイドとREADMEを更新
docker: GPU対応とマルチステージビルドを実装
```

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

### uv関連
```bash
# キャッシュのクリア
uv cache clean

# 依存関係の再インストール
uv sync --reinstall
```

## 📁 プロジェクト構造

```
receipt-recipe/
├── app/                    # FastAPIアプリケーション
│   ├── __init__.py        # メインアプリケーション
│   └── ...
├── docker-compose.yml     # 基本Docker設定
├── docker-compose.override.yml  # 開発環境設定
├── docker-compose.gpu.yml # GPU環境設定
├── Dockerfile            # Dockerイメージ定義
├── pyproject.toml        # Python プロジェクト設定
├── uv.lock              # 依存関係ロックファイル
├── README.md            # プロジェクト概要
└── CONTRIBUTING.md      # この開発ガイド
```

## 📋 現在の開発状況

### ✅ 完了項目
- [x] プロジェクト基本構成
- [x] Docker環境構築
- [x] FastAPI基本実装
- [x] uv による依存関係管理
- [x] 開発環境のホットリロード

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

### 質問・相談
- GitHub Issues で質問を投稿
- チームメンバーとの相談
- 技術的な問題は開発者に相談

## 📚 更新履歴

- **2025/10/07**: Docker環境構築完了、技術スタック決定
- **2025/10/03**: 初版作成
- プロジェクトの成長に合わせて随時更新予定