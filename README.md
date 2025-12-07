# receipt-recipe
Receipt-Based Food Management and Recipe Recommendation Service

## 🧰 セットアップ

### 1. データベースの準備

MySQL でスキーマを作成し、アプリ用ユーザーに権限を付与します。

```bash
mysql -u root -p < init.sql
```

既存のデータベースを使い回している場合は、最新スキーマとの差分を反映するために `migrations/20231206_add_calories_to_recipes.sql` と `migrations/20231207_add_recipe_cook_source_type.sql` も忘れずに適用してください。

```bash
mysql -u root -p receipt_recipe_db < migrations/20231206_add_calories_to_recipes.sql
mysql -u root -p receipt_recipe_db < migrations/20231207_add_recipe_cook_source_type.sql
mysql -u root -p receipt_recipe_db < migrations/20231208_add_recipe_feature_flags.sql
```

`.env` もしくは環境変数で `DATABASE_URL`（例: `mysql+pymysql://user:password@127.0.0.1/receipt_recipe_db`）を指定してください。未設定の場合は `mysql+pymysql://user:password@db:3306/receipt_recipe_db` に接続します（`docker-compose.override.yml` の `db` サービス）。

> Docker Compose で開発する場合は `docker compose up -d db` を実行すると `MYSQL_DATABASE=receipt_recipe_db` が自動で作成され、`init.sql` が初期化されます。もし既存のボリュームが残っていて `Access denied for user 'user'@'%' to database 'receipt_recipe_db'` が発生する場合は `docker compose down -v` でボリュームを削除したうえで再度 `docker compose up -d db` を実行してください（ボリュームを消すとデータは初期化されます）。

> 既定では SQLite へのフォールバックは行わず、常に MySQL に書き込みます。SQLite を使いたい場合は明示的に `DATABASE_URL=sqlite:///./app.db` などを設定してください。

### 2. バックエンドの起動

```bash
uvicorn app.backend.api.app:app --host 0.0.0.0 --port 8000 --reload
```

FastAPI はホスト OS からは `http://127.0.0.1:8000/api/v1`（またはポートフォワードに応じたアドレス）で到達できます。開発用コンテナ内で `--host 127.0.0.1` のまま起動するとホスト OS から接続できず、フロントエンドが `Failed to fetch` になるので注意してください。

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

## 🍲 レシピデータの追加・更新

- `data/recipes.json` の各オブジェクトは `flags` ブロックを必ず持ち、以下 18 個の特徴フラグ（和/洋/中、主菜/副菜/スープ/デザート、食材タイプ、味・食感）を明示的に `true` / `false` で設定してください。
- 例:

```json
{
	"name": "肉じゃが",
	"cooking_time": 31,
	"calories": 465,
	"ingredients": [...],
	"flags": {
		"is_japanese": true,
		"is_western": false,
		"is_chinese": false,
		"is_main_dish": true,
		"is_side_dish": false,
		"is_soup": false,
		"is_dessert": false,
		"type_meat": true,
		"type_seafood": false,
		"type_vegetarian": false,
		"type_composite": false,
		"type_other": false,
		"flavor_sweet": false,
		"flavor_spicy": false,
		"flavor_salty": false,
		"texture_stewed": false,
		"texture_fried": false,
		"texture_stir_fried": false
	}
}
```

- JSON を保存したら `sync_recipe_master()` を再実行して DB の `recipes` / `recipe_foods` を更新します（`app/backend/services/recipe_loader.py` 参照）。

## ✅ テスト

```bash
pytest app/tests/backend
```

テスト対象が追加されたら同コマンドで回帰確認を行ってください。
