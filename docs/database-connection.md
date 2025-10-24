# データベース接続ガイド

## 目次

1. [概要](#概要)  
2. [データベース構成（9つ）](#データベース構成9つ)  
3. [接続情報](#接続情報)  
4. [接続方法（例）](#接続方法例)  
5. [トラブルシューティング（短縮）](#トラブルシューティング短縮)

---

## 概要

このプロジェクトでは MySQL 8.0 を使用し、アプリケーションの要件に合わせて「9つのデータベース」を分離して運用します。重要な機能として、OCRで読み取った不正確な文字列（例: 「こしひか」）を正規化された食材マスター（例: 「お米」）に紐付けるための中間辞書テーブル（raw_food_mappings）を用意しています。init.sql によって起動時に9つのデータベースが作成されます。

使用技術
- MySQL 8.0
- 接続ライブラリ: PyMySQL / aiomysql
- ORM: SQLAlchemy
- コンテナ: Docker Compose

---

## データベース構成（9つ）

以下の9データベースを用意します（それぞれ `*_db` の名前で作成済み）。

1. users_db — ユーザー情報（users テーブル）
2. food_categories_db — 食材カテゴリ（food_categories テーブル）
3. foods_db — 食材マスター（foods テーブル）
4. user_foods_db — ユーザー所有食材（user_foods テーブル）
5. recipes_db — レシピ（recipes テーブル）
6. recipe_foods_db — レシピ材料（recipe_foods テーブル）
7. receipts_db — レシート（receipts テーブル）
8. raw_food_mappings_db — 読み取り食材辞書（raw_food_mappings テーブル）※OCR文字列とfoodsを紐付ける中間テーブル
9. receipt_details_db — レシート明細（receipt_details テーブル）

各テーブルのスキーマ（要件）はプロジェクト仕様に従います。特に raw_food_mappings は「raw_name」「food_id（NULL許可）」「status」を保持し、OCR → 正規化の肝となります。

---

## 接続情報

開発環境（Dev Container / Docker Compose）での接続情報:

- ホスト（コンテナ内）: `db`
- ホスト（ホストマシン）: `localhost` / `127.0.0.1`
- ポート: `3306`
- ユーザー: `user`
- パスワード: `password`
- root パスワード: `rootpassword`

接続 URL の形式:

# 同期（PyMySQL）
mysql+pymysql://user:password@db:3306/<database_name>

# 非同期（aiomysql）
mysql+aiomysql://user:password@db:3306/<database_name>

環境変数（docker-compose.override.yml や .env.example で使う例）:

- DATABASE_URL_USERS=mysql+pymysql://user:password@db:3306/users_db  
- DATABASE_URL_FOOD_CATEGORIES=mysql+pymysql://user:password@db:3306/food_categories_db  
- DATABASE_URL_FOODS=mysql+pymysql://user:password@db:3306/foods_db  
- DATABASE_URL_USER_FOODS=mysql+pymysql://user:password@db:3306/user_foods_db  
- DATABASE_URL_RECIPES=mysql+pymysql://user:password@db:3306/recipes_db  
- DATABASE_URL_RECIPE_FOODS=mysql+pymysql://user:password@db:3306/recipe_foods_db  
- DATABASE_URL_RECEIPTS=mysql+pymysql://user:password@db:3306/receipts_db  
- DATABASE_URL_RAW_FOOD_MAPPINGS=mysql+pymysql://user:password@db:3306/raw_food_mappings_db  
- DATABASE_URL_RECEIPT_DETAILS=mysql+pymysql://user:password@db:3306/receipt_details_db

---

## 接続方法（短い例）

1. MySQL CLI（コンテナ内）
```bash
mysql -h db -u user -ppassword users_db
```

2. SQLAlchemy（同期）接続テスト
```python
from sqlalchemy import create_engine
engine = create_engine("mysql+pymysql://user:password@db:3306/foods_db")
with engine.connect() as conn:
    print(conn.execute("SELECT DATABASE()").fetchone())
```

3. aiomysql（非同期）接続テスト
```python
import aiomysql, asyncio
async def test():
    pool = await aiomysql.create_pool(host="db", port=3306, user="user", password="password", db="raw_food_mappings_db")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT DATABASE()")
            print(await cur.fetchone())
    pool.close(); await pool.wait_closed()
asyncio.run(test())
```

---

## トラブルシューティング（要点）

- init.sql が実行されない場合はコンテナ起動ログを確認: `docker-compose logs db`  
- データベース一覧確認:
```bash
mysql -h db -u user -ppassword -e "SHOW DATABASES;"
```
- コンテナ名確認・実行中プロセス確認などは通常の Docker コマンドを使用してください。

---

## 重要な注意

- raw_food_mappings（読み取り食材辞書）は OCR の曖昧な文字列を foods（食材マスター）に紐付けるための中核です。アプリ側でこのテーブルを参照し、未マッピング(raw_name が存在してかつ food_id が NULL) を管理者や自動マッチングロジックで解決するフローを推奨します。

---

関連ファイル:
- `docker-compose.override.yml`  
- `docker-compose.prod.yml`  
- `init.sql`（9データベースの作成と権限付与を含む）  
- `.env.example`