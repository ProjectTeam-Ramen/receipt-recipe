# データベース接続ガイド

## 目次

1. [概要](#概要)  
2. [データベース構成](#データベース構成)  
3. [接続情報](#接続情報)  
4. [接続方法（例）](#接続方法例)  
5. [トラブルシューティング（短縮）](#トラブルシューティング短縮)

---

## 概要

このプロジェクトでは MySQL 8.0 を使用し、アプリケーションの要件に合わせて **9つのデータベース** を分離して運用します。重要な機能として、OCRで読み取った不正確な文字列（例: 「こしひか」）を正規化された食材マスター（例: 「お米」）に紐付けるための中間辞書テーブル（raw_food_mappings）を用意しています。`init.sql` によって起動時に9つのデータベースが自動作成されます。

**使用技術:**
- MySQL 8.0
- 接続ライブラリ: PyMySQL / aiomysql
- ORM: SQLAlchemy
- コンテナ: Docker Compose

---

## データベース構成

以下の9データベースを用意します（それぞれ `*_db` の名前で作成済み）。

| No. | データベース名 | テーブル名 | 目的 |
|-----|---------------|-----------|------|
| 1 | `users_db` | `users` | ユーザー情報（user_id, username, email, password_hash, birthday, created_at） |
| 2 | `food_categories_db` | `food_categories` | 食材カテゴリ（category_id, category_name） |
| 3 | `foods_db` | `foods` | 食材マスター（food_id, food_name, category_id, default_unit） |
| 4 | `user_foods_db` | `user_foods` | ユーザー所有食材/冷蔵庫（user_food_id, user_id, food_id, quantity, unit, expiration_date, purchase_date） |
| 5 | `recipes_db` | `recipes` | レシピ基本情報（recipe_id, recipe_name, description, instructions, cooking_time, image_url） |
| 6 | `recipe_foods_db` | `recipe_foods` | レシピ材料（recipe_food_id, recipe_id, food_id, quantity, unit） |
| 7 | `receipts_db` | `receipts` | レシート情報（receipt_id, user_id, store_name, purchase_datetime） |
| 8 | `raw_food_mappings_db` | `raw_food_mappings` | **読み取り食材辞書**（mapping_id, raw_name, food_id, status）※OCR文字列とfoodsを紐付ける中間テーブル |
| 9 | `receipt_details_db` | `receipt_details` | レシート明細（detail_id, receipt_id, mapping_id, price, quantity） |

### 重要: raw_food_mappings_db の役割

**最重要要件**: OCRによる不正確な文字列（例：「こしひか」「ﾆﾝｼﾞﾝ」）を、システムが管理する正規化された食材マスター（foods テーブル）に紐付けるための辞書データベースです。

**カラム構成:**
- `mapping_id`: 主キー（自動連番）
- `raw_name`: OCRで読み取った文字列（重複不可、例: "こしひか", "ﾆﾝｼﾞﾝ"）
- `food_id`: 外部キー（foods テーブルへの参照、**NULL許可**）
- `status`: 処理状態（例: '未処理', '処理済'）

**データフロー:**
1. レシートOCR → `raw_name` を `raw_food_mappings` に登録
2. 管理者または自動マッチングロジックで `food_id` を紐付け
3. `receipt_details` は `mapping_id` を参照し、間接的に `foods` にアクセス

---

## 接続情報

**開発環境（Dev Container / Docker Compose）での接続情報:**

| 項目 | 値 |
|------|-----|
| ホスト（コンテナ内） | `db` |
| ホスト（ホストマシン） | `localhost` / `127.0.0.1` |
| ポート | `3306` |
| ユーザー | `user` |
| パスワード | `password` |
| root パスワード | `rootpassword` |

**接続 URL の形式:**

```bash
# 同期（PyMySQL）
mysql+pymysql://user:password@db:3306/<database_name>

# 非同期（aiomysql）
mysql+aiomysql://user:password@db:3306/<database_name>
```

**環境変数（9つのデータベース）:**

```bash
DATABASE_URL_USERS=mysql+pymysql://user:password@db:3306/users_db
DATABASE_URL_FOOD_CATEGORIES=mysql+pymysql://user:password@db:3306/food_categories_db
DATABASE_URL_FOODS=mysql+pymysql://user:password@db:3306/foods_db
DATABASE_URL_USER_FOODS=mysql+pymysql://user:password@db:3306/user_foods_db
DATABASE_URL_RECIPES=mysql+pymysql://user:password@db:3306/recipes_db
DATABASE_URL_RECIPE_FOODS=mysql+pymysql://user:password@db:3306/recipe_foods_db
DATABASE_URL_RECEIPTS=mysql+pymysql://user:password@db:3306/receipts_db
DATABASE_URL_RAW_FOOD_MAPPINGS=mysql+pymysql://user:password@db:3306/raw_food_mappings_db
DATABASE_URL_RECEIPT_DETAILS=mysql+pymysql://user:password@db:3306/receipt_details_db
```

これらの環境変数は `docker-compose.override.yml`、`docker-compose.prod.yml`、`.env.example` で設定されています。

---

## 接続方法（例）

### 1. MySQL CLI（コンテナ内から接続）

```bash
# users_db に接続
mysql -h db -u user -ppassword users_db

# raw_food_mappings_db に接続
mysql -h db -u user -ppassword raw_food_mappings_db

# 9つのデータベース一覧を確認
mysql -h db -u user -ppassword -e "SHOW DATABASES;"
```

### 2. SQLAlchemy（同期）接続テスト

```python
from sqlalchemy import create_engine

# foods_db に接続
engine = create_engine("mysql+pymysql://user:password@db:3306/foods_db")
with engine.connect() as conn:
    result = conn.execute("SELECT DATABASE()").fetchone()
    print(f"接続中のデータベース: {result[0]}")
```

### 3. aiomysql（非同期）接続テスト

```python
import aiomysql
import asyncio

async def test_connection():
    # raw_food_mappings_db に接続
    pool = await aiomysql.create_pool(
        host="db",
        port=3306,
        user="user",
        password="password",
        db="raw_food_mappings_db"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT DATABASE()")
            result = await cur.fetchone()
            print(f"接続中のデータベース: {result[0]}")
    pool.close()
    await pool.wait_closed()

asyncio.run(test_connection())
```

### 4. 全9データベースへの接続確認スクリプト

```python
from sqlalchemy import create_engine

databases = [
    "users_db",
    "food_categories_db",
    "foods_db",
    "user_foods_db",
    "recipes_db",
    "recipe_foods_db",
    "receipts_db",
    "raw_food_mappings_db",
    "receipt_details_db"
]

for db_name in databases:
    try:
        engine = create_engine(f"mysql+pymysql://user:password@db:3306/{db_name}")
        with engine.connect() as conn:
            result = conn.execute("SELECT DATABASE()").fetchone()
            print(f"✓ {db_name}: 接続成功")
    except Exception as e:
        print(f"✗ {db_name}: 接続失敗 - {e}")
```

---

## トラブルシューティング（要点）

### データベースが作成されない場合

1. **init.sql の実行確認:**
   ```bash
   docker-compose logs db
   ```

2. **データベース一覧の確認（9つあるか確認）:**
   ```bash
   mysql -h db -u user -ppassword -e "SHOW DATABASES;"
   ```
   
   以下の9つが表示されるはずです:
   - users_db
   - food_categories_db
   - foods_db
   - user_foods_db
   - recipes_db
   - recipe_foods_db
   - receipts_db
   - raw_food_mappings_db
   - receipt_details_db

3. **ボリュームのリセット（初期化）:**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

### 接続エラーの確認

```bash
# データベースコンテナの状態確認
docker-compose ps

# データベースコンテナのヘルスチェック
docker-compose exec db mysqladmin ping -h localhost -u user -ppassword

# 権限の確認
docker-compose exec db mysql -u user -ppassword -e "SHOW GRANTS FOR 'user'@'%';"
```

---

## 重要な注意事項

### raw_food_mappings_db の運用について

`raw_food_mappings_db` はOCRの曖昧な文字列を `foods_db`（食材マスター）に紐付けるための中核データベースです。

**推奨運用フロー:**

1. **レシート読み取り時:**
   - OCRで読み取った文字列を `raw_name` として登録
   - `food_id` は NULL、`status` は '未処理' で登録

2. **マッピング処理:**
   - 管理画面で未処理の `raw_name` を表示
   - 管理者が適切な `food_id` を選択して紐付け
   - または自動マッチングロジック（類似度検索など）で紐付け
   - 紐付け完了後、`status` を '処理済' に更新

3. **レシート明細での参照:**
   - `receipt_details` は `mapping_id` を参照
   - `mapping_id` → `raw_food_mappings` → `food_id` → `foods` の順で食材情報を取得

**例: 未マッピング食材の検索**
```sql
SELECT * FROM raw_food_mappings 
WHERE food_id IS NULL 
AND status = '未処理';
```

---

## 関連ファイル

- `docker-compose.override.yml` - 開発環境の設定（データベースの環境変数）
- `docker-compose.prod.yml` - 本番環境の設定（データベースの環境変数）
- `init.sql` - **9データベースの作成と権限付与**
- `.env.example` - 環境変数のサンプル（データベース分）

---

**最終更新:** 2025年10月24日