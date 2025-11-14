# API設計書

## 概要
Receipt-Recipe APIは、レシート画像からテキストを抽出し、食材情報を解析してレシピを推薦するRESTful APIです。

**バージョン**: 1.0.0  
**ベースURL**: `http://localhost:8000/api/v1`  
**最終更新日**: 2025年11月6日

---

## 目次
1. [認証](#認証)
2. [エンドポイント一覧](#エンドポイント一覧)
3. [データモデル](#データモデル)
4. [エラーレスポンス](#エラーレスポンス)
5. [レート制限](#レート制限)

---

## 認証

### 認証方式
- JWT (JSON Web Token) ベースの認証を使用
- アクセストークンの有効期限: 30分
- リフレッシュトークンの有効期限: 7日

### 認証ヘッダー
```
Authorization: Bearer <access_token>
```

---

## エンドポイント一覧

### 1. 認証関連

#### 1.1 ユーザー登録
```http
POST /auth/register
```

**リクエストボディ**
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

**レスポンス** (201 Created)
```json
{
  "user_id": "integer",
  "username": "string",
  "email": "string",
  "created_at": "datetime"
}
```

#### 1.2 ログイン
```http
POST /auth/login
```

**リクエストボディ**
```json
{
  "email": "string",
  "password": "string"
}
```

**レスポンス** (200 OK)
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

#### 1.3 トークンリフレッシュ
```http
POST /auth/refresh
```

**リクエストボディ**
```json
{
  "refresh_token": "string"
}
```

**レスポンス** (200 OK)
```json
{
  "access_token": "string",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

#### 1.4 ログアウト
```http
POST /auth/logout
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "message": "Successfully logged out"
}
```

---

### 2. レシート処理

#### 2.1 レシート画像アップロード
```http
POST /receipts/upload
```

**ヘッダー**: `Authorization: Bearer <token>`  
**Content-Type**: `multipart/form-data`

**リクエストボディ**
```
file: <image_file> (PNG, JPG, JPEG)
```

**レスポンス** (202 Accepted)
```json
{
  "receipt_id": "integer",
  "status": "processing",
  "uploaded_at": "datetime",
  "message": "Receipt uploaded successfully. Processing started."
}
```

#### 2.2 レシート処理状況確認
```http
GET /receipts/{receipt_id}/status
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "receipt_id": "integer",
  "status": "completed|processing|failed",
  "progress": "integer (0-100)",
  "current_step": "string",
  "updated_at": "datetime"
}
```

#### 2.3 レシート解析結果取得
```http
GET /receipts/{receipt_id}
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "receipt_id": "integer",
  "user_id": "integer",
  "store_name": "string",
  "purchase_date": "date",
  "total_amount": "integer",
  "tax_amount": "integer",
  "items": [
    {
      "item_id": "integer",
      "raw_text": "string",
      "food_id": "integer|null",
      "food_name": "string",
      "quantity": "float",
      "unit": "string",
      "price": "integer",
      "category": "string"
    }
  ],
  "ocr_confidence": "float",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### 2.4 レシート一覧取得
```http
GET /receipts?page=1&limit=20&sort=desc
```

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**
- `page` (integer, default: 1): ページ番号
- `limit` (integer, default: 20, max: 100): 1ページあたりの件数
- `sort` (string, default: "desc"): 並び順 (asc/desc)
- `from_date` (date, optional): 開始日
- `to_date` (date, optional): 終了日

**レスポンス** (200 OK)
```json
{
  "total": "integer",
  "page": "integer",
  "limit": "integer",
  "total_pages": "integer",
  "receipts": [
    {
      "receipt_id": "integer",
      "store_name": "string",
      "purchase_date": "date",
      "total_amount": "integer",
      "items_count": "integer",
      "created_at": "datetime"
    }
  ]
}
```

#### 2.5 レシート削除
```http
DELETE /receipts/{receipt_id}
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "message": "Receipt deleted successfully",
  "receipt_id": "integer"
}
```

---

### 3. 食材管理

#### 3.1 ユーザー所有食材一覧取得
```http
GET /ingredients?category=all&sort_by=expiry_date
```

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**
- `category` (string, optional): カテゴリフィルター
- `sort_by` (string, default: "expiry_date"): ソート基準
- `expiring_soon` (boolean, optional): 賞味期限間近のみ

**レスポンス** (200 OK)
```json
{
  "total": "integer",
  "ingredients": [
    {
      "user_food_id": "integer",
      "food_id": "integer",
      "food_name": "string",
      "category": "string",
      "quantity": "float",
      "unit": "string",
      "expiry_date": "date|null",
      "purchase_date": "date",
      "receipt_id": "integer|null",
      "days_until_expiry": "integer|null",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
}
```

#### 3.2 食材手動追加
```http
POST /ingredients
```

**ヘッダー**: `Authorization: Bearer <token>`

**リクエストボディ**
```json
{
  "food_name": "string",
  "category": "string",
  "quantity": "float",
  "unit": "string",
  "expiry_date": "date|null",
  "purchase_date": "date"
}
```

**レスポンス** (201 Created)
```json
{
  "user_food_id": "integer",
  "food_id": "integer",
  "food_name": "string",
  "category": "string",
  "quantity": "float",
  "unit": "string",
  "expiry_date": "date|null",
  "created_at": "datetime"
}
```

#### 3.3 食材更新
```http
PUT /ingredients/{user_food_id}
```

**ヘッダー**: `Authorization: Bearer <token>`

**リクエストボディ**
```json
{
  "quantity": "float",
  "unit": "string",
  "expiry_date": "date|null"
}
```

**レスポンス** (200 OK)
```json
{
  "user_food_id": "integer",
  "food_name": "string",
  "quantity": "float",
  "unit": "string",
  "expiry_date": "date|null",
  "updated_at": "datetime"
}
```

#### 3.4 食材削除
```http
DELETE /ingredients/{user_food_id}
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "message": "Ingredient deleted successfully",
  "user_food_id": "integer"
}
```

#### 3.5 食材消費記録
```http
POST /ingredients/{user_food_id}/consume
```

**ヘッダー**: `Authorization: Bearer <token>`

**リクエストボディ**
```json
{
  "consumed_quantity": "float",
  "recipe_id": "integer|null"
}
```

**レスポンス** (200 OK)
```json
{
  "user_food_id": "integer",
  "remaining_quantity": "float",
  "consumed_quantity": "float",
  "message": "Ingredient consumption recorded"
}
```

---

### 4. レシピ推薦

#### 4.1 レシピ推薦取得
```http
GET /recipes/recommendations?limit=10&mode=all
```

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**
- `limit` (integer, default: 10, max: 50): 推薦レシピ数
- `mode` (string, default: "all"): 推薦モード
  - `all`: すべての所有食材から
  - `expiring`: 賞味期限間近の食材優先
  - `use_all`: 特定食材を使い切るレシピ
- `include_food_ids` (array[integer], optional): 必須食材ID
- `exclude_allergens` (array[string], optional): 除外アレルゲン

**レスポンス** (200 OK)
```json
{
  "total": "integer",
  "recommendations": [
    {
      "recipe_id": "integer",
      "recipe_name": "string",
      "description": "string",
      "cooking_time": "integer (minutes)",
      "difficulty": "easy|medium|hard",
      "servings": "integer",
      "match_score": "float (0-1)",
      "matched_ingredients": [
        {
          "food_id": "integer",
          "food_name": "string",
          "required_quantity": "float",
          "owned_quantity": "float",
          "unit": "string",
          "is_available": "boolean"
        }
      ],
      "missing_ingredients": [
        {
          "food_id": "integer",
          "food_name": "string",
          "required_quantity": "float",
          "unit": "string"
        }
      ],
      "categories": ["string"],
      "image_url": "string|null",
      "nutrition": {
        "calories": "integer",
        "protein": "float",
        "fat": "float",
        "carbohydrates": "float"
      }
    }
  ]
}
```

#### 4.2 レシピ詳細取得
```http
GET /recipes/{recipe_id}
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "recipe_id": "integer",
  "recipe_name": "string",
  "description": "string",
  "cooking_time": "integer",
  "difficulty": "string",
  "servings": "integer",
  "ingredients": [
    {
      "food_id": "integer",
      "food_name": "string",
      "quantity": "float",
      "unit": "string",
      "is_optional": "boolean"
    }
  ],
  "steps": [
    {
      "step_number": "integer",
      "instruction": "string",
      "duration": "integer|null",
      "image_url": "string|null"
    }
  ],
  "categories": ["string"],
  "tags": ["string"],
  "nutrition": {
    "calories": "integer",
    "protein": "float",
    "fat": "float",
    "carbohydrates": "float",
    "fiber": "float",
    "sodium": "float"
  },
  "allergens": ["string"],
  "image_url": "string|null",
  "source": "string|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### 4.3 レシピ検索
```http
GET /recipes/search?query=パスタ&category=洋食
```

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**
- `query` (string): 検索キーワード
- `category` (string, optional): カテゴリ
- `cooking_time_max` (integer, optional): 最大調理時間
- `difficulty` (string, optional): 難易度
- `page` (integer, default: 1): ページ番号
- `limit` (integer, default: 20, max: 100): 件数

**レスポンス** (200 OK)
```json
{
  "total": "integer",
  "page": "integer",
  "limit": "integer",
  "total_pages": "integer",
  "recipes": [
    {
      "recipe_id": "integer",
      "recipe_name": "string",
      "description": "string",
      "cooking_time": "integer",
      "difficulty": "string",
      "servings": "integer",
      "image_url": "string|null",
      "match_score": "float|null"
    }
  ]
}
```

#### 4.4 お気に入りレシピ追加
```http
POST /recipes/{recipe_id}/favorite
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "message": "Recipe added to favorites",
  "recipe_id": "integer"
}
```

#### 4.5 お気に入りレシピ削除
```http
DELETE /recipes/{recipe_id}/favorite
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "message": "Recipe removed from favorites",
  "recipe_id": "integer"
}
```

#### 4.6 お気に入りレシピ一覧
```http
GET /recipes/favorites
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "total": "integer",
  "favorites": [
    {
      "recipe_id": "integer",
      "recipe_name": "string",
      "description": "string",
      "cooking_time": "integer",
      "difficulty": "string",
      "image_url": "string|null",
      "added_at": "datetime"
    }
  ]
}
```

---

### 5. ユーザー管理

#### 5.1 ユーザー情報取得
```http
GET /users/me
```

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK)
```json
{
  "user_id": "integer",
  "username": "string",
  "email": "string",
  "created_at": "datetime",
  "updated_at": "datetime",
  "preferences": {
    "dietary_restrictions": ["string"],
    "allergens": ["string"],
    "favorite_categories": ["string"]
  },
  "statistics": {
    "total_receipts": "integer",
    "total_ingredients": "integer",
    "favorite_recipes": "integer"
  }
}
```

#### 5.2 ユーザー情報更新
```http
PUT /users/me
```

**ヘッダー**: `Authorization: Bearer <token>`

**リクエストボディ**
```json
{
  "username": "string",
  "email": "string",
  "preferences": {
    "dietary_restrictions": ["string"],
    "allergens": ["string"],
    "favorite_categories": ["string"]
  }
}
```

**レスポンス** (200 OK)
```json
{
  "user_id": "integer",
  "username": "string",
  "email": "string",
  "updated_at": "datetime"
}
```

#### 5.3 パスワード変更
```http
PUT /users/me/password
```

**ヘッダー**: `Authorization: Bearer <token>`

**リクエストボディ**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**レスポンス** (200 OK)
```json
{
  "message": "Password updated successfully"
}
```

#### 5.4 ユーザー削除
```http
DELETE /users/me
```

**ヘッダー**: `Authorization: Bearer <token>`

**リクエストボディ**
```json
{
  "password": "string",
  "confirmation": "DELETE_MY_ACCOUNT"
}
```

**レスポンス** (200 OK)
```json
{
  "message": "User account deleted successfully"
}
```

---

### 6. 食材マスターデータ

#### 6.1 食材カテゴリ一覧取得
```http
GET /master/categories
```

**レスポンス** (200 OK)
```json
{
  "categories": [
    {
      "category_id": "integer",
      "category_name": "string",
      "parent_category_id": "integer|null",
      "description": "string"
    }
  ]
}
```

#### 6.2 食材マスター検索
```http
GET /master/foods?query=トマト
```

**クエリパラメータ**
- `query` (string): 検索キーワード
- `category_id` (integer, optional): カテゴリID
- `limit` (integer, default: 50): 件数

**レスポンス** (200 OK)
```json
{
  "total": "integer",
  "foods": [
    {
      "food_id": "integer",
      "food_name": "string",
      "category_id": "integer",
      "category_name": "string",
      "standard_unit": "string",
      "aliases": ["string"],
      "nutrition_per_100g": {
        "calories": "integer",
        "protein": "float",
        "fat": "float",
        "carbohydrates": "float"
      }
    }
  ]
}
```

---

### 7. OCR処理

#### 7.1 画像前処理のみ実行
```http
POST /ocr/preprocess
```

**ヘッダー**: `Authorization: Bearer <token>`  
**Content-Type**: `multipart/form-data`

**リクエストボディ**
```
file: <image_file>
```

**クエリパラメータ**
- `grayscale` (boolean, default: true): グレースケール変換
- `binarize` (boolean, default: true): 二値化
- `denoise` (boolean, default: true): ノイズ除去
- `correct_skew` (boolean, default: true): 傾き補正

**レスポンス** (200 OK)
```json
{
  "processed_image_url": "string",
  "preprocessing_steps": ["string"],
  "image_quality_score": "float",
  "processing_time": "float"
}
```

#### 7.2 テキスト検出のみ実行
```http
POST /ocr/detect-text
```

**ヘッダー**: `Authorization: Bearer <token>`  
**Content-Type**: `multipart/form-data`

**リクエストボディ**
```
file: <image_file>
```

**レスポンス** (200 OK)
```json
{
  "text_regions": [
    {
      "text": "string",
      "confidence": "float",
      "bounding_box": {
        "x": "integer",
        "y": "integer",
        "width": "integer",
        "height": "integer"
      },
      "line_number": "integer"
    }
  ],
  "total_regions": "integer",
  "average_confidence": "float",
  "processing_time": "float"
}
```

---

### 8. 統計・分析

#### 8.1 食材消費統計
```http
GET /statistics/consumption?period=month
```

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**
- `period` (string, default: "month"): 集計期間 (week/month/year)
- `category` (string, optional): カテゴリフィルター

**レスポンス** (200 OK)
```json
{
  "period": "string",
  "start_date": "date",
  "end_date": "date",
  "total_consumption": {
    "items_count": "integer",
    "total_value": "integer"
  },
  "by_category": [
    {
      "category": "string",
      "items_count": "integer",
      "total_value": "integer",
      "percentage": "float"
    }
  ],
  "waste_analysis": {
    "expired_items_count": "integer",
    "waste_value": "integer",
    "waste_percentage": "float"
  }
}
```

#### 8.2 レシート統計
```http
GET /statistics/receipts?period=month
```

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**
- `period` (string, default: "month"): 集計期間

**レスポンス** (200 OK)
```json
{
  "period": "string",
  "total_receipts": "integer",
  "total_amount": "integer",
  "average_amount": "float",
  "most_visited_stores": [
    {
      "store_name": "string",
      "visit_count": "integer",
      "total_spent": "integer"
    }
  ],
  "spending_trend": [
    {
      "date": "date",
      "amount": "integer"
    }
  ]
}
```

---

## データモデル

### User (ユーザー)
```typescript
{
  user_id: integer
  username: string
  email: string
  password_hash: string
  created_at: datetime
  updated_at: datetime
  is_active: boolean
  preferences: UserPreferences
}
```

### Receipt (レシート)
```typescript
{
  receipt_id: integer
  user_id: integer
  store_name: string
  purchase_date: date
  total_amount: integer
  tax_amount: integer
  image_url: string
  ocr_confidence: float
  processing_status: enum["pending", "processing", "completed", "failed"]
  created_at: datetime
  updated_at: datetime
}
```

### ReceiptDetail (レシート明細)
```typescript
{
  detail_id: integer
  receipt_id: integer
  raw_text: string
  food_id: integer | null
  food_name: string
  quantity: float
  unit: string
  price: integer
  category: string
  confidence: float
}
```

### Food (食材マスター)
```typescript
{
  food_id: integer
  food_name: string
  category_id: integer
  standard_unit: string
  aliases: string[]
  nutrition_per_100g: NutritionInfo
  allergens: string[]
  created_at: datetime
  updated_at: datetime
}
```

### UserFood (ユーザー所有食材)
```typescript
{
  user_food_id: integer
  user_id: integer
  food_id: integer
  quantity: float
  unit: string
  expiry_date: date | null
  purchase_date: date
  receipt_id: integer | null
  created_at: datetime
  updated_at: datetime
}
```

### Recipe (レシピ)
```typescript
{
  recipe_id: integer
  recipe_name: string
  description: string
  cooking_time: integer
  difficulty: enum["easy", "medium", "hard"]
  servings: integer
  steps: RecipeStep[]
  categories: string[]
  tags: string[]
  nutrition: NutritionInfo
  allergens: string[]
  image_url: string | null
  source: string | null
  created_at: datetime
  updated_at: datetime
}
```

### RecipeIngredient (レシピ材料)
```typescript
{
  recipe_ingredient_id: integer
  recipe_id: integer
  food_id: integer
  quantity: float
  unit: string
  is_optional: boolean
}
```

---

## エラーレスポンス

### 標準エラーフォーマット
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object | null",
    "timestamp": "datetime"
  }
}
```

