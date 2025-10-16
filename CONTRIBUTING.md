# 開発ガイド

Receipt Recipe プロジェクトの開発ガイドです。

## 📋 目次

- [はじめに](#はじめに)
- [開発環境のセットアップ](#開発環境のセットアップ)
- [日常の作業フロー](#日常の作業フロー)
- [コーディング規約](#コーディング規約)
- [Git運用ルール](#git運用ルール)
- [プルリクエスト](#プルリクエスト)
- [GitHub Actions](#github-actions)
- [トラブルシューティング](#トラブルシューティング)
- [プロジェクト構造](#プロジェクト構造)
- [サポート](#サポート)

## はじめに

このプロジェクトは、レシート画像から料理レシピを生成するAIアプリケーションです。
チーム開発を円滑に進めるため、このガイドに従って開発を進めてください。

### 技術スタック

**Backend**
- FastAPI, SQLAlchemy, MySQL, Pydantic

**AI/機械学習**
- PyTorch 1.12.0, CUDA 11.7, Transformers, torch-geometric
- OpenCV, Pillow, Tesseract (OCR)

**自然言語処理・スクレイピング**
- MeCab, BeautifulSoup4, Selenium, requests

**開発・デプロイ**
- Docker, uv (パッケージ管理), ruff (リンター/フォーマッター)
- VS Code Dev Containers, GitHub Actions

詳細は [docs/environment.md](docs/environment.md) を参照してください。

## 開発環境のセットアップ

### 初回セットアップ

**[📚 セットアップガイド](docs/setup.md) を参照してください。**

以下の手順で環境構築を行います:

1. Docker Desktop のインストール
2. VS Code と Dev Containers 拡張機能のインストール
3. Git の初期設定
4. プロジェクトのクローン
5. Dev Container で開く
6. 環境の動作確認

### クイックスタート

```bash
# プロジェクトをクローン
git clone https://github.com/ProjectTeam-Ramen/receipt-recipe.git
cd receipt-recipe

# VS Codeで開く
code .

# コマンドパレット (Ctrl+Shift+P) で
# "Dev Containers: Reopen in Container" を実行
```

## 日常の作業フロー

### 作業開始

```bash
# 1. VS CodeでDev Containerを開く
code .
# 左下のアイコン（><）→ "Reopen in Container"

# 2. 最新の状態に更新
git checkout main
git pull origin main

# 3. 作業用ブランチを作成
git checkout -b feature/機能名
# 例: git checkout -b feature/receipt-upload
```

### 開発作業

#### コードの編集

- VS Codeでファイルを編集
- ファイル保存時に自動的にruffフォーマットが適用される

#### コード品質チェック

```bash
# リンティング
uv run ruff check .

# 自動修正
uv run ruff check . --fix

# フォーマット
uv run ruff format .
```

#### テストの実行

```bash
# すべてのテストを実行
uv run pytest

# カバレッジ付き
uv run pytest --cov=app

# 特定のテストのみ
uv run pytest tests/test_api.py

# 詳細な出力
uv run pytest -v
```

#### アプリケーションの起動

```bash
# 開発サーバーを起動（ホットリロード有効）
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# アクセス先:
# http://localhost:8000 - メインページ
# http://localhost:8000/docs - Swagger UI
# http://localhost:8000/redoc - ReDoc
# http://localhost:8000/health - ヘルスチェック
```

#### データベース操作

```bash
# MySQLに接続
mysql -h db -u user -ppassword receipt_recipe

# MySQL内でのコマンド:
# SHOW TABLES;              -- テーブル一覧
# DESCRIBE table_name;      -- テーブル構造
# SELECT * FROM table_name; -- データ確認
# exit                      -- 終了

# Alembicマイグレーション
alembic revision --autogenerate -m "マイグレーション内容"
alembic upgrade head
alembic downgrade -1
```

### コミットとプッシュ

```bash
# 変更をステージング
git add .

# コミット（コミットメッセージ規約に従う）
git commit -m "feat: レシート画像アップロード機能を追加"

# プッシュ
git push -u origin feature/機能名  # 初回
git push                          # 2回目以降
```

### 作業終了

```bash
# mainブランチに戻る
git checkout main

# 最新の状態に更新
git pull origin main

# マージ済みのブランチを削除（オプション）
git branch -d feature/機能名
```

## コーディング規約

### Pythonコーディングスタイル

- **PEP 8** に準拠
- **ruff** による自動フォーマット・リンティング
- 行の最大長: 88文字（black互換）
- インデント: スペース4つ

### 命名規則

```python
# クラス: PascalCase
class ReceiptProcessor:
    pass

# 関数・変数: snake_case
def process_receipt_image(image_path: str) -> dict:
    receipt_data = {}
    return receipt_data

# 定数: UPPER_SNAKE_CASE
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

# プライベート: 先頭にアンダースコア
def _internal_helper():
    pass
```

### 型ヒント

```python
from typing import List, Dict, Optional

def get_recipes(
    ingredients: List[str],
    max_results: int = 10,
    user_id: Optional[int] = None
) -> List[Dict[str, any]]:
    """レシピを取得する
    
    Args:
        ingredients: 食材のリスト
        max_results: 最大結果数
        user_id: ユーザーID（オプション）
    
    Returns:
        レシピのリスト
    """
    pass
```

### Docstring

```python
def process_image(image_path: str, options: dict = None) -> dict:
    """画像を処理してテキストを抽出する
    
    この関数はOCRエンジンを使用して画像からテキストを抽出し、
    前処理を行った結果を返します。
    
    Args:
        image_path: 処理する画像ファイルのパス
        options: 処理オプション（デフォルト: None）
            - threshold: 二値化の閾値（0-255）
            - denoise: ノイズ除去の有効化（bool）
    
    Returns:
        処理結果を含む辞書
        - text: 抽出されたテキスト
        - confidence: 信頼度スコア（0-100）
        - coordinates: テキスト領域の座標
    
    Raises:
        FileNotFoundError: 画像ファイルが見つからない場合
        ValueError: 画像形式が不正な場合
    
    Example:
        >>> result = process_image("receipt.jpg")
        >>> print(result["text"])
        'レシート内容...'
    """
    pass
```

## Git運用ルール

### ブランチ戦略

```
main          # 本番環境用（保護ブランチ）
  ├─ feature/xxx  # 新機能開発
  ├─ fix/xxx      # バグ修正
  ├─ docs/xxx     # ドキュメント更新
  └─ refactor/xxx # リファクタリング
```

### ブランチ命名規則

```bash
feature/機能名      # 新機能
fix/バグ内容        # バグ修正
docs/ドキュメント名  # ドキュメント
refactor/対象      # リファクタリング
perf/最適化内容    # パフォーマンス改善
test/テスト内容    # テスト追加
chore/作業内容     # その他の作業

# 例:
feature/receipt-upload
fix/database-connection
docs/api-specification
refactor/ocr-pipeline
```

### コミットメッセージ規約

#### 基本形式

```
type: 日本語で簡潔な説明

詳細な説明（オプション）
- 変更内容1
- 変更内容2
```

#### type 一覧

| type | 説明 | 例 |
|------|------|-----|
| `feat` | 新機能を追加 | `feat: レシート画像アップロード機能を追加` |
| `fix` | バグを修正 | `fix: 画像処理時のメモリリークを修正` |
| `docs` | ドキュメントを変更 | `docs: API仕様書を更新` |
| `style` | コードフォーマット | `style: ruffによるコードフォーマット適用` |
| `refactor` | リファクタリング | `refactor: データベース接続ロジックを整理` |
| `test` | テスト追加・修正 | `test: OCR機能のユニットテストを追加` |
| `chore` | ビルド・補助ツール | `chore: 依存関係を更新` |
| `perf` | パフォーマンス改善 | `perf: 画像処理の高速化` |
| `ci` | CI/CD設定の変更 | `ci: GitHub Actionsにruffリントを追加` |

#### 良い例 ✅

```bash
git commit -m "feat: レシート画像アップロード機能を追加"

git commit -m "fix: 画像処理時のメモリリークを修正

- cv2.imreadの後にreleaseを追加
- 一時ファイルの削除処理を追加"

git commit -m "docs: API仕様書とCONTRIBUTING.mdを更新"

git commit -m "refactor: データベース接続ロジックをヘルパー関数に分離"
```

#### 悪い例 ❌

```bash
git commit -m "update"              # 何を更新したかわからない
git commit -m "ちょっと修正"         # typeがない、内容が不明確
git commit -m "FIX: バグ修正"        # 大文字はNG
git commit -m "fix bug"             # 日本語で書く
```

### よく使うGitコマンド

#### 状況確認

```bash
git status                  # 現在の状態
git log --oneline          # コミット履歴
git log --graph --oneline  # グラフ表示
git branch                 # ブランチ一覧
git diff                   # 変更差分
```

#### 変更の取り消し

```bash
git checkout .             # 未コミットの変更を取り消し
git reset HEAD~1           # 直前のコミットを取り消し（変更は保持）
git reset --hard HEAD~1    # 直前のコミットを完全に取り消し（注意！）
```

#### ブランチ操作

```bash
git checkout main          # mainブランチに移動
git checkout -b new-branch # 新しいブランチを作成して移動
git branch -d branch-name  # ブランチを削除
git merge feature-branch   # マージ
```

## プルリクエスト

### PRのタイトル

コミットメッセージと同じ形式:

```
feat: レシート画像アップロード機能を追加
fix: Docker環境でのuvicorn起動エラーを修正
docs: 開発ガイドとREADMEを更新
```

### PRの説明テンプレート

```markdown
## 概要
このPRの目的を簡潔に説明してください。

## 変更内容
- 変更内容1
- 変更内容2
- 変更内容3

## 関連Issue
Closes #123

## チェックリスト
- [ ] コードが正常に動作することを確認した
- [ ] ruffでリンティングを実行した
- [ ] テストを追加・更新した
- [ ] ドキュメントを更新した（必要な場合）

## スクリーンショット（該当する場合）
画面の変更がある場合、スクリーンショットを添付してください。

## 備考
その他、レビュアーに伝えたいことがあれば記載してください。
```

### レビュープロセス

1. **レビュアーの指定**: PR作成時に「Reviewers」でチームメンバーを指定
2. **レビューコメントへの対応**: 指摘事項を修正してプッシュ
3. **承認後のマージ**: すべてのレビュアーの承認 + GitHub Actionsパス後にマージ

### GitHub Actionsの自動チェック

PRを作成すると、以下が自動実行されます:

```yaml
✓ 依存関係のインストール (uv sync --extra dev --frozen)
✓ コードスタイルのチェック (uv run ruff check .)
✓ 自動修正の適用 (uv run ruff check . --fix)
✓ コードフォーマット (uv run ruff format .)
✓ 変更があればコミット＆プッシュ
```

**ローカルで事前チェック:**
```bash
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .
```

## GitHub Actions

### 設定されているワークフロー

#### Lint Fix（自動コード修正）

**トリガー:**
- プルリクエストの作成・更新時
- mainブランチへのプッシュ時
- 手動実行（workflow_dispatch）

**実行内容:**
1. リポジトリのチェックアウト
2. Python 3.8のセットアップ
3. uvのインストール
4. 依存関係のインストール
5. ruffによるリンティング・自動修正・フォーマット
6. 変更があればコミット＆プッシュ

### 手動でワークフローを実行

1. GitHubリポジトリの「Actions」タブにアクセス
2. 「Lint Fix」ワークフローを選択
3. 「Run workflow」ボタンをクリック
4. ブランチを選択して実行

## トラブルシューティング

### Docker関連

#### コンテナの完全な再ビルド

```bash
docker compose down --rmi all --volumes --remove-orphans
docker builder prune -a
docker compose up --build
```

#### コンテナ内でのデバッグ

```bash
docker compose exec api bash
docker compose logs api
docker compose logs -f api  # リアルタイム監視
```

### Dev Container関連

#### Dev Containerが起動しない

```bash
# Docker Desktopが起動していることを確認
docker info

# Dev Containerを再ビルド
# コマンドパレット → "Dev Containers: Rebuild Container"
```

#### Python拡張機能が動作しない

```bash
# コンテナを再ビルド
# コマンドパレット → "Dev Containers: Rebuild Container"

# Python interpreterを再選択
# コマンドパレット → "Python: Select Interpreter"
```

### uv・ruff関連

#### ruffが動作しない

```bash
uv run ruff --version
uv sync --extra dev --frozen

# Dev Containerを再ビルド（推奨）
```

#### 依存関係のインストールエラー

```bash
rm uv.lock
uv lock
uv sync --extra dev --frozen
```

### Git関連

#### unsafe repository エラー

```bash
git config --global --add safe.directory /workspace
```

#### マージコンフリクトの解決

```bash
git checkout main
git pull origin main
git checkout feature/your-branch
git merge main
# コンフリクト解決後
git add .
git commit -m "fix: マージコンフリクトを解決"
git push
```

### MySQL関連

#### 接続エラー

```bash
docker compose ps db
docker compose up db -d
docker compose logs db
mysql -h db -u user -ppassword receipt_recipe
```

#### データベースのリセット

```bash
docker compose down --volumes
docker compose up -d
alembic upgrade head
```

詳細なトラブルシューティングは [docs/setup.md](docs/setup.md#トラブルシューティング初回セットアップ) を参照してください。

## プロジェクト構造

```
receipt-recipe/
├── .github/
│   └── workflows/          # GitHub Actions
├── .devcontainer/          # Dev Container設定
├── app/                    # FastAPIアプリケーション
│   ├── __init__.py
│   ├── api/               # APIエンドポイント
│   ├── core/              # コア機能
│   ├── models/            # データモデル
│   ├── schemas/           # Pydanticスキーマ
│   ├── services/          # ビジネスロジック
│   └── db/                # データベース関連
├── tests/                 # テストコード
├── docs/                  # ドキュメント
│   ├── setup.md          # セットアップガイド
│   ├── environment.md    # 環境構築詳細
│   └── architecture.md   # システムアーキテクチャ
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── README.md
└── CONTRIBUTING.md        # このファイル
```

## サポート

### 質問・相談

- **GitHub Discussions**: プロジェクトリポジトリのDiscussionsで質問
- **Slack/Discord**: チームのチャンネルで気軽に質問
- **Issue作成**: バグ報告や機能要望はIssueで

### よくある質問（FAQ）

**Q: Dev Containerとは何ですか？**  
A: VS Code内で動作する開発用Dockerコンテナです。チーム全員が同じ環境で開発できます。

**Q: uvとpipの違いは何ですか？**  
A: uvはpipよりも高速で、依存関係の解決が優れています。このプロジェクトではuvを使用します。

**Q: ruffとは何ですか？**  
A: Pythonのリンター・フォーマッターで、blackやflake8よりも高速です。

**Q: ローカルでテストを実行するにはどうすればいいですか？**  
A: `uv run pytest` を実行してください。

**Q: データベースをリセットするにはどうすればいいですか？**  
A: `docker compose down --volumes` → `docker compose up -d` → `alembic upgrade head`

## 参考リンク

### プロジェクトドキュメント
- [セットアップガイド](docs/setup.md)
- [環境構築詳細](docs/environment.md)
- [システムアーキテクチャ](docs/architecture.md)

### 公式ドキュメント
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

### 学習リソース
- [Git Handbook](https://guides.github.com/introduction/git-handbook/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Python Style Guide (PEP 8)](https://pep8-ja.readthedocs.io/ja/latest/)
- [Conventional Commits](https://www.conventionalcommits.org/ja/)

## 開発状況

### ✅ 完了項目
- [x] プロジェクト基本構成
- [x] Docker環境構築
- [x] Dev Container設定
- [x] MySQL データベース設定
- [x] uv による依存関係管理
- [x] ruff による自動コード品質管理
- [x] GitHub Actions CI/CD設定

### 🔄 開発中
- [ ] レシート画像アップロード機能
- [ ] OCR（文字認識）機能
- [ ] AI レシピ提案システム
- [ ] データベース設計・実装
- [ ] ユーザー認証システム

### 📅 今後の予定
- [ ] フロントエンド実装
- [ ] レシピ検索機能
- [ ] お気に入り機能
- [ ] 本番環境デプロイ設定

---

**このガイドは継続的に更新されます。改善提案があれば、PRまたはIssueで提案してください！**

**最終更新日**: 2025年10月16日