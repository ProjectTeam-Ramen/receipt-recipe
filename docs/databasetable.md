# データベース設計書

## 1. users (ユーザー)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **user_id** | INT | **PK** | AUTO_INCREMENT | ユーザーID |
| username | VARCHAR(100) | | NOT NULL | ユーザー名 |
| email | VARCHAR(255) | UNI | NOT NULL | メールアドレス |
| password_hash | VARCHAR(255) | | NOT NULL | パスワード（ハッシュ化済） |
| birthday | DATE | | NULL | 生年月日 |
| created_at | TIMESTAMP | | CURRENT_TIMESTAMP | 作成日時 |

## 2. categories (カテゴリ)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **category_id** | INT | **PK** | AUTO_INCREMENT | カテゴリID |
| category_name | VARCHAR(100) | UNI | NOT NULL | カテゴリ名 (野菜, 肉, 調味料等) |

## 3. foods (食材マスタ)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **food_id** | INT | **PK** | AUTO_INCREMENT | 食材ID |
| food_name | VARCHAR(200) | UNI | NOT NULL | 正式な食材名 |
| category_id | INT | FK | NOT NULL | カテゴリID |
| **is_trackable** | TINYINT(1) | | 1 (True) | **管理対象フラグ** (0:管理外, 1:管理対象) |

## 4. user_foods (ユーザー所有食材)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **user_food_id** | INT | **PK** | AUTO_INCREMENT | ID |
| user_id | INT | FK | NOT NULL | ユーザーID |
| food_id | INT | FK | NOT NULL | 食材ID |
| **quantity_g** | DECIMAL(10,2) | | 0.00 | **数量 (単位: g)** |
| expiration_date | DATE | | NULL | 賞味期限 |
| purchase_date | DATE | | NULL | 購入日 |

## 5. recipes (レシピ基本情報)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **recipe_id** | INT | **PK** | AUTO_INCREMENT | レシピID |
| recipe_name | VARCHAR(255) | | NOT NULL | 料理名 |
| description | TEXT | | NULL | 説明 |
| instructions | TEXT | | NULL | 作り方 |
| cooking_time | INT UNSIGNED | | NULL | 調理時間(分) |
| image_url | VARCHAR(1000) | | NULL | 画像URL |
| calories | INT UNSIGNED | | NULL | カロリー(kcal) |

### 5-2. recipes (特徴フラグ)
※ `recipes` テーブルに含まれるフラグカラム一覧

| 分類 | カラム名 | データ型 | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **様式** | is_japanese | TINYINT(1) | 0 | 和食 |
| | is_western | TINYINT(1) | 0 | 洋食 |
| | is_chinese | TINYINT(1) | 0 | 中華 |
| **種類** | is_main_dish | TINYINT(1) | 0 | 主菜 |
| | is_side_dish | TINYINT(1) | 0 | 副菜 |
| | is_soup | TINYINT(1) | 0 | 汁物 |
| | is_dessert | TINYINT(1) | 0 | デザート |
| **食材タイプ** | type_meat | TINYINT(1) | 0 | 肉類 |
| | type_seafood | TINYINT(1) | 0 | 魚介類 |
| | type_vegetarian | TINYINT(1) | 0 | ベジタリアン |
| | type_composite | TINYINT(1) | 0 | 複合 |
| | type_other | TINYINT(1) | 0 | その他 |
| **味覚** | flavor_sweet | TINYINT(1) | 0 | 甘味 |
| | flavor_spicy | TINYINT(1) | 0 | 辛味 |
| | flavor_salty | TINYINT(1) | 0 | 塩味 |
| **調理法** | texture_stewed | TINYINT(1) | 0 | 煮込み |
| | texture_fried | TINYINT(1) | 0 | 揚げ物 |
| | texture_stir_fried| TINYINT(1) | 0 | 炒め物 |

## 6. recipe_foods (レシピ材料)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **recipe_food_id** | INT | **PK** | AUTO_INCREMENT | ID |
| recipe_id | INT | FK | NOT NULL | レシピID |
| food_id | INT | FK | NOT NULL | 食材ID |
| quantity_g | DECIMAL(10,2) | | 0.00 | 必要数量 (単位: g) |

## 7. receipts (レシート)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **receipt_id** | INT | **PK** | AUTO_INCREMENT | レシートID |
| user_id | INT | FK | NOT NULL | ユーザーID |
| store_name | VARCHAR(255) | | NULL | 店名 |
| purchase_datetime | TIMESTAMP | | CURRENT_TIMESTAMP | 購入日時 |

## 8. raw_food_mappings (読み取り食材辞書)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **mapping_id** | INT | **PK** | AUTO_INCREMENT | 辞書ID |
| raw_name | VARCHAR(255) | UNI | NOT NULL | 読み取ったままの文字列 |
| food_id | INT | FK | NULL | 正式な食材ID (紐付け先) |
| status | VARCHAR(50) | | '未処理' | 状態 ('未処理', '処理済' 等) |

## 9. receipt_details (レシート明細)
| カラム名 | データ型 | Key | Default | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| **detail_id** | INT | **PK** | AUTO_INCREMENT | 明細ID |
| receipt_id | INT | FK | NOT NULL | レシートID |
| mapping_id | INT | FK | NOT NULL | 辞書ID |
| price | DECIMAL(10,2) | | 0.00 | 価格 |
| quantity | DECIMAL(10,2) | | 1.00 | 個数 (レシート上の点数) |