### HTTPステータスコード

| コード | 説明 | 例 |
|--------|------|-----|
| 200 | OK | 正常処理完了 |
| 201 | Created | リソース作成成功 |
| 202 | Accepted | 非同期処理受付 |
| 204 | No Content | 削除成功（レスポンスボディなし） |
| 400 | Bad Request | リクエスト形式エラー |
| 401 | Unauthorized | 認証エラー |
| 403 | Forbidden | 権限エラー |
| 404 | Not Found | リソース未検出 |
| 409 | Conflict | リソース競合 |
| 422 | Unprocessable Entity | バリデーションエラー |
| 429 | Too Many Requests | レート制限超過 |
| 500 | Internal Server Error | サーバーエラー |
| 503 | Service Unavailable | サービス利用不可 |

### エラーコード一覧

| コード | 説明 |
|--------|------|
| `AUTH_001` | 無効な認証情報 |
| `AUTH_002` | トークン期限切れ |
| `AUTH_003` | 無効なトークン |
| `AUTH_004` | 権限不足 |
| `VALIDATION_001` | 必須フィールド欠落 |
| `VALIDATION_002` | 無効な値 |
| `VALIDATION_003` | フォーマットエラー |
| `RESOURCE_001` | リソースが見つかりません |
| `RESOURCE_002` | リソース既に存在 |
| `RESOURCE_003` | リソース削除済み |
| `OCR_001` | 画像処理エラー |
| `OCR_002` | 未サポートの画像形式 |
| `OCR_003` | 画像サイズ超過 |
| `OCR_004` | テキスト検出失敗 |
| `SYSTEM_001` | データベースエラー |
| `SYSTEM_002` | 外部APIエラー |
| `SYSTEM_003` | タイムアウト |

