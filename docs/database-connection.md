# データベース接続ガイド

## 目次

1. [概要](#概要)
2. [データベース構成](#データベース構成)
3. [接続情報](#接続情報)
4. [接続方法](#接続方法)
5. [トラブルシューティング](#トラブルシューティング)

---

## 概要

このプロジェクトでは、MySQL 8.0 を使用して3つのデータベースを管理しています。開発環境では Docker Compose を使用してデータベースサーバーを起動し、Dev Container 内のアプリケーションから接続します。

### 使用技術
- **データベース**: MySQL 8.0
- **接続ライブラリ**: PyMySQL, aiomysql
- **ORM**: SQLAlchemy
- **コンテナ管理**: Docker Compose

---

## データベース構成

プロジェクトでは以下の3つのデータベースを使用します：

| データベース名 | 用途 | 環境変数 |
|---------------|------|----------|
| `ingredients_db` | 食材管理 | `DATABASE_URL_INGREDIENTS` |
| `users_db` | ユーザー情報 | `DATABASE_URL_USERS` |
| `recipes_db` | レシピ情報 | `DATABASE_URL_RECIPES` |

### データベース初期化

データベースは [`init.sql`](../init.sql) スクリプトによって自動的に作成されます。このスクリプトは MySQL コンテナの起動時に実行されます。

---

## 接続情報

### 開発環境

| 項目 | 値 |
|------|-----|
| **ホスト名（Dev Container 内）** | `db` |
| **ホスト名（ホストマシン）** | `localhost` / `127.0.0.1` |
| **ポート** | `3306` |
| **ユーザー名** | `user` |
| **パスワード** | `password` |
| **Root パスワード** | `rootpassword` |

### 接続 URL 形式

```
# 同期接続（PyMySQL）
mysql+pymysql://user:password@db:3306/<database_name>

# 非同期接続（aiomysql）
mysql+aiomysql://user:password@db:3306/<database_name>
```

### 環境変数

以下の環境変数が [`docker-compose.override.yml`](../docker-compose.override.yml) で自動的に設定されます：

```bash
DATABASE_URL_INGREDIENTS=mysql+pymysql://user:password@db:3306/ingredients_db
DATABASE_URL_USERS=mysql+pymysql://user:password@db:3306/users_db
DATABASE_URL_RECIPES=mysql+pymysql://user:password@db:3306/recipes_db
```

---

## 接続方法

### 1. Dev Container 内からの接続

#### A. MySQL CLI クライアント

```bash
# 通常ユーザーで接続
mysql -h db -u user -ppassword

# Root ユーザーで接続
mysql -h db -u root -prootpassword

# 特定のデータベースに直接接続
mysql -h db -u user -ppassword ingredients_db
mysql -h db -u user -ppassword users_db
mysql -h db -u user -ppassword recipes_db
```

**注意**: `-p` オプションの後にスペースを入れずにパスワードを指定してください。

#### B. Python（SQLAlchemy）- 同期接続

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 食材管理データベースに接続
engine = create_engine(
    "mysql+pymysql://user:password@db:3306/ingredients_db",
    echo=True  # SQL をログ出力する場合
)

# セッションの作成
Session = sessionmaker(bind=engine)
session = Session()

# 接続テスト
with engine.connect() as connection:
    result = connection.execute("SELECT DATABASE()")
    print(f"Connected to: {result.fetchone()[0]}")
```

#### C. Python（aiomysql）- 非同期接続

```python
import aiomysql
import asyncio

async def connect_to_db():
    # 接続プールの作成
    pool = await aiomysql.create_pool(
        host='db',
        port=3306,
        user='user',
        password='password',
        db='ingredients_db',
        autocommit=True
    )
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT DATABASE()")
            result = await cursor.fetchone()
            print(f"Connected to: {result[0]}")
    
    pool.close()
    await pool.wait_closed()

# 実行
asyncio.run(connect_to_db())
```

#### D. 環境変数を使用した接続

```python
import os
from sqlalchemy import create_engine

# 環境変数から接続 URL を取得
database_url = os.getenv('DATABASE_URL_INGREDIENTS')

# エンジンの作成
engine = create_engine(database_url)

# 接続テスト
with engine.connect() as connection:
    result = connection.execute("SELECT VERSION()")
    print(f"MySQL version: {result.fetchone()[0]}")
```

---

### 2. ホストマシンからの接続

データベースのポート `3306` がホストマシンにマッピングされているため、ホストから直接接続できます。

#### A. MySQL CLI クライアント

```bash
# ホストマシンのターミナルから
mysql -h 127.0.0.1 -P 3306 -u user -ppassword

# 特定のデータベースに接続
mysql -h localhost -P 3306 -u user -ppassword ingredients_db
```

#### B. GUI ツール（MySQL Workbench, DBeaver など）

**接続設定**:
- **ホスト**: `127.0.0.1` または `localhost`
- **ポート**: `3306`
- **ユーザー名**: `user`
- **パスワード**: `password`
- **データベース**: `ingredients_db`, `users_db`, または `recipes_db`

#### C. Python スクリプト（ホストマシン上）

```python
from sqlalchemy import create_engine

# localhost を使用
engine = create_engine(
    "mysql+pymysql://user:password@localhost:3306/ingredients_db"
)

with engine.connect() as connection:
    result = connection.execute("SELECT DATABASE()")
    print(f"Connected to: {result.fetchone()[0]}")
```

---

### 3. Docker コマンドを使用した直接接続

#### A. コンテナに入って接続

```bash
# コンテナ名を確認
docker ps | grep db

# コンテナに入る
docker exec -it receipt-recipe-dev-db-1 bash

# コンテナ内から MySQL に接続
mysql -u user -ppassword
```

#### B. Docker exec で直接クエリを実行

```bash
# データベース一覧を表示
docker exec -it receipt-recipe-dev-db-1 mysql -u user -ppassword -e "SHOW DATABASES;"

# 特定のクエリを実行
docker exec -it receipt-recipe-dev-db-1 mysql -u user -ppassword ingredients_db -e "SHOW TABLES;"

# データベースのバックアップ
docker exec receipt-recipe-dev-db-1 mysqldump -u user -ppassword ingredients_db > backup.sql

# バックアップからリストア
docker exec -i receipt-recipe-dev-db-1 mysql -u user -ppassword ingredients_db < backup.sql
```

---

## データベース管理操作

### データベースの作成確認

```bash
# Dev Container 内から
mysql -h db -u user -ppassword -e "SHOW DATABASES;"

# ホストマシンから
mysql -h localhost -u user -ppassword -e "SHOW DATABASES;"
```

期待される出力:
```
+--------------------+
| Database           |
+--------------------+
| information_schema |
| ingredients_db     |
| mysql              |
| performance_schema |
| recipes_db         |
| sys                |
| users_db           |
+--------------------+
```

### ユーザー権限の確認

```bash
mysql -h db -u root -prootpassword -e "SELECT user, host FROM mysql.user;"
```

### テーブルの確認

```bash
# 特定のデータベースのテーブル一覧
mysql -h db -u user -ppassword ingredients_db -e "SHOW TABLES;"
```

### データのエクスポート

```bash
# 特定のデータベースをエクスポート
docker exec receipt-recipe-dev-db-1 mysqldump -u user -ppassword ingredients_db > ingredients_backup.sql

# すべてのデータベースをエクスポート
docker exec receipt-recipe-dev-db-1 mysqldump -u user -ppassword --all-databases > all_databases_backup.sql
```

### データのインポート

```bash
# バックアップからインポート
docker exec -i receipt-recipe-dev-db-1 mysql -u user -ppassword ingredients_db < ingredients_backup.sql
```

---

## トラブルシューティング

### データベースに接続できない

#### 1. データベースコンテナの状態を確認

```bash
# コンテナが起動しているか確認
docker ps | grep db

# コンテナのログを確認
docker logs receipt-recipe-dev-db-1

# コンテナのヘルスチェック状態を確認
docker inspect receipt-recipe-dev-db-1 | grep -A 10 Health
```

#### 2. ネットワーク接続を確認

```bash
# ネットワークの確認
docker network inspect receipt-recipe-dev

# ポートが開いているか確認
netstat -an | grep 3306
```

#### 3. MySQL サービスの状態を確認

```bash
# ヘルスチェックを手動で実行
docker exec receipt-recipe-dev-db-1 mysqladmin ping -h localhost

# MySQL プロセスの確認
docker exec receipt-recipe-dev-db-1 ps aux | grep mysql
```

### データベースが初期化されない

#### init.sql が実行されているか確認

```bash
# コンテナのログを確認
docker logs receipt-recipe-dev-db-1 | grep init.sql

# 初期化スクリプトの存在を確認
ls -la init.sql
```

#### データベースを再作成

```bash
# コンテナとボリュームを削除
docker-compose down -v

# 再度起動
docker-compose up -d

# ログを確認
docker-compose logs db
```

### 接続タイムアウトエラー

```bash
# データベースの準備が完了するまで待機
docker-compose up -d db
sleep 30  # 30秒待機
```

または、Python コードでリトライロジックを実装：

```python
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

def connect_with_retry(database_url, max_retries=5, delay=5):
    for i in range(max_retries):
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                print("Database connection successful")
                return engine
        except OperationalError as e:
            if i < max_retries - 1:
                print(f"Connection failed, retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise e

engine = connect_with_retry("mysql+pymysql://user:password@db:3306/ingredients_db")
```

### 認証エラー

```bash
# ユーザーとパスワードを確認
docker exec -it receipt-recipe-dev-db-1 mysql -u root -prootpassword -e "SELECT user, host FROM mysql.user;"

# パスワードをリセット（必要な場合）
docker exec -it receipt-recipe-dev-db-1 mysql -u root -prootpassword -e "ALTER USER 'user'@'%' IDENTIFIED BY 'password'; FLUSH PRIVILEGES;"
```

### ポート競合エラー

```bash
# 既存のポート使用状況を確認
sudo lsof -i :3306

# 競合しているプロセスを停止
sudo systemctl stop mysql  # ホストマシンの MySQL を停止

# または、docker-compose.override.yml でポートを変更
# ports:
#   - "3307:3306"
```

---

## 参考リンク

- [MySQL 8.0 Documentation](https://dev.mysql.com/doc/refman/8.0/en/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [aiomysql Documentation](https://aiomysql.readthedocs.io/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

## 関連ファイル

- [`docker-compose.override.yml`](../docker-compose.override.yml): 開発環境のデータベース設定
- [`docker-compose.prod.yml`](../docker-compose.prod.yml): 本番環境のデータベース設定
- [`init.sql`](../init.sql): データベース初期化スクリプト
- [`.env.example`](../.env.example): 環境変数のテンプレート