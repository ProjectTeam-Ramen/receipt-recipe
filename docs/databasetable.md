# 現行データベース構造まとめ

FastAPI バックエンド (`app/backend/models/`) に定義されている SQLAlchemy モデルをもとに、現在運用しているテーブルと主なカラム・リレーションを整理した。以下は 2025-12-08 時点の実装に一致する。

## エンティティ一覧

| テーブル | 役割 | 主な関連先 |
| :-- | :-- | :-- |
| `users` | 認証済みユーザー | `refresh_tokens`, `user_foods`, `user_food_transactions`, `user_recipe_history` |
| `refresh_tokens` | リフレッシュトークン管理 | `users` |
| `food_categories` | 食材カテゴリ (野菜/調味料など) | `foods` |
| `foods` | 食材マスタ | `food_categories`, `user_foods`, `user_food_transactions`, `recipe_foods` |
| `user_foods` | ユーザーの在庫アイテム | `users`, `foods`, `user_food_transactions` |
| `user_food_transactions` | 在庫変動の履歴 | `users`, `foods`, `user_foods` |
| `recipes` | レシピ本体（特徴フラグを含む） | `recipe_foods`, `user_recipe_history` |
| `recipe_foods` | レシピと食材の中間 (必要量) | `recipes`, `foods` |
| `user_recipe_history` | ユーザーが作ったレシピ履歴 | `users`, `recipes` |

> ※ 以前の設計書に記載されていた `receipts` や `raw_food_mappings` テーブルは現行コードベースには存在しない。

---

## users

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `user_id` | INT | PK, AUTO_INCREMENT | ユーザーID |
| `username` | VARCHAR(100) | NOT NULL | 表示名 |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | ログイン用メール |
| `password_hash` | VARCHAR(255) | NOT NULL | ハッシュ済みパスワード |
| `birthday` | DATE | NULL | 生年月日 (任意) |
| `created_at` | TIMESTAMP WITH TZ | DEFAULT `CURRENT_TIMESTAMP` | 登録日時 |

リレーション: `refresh_tokens`, `user_foods`, `user_food_transactions`, `user_recipe_history` が `users.user_id` を参照。

## refresh_tokens

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `id` | INT | PK, AUTO_INCREMENT | トークン行ID |
| `token` | VARCHAR(512) | UNIQUE, NOT NULL | リフレッシュトークン文字列 |
| `user_id` | INT | FK (`users.user_id`), NOT NULL | 所有ユーザー |
| `created_at` | DATETIME | DEFAULT `NOW()` | 発行日時 |
| `expires_at` | DATETIME | NOT NULL | 失効日時 |

## food_categories

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `category_id` | INT | PK, AUTO_INCREMENT | カテゴリID |
| `category_name` | VARCHAR(100) | UNIQUE, NOT NULL | カテゴリ名 (例: 野菜/肉/調味料) |

`foods.category_id` が参照。

## foods

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `food_id` | INT | PK, AUTO_INCREMENT | 食材ID |
| `food_name` | VARCHAR(200) | UNIQUE, NOT NULL | 正式名称 (在庫/レシピで統一) |
| `category_id` | INT | FK (`food_categories.category_id`), NOT NULL | 食材カテゴリ |
| `is_trackable` | BOOLEAN | DEFAULT TRUE | 在庫管理対象フラグ |

リレーション: `user_foods`, `user_food_transactions`, `recipe_foods` から参照。

## user_foods

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `user_food_id` | INT | PK, AUTO_INCREMENT | 在庫アイテムID |
| `user_id` | INT | FK (`users.user_id`), NOT NULL | 所有ユーザー |
| `food_id` | INT | FK (`foods.food_id`), NOT NULL | 食材 |
| `quantity_g` | DECIMAL(10,2) | DEFAULT 0 | 現在量 (g) |
| `expiration_date` | DATE | NULL | 消費期限 |
| `purchase_date` | DATE | NULL | 購入日 |
| `status` | ENUM(`unused`,`used`,`deleted`) | DEFAULT `unused` | 在庫状態 (`IngredientStatus`) |

`user_food_transactions.user_food_id` が任意参照。

### status の意味
- `unused` : 在庫中
- `used` : 消費済み
- `deleted` : 手動削除などの無効化

## user_food_transactions