### エラーレスポンス例

**401 Unauthorized**
```json
{
  "error": {
    "code": "AUTH_002",
    "message": "Access token has expired",
    "details": {
      "expired_at": "2025-11-06T10:30:00Z"
    },
    "timestamp": "2025-11-06T11:00:00Z"
  }
}
```

**422 Unprocessable Entity**
```json
{
  "error": {
    "code": "VALIDATION_002",
    "message": "Validation failed",
    "details": {
      "fields": [
        {
          "field": "email",
          "message": "Invalid email format"
        },
        {
          "field": "password",
          "message": "Password must be at least 8 characters"
        }
      ]
    },
    "timestamp": "2025-11-06T11:00:00Z"
  }
}
```

---

## レート制限

### 制限値
- **認証済みユーザー**: 100リクエスト/分
- **未認証ユーザー**: 20リクエスト/分
- **画像アップロード**: 10リクエスト/分

### レスポンスヘッダー
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699267200
```

### レート制限超過時
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "retry_after": 60
    },
    "timestamp": "2025-11-06T11:00:00Z"
  }
}
```

---

## ベストプラクティス

### 1. 認証
- アクセストークンは安全に保管
- トークン期限切れ前にリフレッシュ
- ログアウト時にトークンを破棄

### 2. 画像アップロード
- 推奨サイズ: 最大10MB
- 推奨フォーマット: JPEG, PNG
- 画像は明るく鮮明なものを使用

### 3. エラーハンドリング
- すべてのAPIコールでエラーハンドリングを実装
- リトライロジックの実装（エクスポネンシャルバックオフ）
- 適切なタイムアウト設定

### 4. パフォーマンス
- ページネーションの活用
- 必要なフィールドのみをリクエスト
- キャッシュの活用

### 5. セキュリティ
- HTTPSの使用
- APIキーの適切な管理
- 入力値の検証

---

## バージョニング

### バージョン管理方式
- URLベースのバージョニング: `/api/v1/`, `/api/v2/`
- 後方互換性の維持
- 旧バージョンのサポート期間: 最低6ヶ月
---

### ドキュメント
- API Reference: https://api.receipt-recipe.com/docs
- Swagger UI: https://api.receipt-recipe.com/swagger

---

**最終更新日**: 2025年11月6日
**Version**: 1.0.0
**作成者**: fmt
**変更内容**: 文章の作成

## 更新履歴

**最終更新日**: 2025年11月6日
**Version**: 1.0.0
**作成者**: fmt
**変更内容**: 文章の作成