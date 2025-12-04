# receipt-recipe
Receipt-Based Food Management and Recipe Recommendation Service

## 🧰 セットアップ

### 1. データベースの準備

MySQL でスキーマを作成し、アプリ用ユーザーに権限を付与します。

```bash
mysql -u root -p < init.sql
```

`.env` もしくは環境変数で `DATABASE_URL`（例: `mysql+pymysql://user:password@127.0.0.1/receipt_recipe_db`）を指定してください。未設定の場合は `mysql+pymysql://user:password@db:3306/receipt_recipe_db` に接続します（`docker-compose.override.yml` の `db` サービス）。

> 既定では SQLite へのフォールバックは行わず、常に MySQL に書き込みます。SQLite を使いたい場合は明示的に `DATABASE_URL=sqlite:///./app.db` などを設定してください。

### 2. バックエンドの起動

```bash
uvicorn app.backend.api.app:app --host 127.0.0.1 --port 8000 --reload
```

FastAPI は `http://127.0.0.1:8000/api/v1` で待ち受け、JWT 認証 / ユーザー登録 / 受信箱 API を提供します。

### 3. フロントエンドの配信

`app/frontend` を静的ホスティング（例: VSCode Live Server, `python -m http.server` など）で配信します。`config.js` がホスト名を見て API ベース URL を自動判定するため、ローカル実行時はそのまま FastAPI に接続されます。

```bash
cd app/frontend
python -m http.server 5500
```

## 🔐 ログイン & ユーザー登録フロー

1. `register.html` でユーザー名 / メールアドレス / パスワード（+任意の誕生日）を入力し、`/api/v1/auth/register` に登録します。
2. `index.html` のログインフォームからメール + パスワードで `/api/v1/auth/login` にリクエストし、アクセストークン / リフレッシュトークンを取得します。
3. 認証成功後は `/api/v1/users/me` を呼び出してプロフィールを表示し、`localStorage` にトークンを保存します。
4. `home.html` ではトークン期限を監視し、必要に応じて `/api/v1/auth/refresh` でアクセストークンを更新します。ログアウト時は `/api/v1/auth/logout` でサーバー側の refresh token も破棄します。

## 📁 主要ディレクトリ

- `app/backend` — FastAPI, SQLAlchemy, 認証 / ユーザー API
- `app/frontend` — バニラ HTML/CSS/JS。`config.js` で API ベース URL を一元管理
- `docs` — API 設計書、DB 設計書など
- `init.sql` — MySQL 用のテーブル/トリガー定義

## ✅ テスト

```bash
pytest app/tests/backend
```

テスト対象が追加されたら同コマンドで回帰確認を行ってください。