在庫変動を時系列で記録する監査テーブル。

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `transaction_id` | INT | PK, AUTO_INCREMENT | 取引ID |
| `user_id` | INT | FK (`users.user_id`), NOT NULL | 操作ユーザー |
| `food_id` | INT | FK (`foods.food_id`), NOT NULL | 対象食材 |
| `user_food_id` | INT | FK (`user_foods.user_food_id`), NULL | 対応する在庫行 (無い場合もあり) |
| `delta_g` | DECIMAL(10,2) | NOT NULL | 変動量。消費時はマイナス |
| `quantity_after_g` | DECIMAL(10,2) | NOT NULL | 変動後の在庫量 |
| `source_type` | ENUM | NOT NULL | 変動理由 (`InventoryChangeSource`) |
| `source_reference` | VARCHAR(255) | NULL | 外部IDなど |
| `note` | VARCHAR(255) | NULL | 補足 |
| `created_at` | TIMESTAMP WITH TZ | DEFAULT `CURRENT_TIMESTAMP` | 記録日時 |

`source_type` 例: `manual_add`, `manual_consume`, `ocr_import`, `sync`, `adjustment`, `recipe_cook`。

## recipes

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `recipe_id` | INT | PK, AUTO_INCREMENT | レシピID |
| `recipe_name` | VARCHAR(255) | UNIQUE, NOT NULL | レシピ名 |
| `description` | VARCHAR(2000) | NULL | 概要 |
| `instructions` | VARCHAR(4000) | NULL | 手順 |
| `cooking_time` | INT | NULL | 調理時間 (分) |
| `calories` | INT | NULL | カロリー |
| `image_url` | VARCHAR(1000) | NULL | 画像URL |
| *特徴フラグ* | BOOLEAN | DEFAULT FALSE | 下記参照 |

### 特徴フラグ (recipes 内)

| 分類 | カラム | 意味 |
| :-- | :-- | :-- |
| 料理様式 | `is_japanese`, `is_western`, `is_chinese` | 和/洋/中 |
| コース | `is_main_dish`, `is_side_dish`, `is_soup`, `is_dessert` | 主菜/副菜/汁物/デザート |
| タンパク源 | `type_meat`, `type_seafood`, `type_vegetarian`, `type_composite`, `type_other` | 肉/魚/菜食など |
| 味付け | `flavor_sweet`, `flavor_spicy`, `flavor_salty` | 甘味/辛味/塩味 |
| 調理法 | `texture_stewed`, `texture_fried`, `texture_stir_fried` | 煮/揚/炒 |

リレーション: `recipe_foods`, `user_recipe_history`。

## recipe_foods

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `recipe_food_id` | INT | PK, AUTO_INCREMENT | 行ID |
| `recipe_id` | INT | FK (`recipes.recipe_id`), NOT NULL | 親レシピ |
| `food_id` | INT | FK (`foods.food_id`), NOT NULL | 必要食材 |
| `quantity_g` | DECIMAL(10,2) | DEFAULT 0 | 必要量 (g) |

## user_recipe_history

ユーザーが調理した実績を保持し、推薦アルゴリズムの嗜好ベクトル入力として利用。

| カラム | 型 | Key/Default | 説明 |
| :-- | :-- | :-- | :-- |
| `history_id` | INT | PK, AUTO_INCREMENT | 履歴ID |
| `user_id` | INT | FK (`users.user_id`), NOT NULL | ユーザー |
| `recipe_id` | INT | FK (`recipes.recipe_id`), NOT NULL | 料理 |
| `servings` | DECIMAL(6,2) | DEFAULT 1.0 | 何人前を作ったか |
| `calories_total` | INT | NULL | 総カロリー (任意) |
| `cooked_at` | TIMESTAMP WITH TZ | DEFAULT `CURRENT_TIMESTAMP` | 調理日時 |
| `note` | VARCHAR(255) | NULL | メモ |

---

## リレーション概要

- **ユーザー系**: `users` → `refresh_tokens`, `user_foods`, `user_food_transactions`, `user_recipe_history`
- **マスタ系**: `food_categories` ⇄ `foods`
- **在庫系**: `foods` ⇄ `user_foods` ⇄ `user_food_transactions`
- **レシピ系**: `recipes` ⇄ `recipe_foods` ⇄ `foods`、`users` ⇄ `user_recipe_history`

各テーブルは `CASCADE`/`RESTRICT` を適宜設定済み。例えばレシピ削除時は関連する `recipe_foods` と `user_recipe_history` も自動削除、食材カテゴリ削除時は参照する食材があれば `RESTRICT` によってブロックされる。
