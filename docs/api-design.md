# API設計書

## 概要

Receipt-Recipe APIは、レシート画像を解析して食材を抽出し、それらの食材を使ったレシピを推薦するRESTful APIです。

## ベースURL

```
開発環境: http://localhost:8000
本番環境: https://api.receipt-recipe.com
```

## 認証

JWT (JSON Web Token) ベースの認証を使用します。

### 認証フロー

1. ユーザー登録またはログインでトークンを取得
2. 以降のリクエストで `Authorization: Bearer <token>` ヘッダーを付与

---

## エンドポイント一覧

### 1. 認証系

#### 1.1 ユーザー登録

```
POST /api/v1/auth/register
```

**リクエストボディ**

```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "username": "username"
}
```

**レスポンス (201 Created)**

```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "username": "username",
  "created_at": "2025-11-06T10:00:00Z"
}
```

**エラーレスポンス**

```json
{
  "error": "EMAIL_ALREADY_EXISTS",
  "message": "このメールアドレスは既に登録されています"
}
```

#### 1.2 ログイン

```
POST /api/v1/auth/login
```

**リクエストボディ**

```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**レスポンス (200 OK)**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "user_id": "uuid-string",
    "email": "user@example.com",
    "username": "username"
  }
}
```

#### 1.3 トークン更新

```
POST /api/v1/auth/refresh
```

**リクエストヘッダー**

```
Authorization: Bearer <token>
```

**レスポンス (200 OK)**

```json
{
  "access_token": "new-token-string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### 2. レシート処理系

#### 2.1 レシート画像アップロード

```
POST /api/v1/receipts
```

**リクエスト (multipart/form-data)**

```
receipt_image: <binary-file>
```

**リクエストヘッダー**

```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**レスポンス (201 Created)**

```json
{
  "receipt_id": "uuid-string",
  "user_id": "uuid-string",
  "status": "processing",
  "uploaded_at": "2025-11-06T10:00:00Z",
  "image_url": "/receipts/uuid-string/image.jpg"
}
```

#### 2.2 レシート処理状況取得

```
GET /api/v1/receipts/{receipt_id}
```

**レスポンス (200 OK) - 処理中**

```json
{
  "receipt_id": "uuid-string",
  "status": "processing",
  "progress": {
    "current_step": "ocr_processing",
    "percentage": 50
  },
  "uploaded_at": "2025-11-06T10:00:00Z"
}
```

**レスポンス (200 OK) - 処理完了**

```json
{
  "receipt_id": "uuid-string",
  "user_id": "uuid-string",
  "status": "completed",
  "uploaded_at": "2025-11-06T10:00:00Z",
  "processed_at": "2025-11-06T10:01:30Z",
  "image_url": "/receipts/uuid-string/image.jpg",
  "extracted_items": [
    {
      "item_id": "uuid-string",
      "name": "玉ねぎ",
      "quantity": 2,
      "category": "野菜"
    },
    {
      "item_id": "uuid-string",
      "name": "豚肉",
      "quantity": 300,
      "category": "肉類"
    }
  ]
}

#### 2.4 レシート削除

```
DELETE /api/v1/receipts/{receipt_id}
```

**レスポンス (204 No Content)**

---

### 3. 食材管理系

#### 3.1 食材一覧取得

```
GET /api/v1/ingredients?category=野菜&in_stock=true
```

**クエリパラメータ**

- `category` (optional): カテゴリでフィルタ (`野菜`, `肉類`, `魚介類`, `調味料`, etc.)
- `in_stock` (optional): 在庫ありのみ表示 (true/false)
- `search` (optional): 食材名で検索

**レスポンス (200 OK)**

```json
{
  "ingredients": [
    {
      "ingredient_id": "uuid-string",
      "name": "玉ねぎ",
      "category": "野菜",
      "quantity": 5,
      "unit": "個",
      "purchase_date": "2025-11-06",
      "expiry_date": "2025-11-20",
      "status": "in_stock",
      "receipts": [
        {
          "receipt_id": "uuid-string",
          "purchased_at": "2025-11-06T10:00:00Z"
        }
      ]
    }
  ],
  "total_count": 15
}
```

#### 3.2 食材詳細取得

```
GET /api/v1/ingredients/{ingredient_id}
```

**レスポンス (200 OK)**

```json
{
  "ingredient_id": "uuid-string",
  "name": "玉ねぎ",
  "category": "野菜",
  "quantity": 5,
  "unit": "個",
  "purchase_date": "2025-11-06",
  "expiry_date": "2025-11-20",
  "status": "in_stock",
  "nutritional_info": {
    "calories": 37,
    "protein": 1.0,
    "carbohydrates": 8.8,
    "fat": 0.1
  },
  "storage_tips": "冷暗所で保存してください",
  "usage_history": [
    {
      "used_in_recipe": "カレーライス",
      "used_at": "2025-11-07T18:00:00Z",
      "quantity_used": 2
    }
  ]
}
```

#### 3.3 食材の手動追加

```
POST /api/v1/ingredients
```

**リクエストボディ**

```json
{
  "name": "キャベツ",
  "category": "野菜",
  "quantity": 1,
  "unit": "個",
  "purchase_date": "2025-11-06",
  "expiry_date": "2025-11-13"
}
```

**レスポンス (201 Created)**

```json
{
  "ingredient_id": "uuid-string",
  "name": "キャベツ",
  "category": "野菜",
  "quantity": 1,
  "unit": "個",
  "purchase_date": "2025-11-06",
  "expiry_date": "2025-11-13",
  "status": "in_stock",
  "created_at": "2025-11-06T10:00:00Z"
}
```

#### 3.4 食材の更新

```
PUT /api/v1/ingredients/{ingredient_id}
```

**リクエストボディ**

```json
{
  "quantity": 3,
  "status": "in_stock"
}
```

**レスポンス (200 OK)**

```json
{
  "ingredient_id": "uuid-string",
  "name": "キャベツ",
  "quantity": 3,
  "status": "in_stock",
  "updated_at": "2025-11-06T12:00:00Z"
}
```

#### 3.5 食材の削除

```
DELETE /api/v1/ingredients/{ingredient_id}
```

**レスポンス (204 No Content)**

---

### 4. レシピ推薦系

#### 4.1 レシピ推薦取得

```
POST /api/v1/recipes/recommend
```

**リクエストボディ**

```json
{
  "ingredient_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "preferences": {
    "difficulty": "easy",
    "cooking_time_max": 30,
    "cuisine_type": "japanese",
    "dietary_restrictions": ["vegetarian"]
  },
  "limit": 10
}
```

**パラメータ説明**

- `ingredient_ids`: 使用する食材のID配列 (省略時は全在庫食材を使用)
- `preferences.difficulty`: 難易度 (`easy`, `medium`, `hard`)
- `preferences.cooking_time_max`: 最大調理時間(分)
- `preferences.cuisine_type`: 料理の種類 (`japanese`, `western`, `chinese`, `italian`, etc.)
- `preferences.dietary_restrictions`: 食事制限 (`vegetarian`, `vegan`, `gluten-free`, etc.)
- `limit`: 推薦レシピ数 (デフォルト: 10)

**レスポンス (200 OK)**

```json
{
  "recipes": [
    {
      "recipe_id": "uuid-string",
      "name": "野菜カレー",
      "description": "野菜たっぷりの美味しいカレーです",
      "difficulty": "easy",
      "cooking_time": 30,
      "servings": 4,
      "cuisine_type": "japanese",
      "image_url": "/recipes/uuid-string/image.jpg",
      "match_score": 0.95,
      "matched_ingredients": [
        {
          "ingredient_id": "uuid-1",
          "name": "玉ねぎ",
          "required_quantity": 2,
          "available_quantity": 5,
          "unit": "個"
        }
      ],
      "missing_ingredients": [
        {
          "name": "カレールー",
          "required_quantity": 1,
          "unit": "箱"
        }
      ],
      "nutrition": {
        "calories": 450,
        "protein": 12,
        "carbohydrates": 65,
        "fat": 15
      }
    }
  ],
  "total_count": 15,
  "recommendation_metadata": {
    "algorithm_version": "v1.2",
    "generated_at": "2025-11-06T10:00:00Z"
  }
}
```

#### 4.2 レシピ詳細取得

```
GET /api/v1/recipes/{recipe_id}
```

**レスポンス (200 OK)**

```json
{
  "recipe_id": "uuid-string",
  "name": "野菜カレー",
  "description": "野菜たっぷりの美味しいカレーです",
  "difficulty": "easy",
  "cooking_time": 30,
  "servings": 4,
  "cuisine_type": "japanese",
  "image_url": "/recipes/uuid-string/image.jpg",
  "ingredients": [
    {
      "name": "玉ねぎ",
      "quantity": 2,
      "unit": "個",
      "notes": "薄切りにする"
    },
    {
      "name": "人参",
      "quantity": 1,
      "unit": "本",
      "notes": "乱切りにする"
    }
  ],
  "instructions": [
    {
      "step": 1,
      "description": "玉ねぎと人参を切る",
      "time_estimate": 5,
      "image_url": "/recipes/uuid-string/step1.jpg"
    },
    {
      "step": 2,
      "description": "鍋で野菜を炒める",
      "time_estimate": 10,
      "temperature": "中火"
    }
  ],
  "nutrition": {
    "per_serving": {
      "calories": 450,
      "protein": 12,
      "carbohydrates": 65,
      "fat": 15,
      "fiber": 5,
      "sodium": 800
    }
  },
  "tags": ["簡単", "野菜たっぷり", "カレー"],
  "created_at": "2025-10-01T10:00:00Z",
  "rating": {
    "average": 4.5,
    "count": 120
  }
}
```

#### 4.3 レシピ検索

```
GET /api/v1/recipes/search?q=カレー&cuisine_type=japanese&max_time=30
```

**クエリパラメータ**

- `q`: 検索キーワード
- `cuisine_type`: 料理の種類
- `difficulty`: 難易度
- `max_time`: 最大調理時間
- `page`: ページ番号
- `limit`: 1ページあたりの件数

**レスポンス (200 OK)**

```json
{
  "recipes": [
    {
      "recipe_id": "uuid-string",
      "name": "野菜カレー",
      "difficulty": "easy",
      "cooking_time": 30,
      "image_url": "/recipes/uuid-string/image.jpg",
      "rating": 4.5
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 3,
    "total_items": 25,
    "items_per_page": 10
  }
}
```

#### 4.4 お気に入りレシピに追加

```
POST /api/v1/recipes/{recipe_id}/favorite
```

**レスポンス (200 OK)**

```json
{
  "recipe_id": "uuid-string",
  "favorited": true,
  "favorited_at": "2025-11-06T10:00:00Z"
}
```

#### 4.5 お気に入りレシピ一覧取得

```
GET /api/v1/recipes/favorites
```

**レスポンス (200 OK)**

```json
{
  "recipes": [
    {
      "recipe_id": "uuid-string",
      "name": "野菜カレー",
      "image_url": "/recipes/uuid-string/image.jpg",
      "favorited_at": "2025-11-06T10:00:00Z"
    }
  ],
  "total_count": 5
}
```

---

### 5. OCR処理系 (内部API)

#### 5.1 画像前処理

```
POST /api/v1/ocr/preprocess
```

**リクエスト (multipart/form-data)**

```
image: <binary-file>
denoise_method: "bilateral"
binarize_method: "adaptive"
correct_skew: true
```

**レスポンス (200 OK)**

```json
{
  "processed_image_url": "/ocr/processed/uuid-string.jpg",
  "preprocessing_info": {
    "original_size": [1920, 1080],
    "processed_size": [1920, 1080],
    "detected_skew_angle": -2.5,
    "processing_time_ms": 150
  }
}
```

#### 5.2 テキスト検出

```
POST /api/v1/ocr/detect-text
```

**リクエスト (multipart/form-data)**

```
image: <binary-file>
languages: ["ja", "en"]
```

**レスポンス (200 OK)**

```json
{
  "text_regions": [
    {
      "region_id": 0,
      "bbox": [[100, 50], [300, 50], [300, 80], [100, 80]],
      "text": "スーパーマーケット",
      "confidence": 0.98,
      "center": [200, 65]
    }
  ],
  "total_regions": 25,
  "processing_time_ms": 500
}
```

#### 5.3 文字認識（詳細）

```
POST /api/v1/ocr/recognize-characters
```

**リクエスト**

```json
{
  "image_url": "/receipts/uuid-string/image.jpg",
  "padding": 2
}
```

**レスポンス (200 OK)**

```json
{
  "characters": [
    {
      "char_id": 0,
      "region_id": 0,
      "char": "ス",
      "char_index_in_region": 0,
      "bbox": [100, 50, 115, 80],
      "center": [107.5, 65],
      "confidence": 0.98,
      "image_url": "/ocr/characters/uuid-string/char_0000.png"
    }
  ],
  "total_characters": 150,
  "metadata_url": "/ocr/characters/uuid-string/metadata.json"
}
```

---

### 6. ユーザー管理系

#### 6.1 ユーザー情報取得

```
GET /api/v1/users/me
```

**レスポンス (200 OK)**

```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "username": "username",
  "profile": {
    "display_name": "太郎",
    "avatar_url": "/avatars/uuid-string.jpg",
    "bio": "料理が好きです"
  },
  "preferences": {
    "dietary_restrictions": ["vegetarian"],
    "favorite_cuisines": ["japanese", "italian"],
    "skill_level": "intermediate"
  },
  "statistics": {
    "total_receipts": 50,
    "total_ingredients": 25,
    "favorite_recipes": 15,
    "recipes_cooked": 30
  },
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### 6.2 ユーザー情報更新

```
PUT /api/v1/users/me
```

**リクエストボディ**

```json
{
  "profile": {
    "display_name": "太郎",
    "bio": "料理が大好きです"
  },
  "preferences": {
    "dietary_restrictions": ["vegetarian"],
    "favorite_cuisines": ["japanese", "italian"]
  }
}
```

**レスポンス (200 OK)**

```json
{
  "user_id": "uuid-string",
  "profile": {
    "display_name": "太郎",
    "bio": "料理が大好きです"
  },
  "updated_at": "2025-11-06T10:00:00Z"
}
```

#### 6.3 プロフィール画像アップロード

```
POST /api/v1/users/me/avatar
```

**リクエスト (multipart/form-data)**

```
avatar: <binary-file>
```

**レスポンス (200 OK)**

```json
{
  "avatar_url": "/avatars/uuid-string.jpg",
  "uploaded_at": "2025-11-06T10:00:00Z"
}
```

---

## データモデル

### User

```typescript
{
  user_id: string (UUID)
  email: string
  username: string
  password_hash: string
  profile: {
    display_name?: string
    avatar_url?: string
    bio?: string
  }
  preferences: {
    dietary_restrictions?: string[]
    favorite_cuisines?: string[]
    skill_level?: "beginner" | "intermediate" | "advanced"
  }
  created_at: datetime
  updated_at: datetime
}
```

### Receipt

```typescript
{
  receipt_id: string (UUID)
  user_id: string (UUID)
  status: "processing" | "completed" | "failed"
  image_url: string
  store_name?: string
  purchase_date?: date
  total_amount?: number
  ocr_result?: {
    detected_text: string
    confidence: number
    processing_time_ms: number
  }
  uploaded_at: datetime
  processed_at?: datetime
}
```

### Ingredient

```typescript
{
  ingredient_id: string (UUID)
  user_id: string (UUID)
  name: string
  category: string
  quantity: number
  unit: string
  purchase_date?: date
  expiry_date?: date
  status: "in_stock" | "low_stock" | "out_of_stock" | "expired"
  nutritional_info?: {
    calories: number
    protein: number
    carbohydrates: number
    fat: number
  }
  created_at: datetime
  updated_at: datetime
}
```

### Recipe

```typescript
{
  recipe_id: string (UUID)
  name: string
  description: string
  difficulty: "easy" | "medium" | "hard"
  cooking_time: number (minutes)
  servings: number
  cuisine_type: string
  image_url?: string
  ingredients: Array<{
    name: string
    quantity: number
    unit: string
    notes?: string
  }>
  instructions: Array<{
    step: number
    description: string
    time_estimate?: number
    image_url?: string
  }>
  nutrition: {
    per_serving: {
      calories: number
      protein: number
      carbohydrates: number
      fat: number
    }
  }
  tags: string[]
  rating?: {
    average: number
    count: number
  }
  created_at: datetime
}
```

---

## エラーコード

### HTTPステータスコード

- `200 OK`: リクエスト成功
- `201 Created`: リソース作成成功
- `204 No Content`: 削除成功（レスポンスボディなし）
- `400 Bad Request`: リクエストが不正
- `401 Unauthorized`: 認証が必要
- `403 Forbidden`: 権限がない
- `404 Not Found`: リソースが見つからない
- `409 Conflict`: リソースの競合
- `422 Unprocessable Entity`: バリデーションエラー
- `429 Too Many Requests`: レート制限超過
- `500 Internal Server Error`: サーバーエラー
- `503 Service Unavailable`: サービス利用不可

### エラーレスポンス形式

```json
{
  "error": "ERROR_CODE",
  "message": "エラーの説明",
  "details": {
    "field": "問題のあるフィールド",
    "reason": "詳細な理由"
  },
  "timestamp": "2025-11-06T10:00:00Z",
  "request_id": "uuid-string"
}
```

### エラーコード一覧

#### 認証関連

- `INVALID_CREDENTIALS`: 認証情報が無効
- `TOKEN_EXPIRED`: トークンの有効期限切れ
- `TOKEN_INVALID`: トークンが無効
- `EMAIL_ALREADY_EXISTS`: メールアドレスが既に登録済み
- `USERNAME_ALREADY_EXISTS`: ユーザー名が既に使用済み

#### レシート処理関連

- `RECEIPT_NOT_FOUND`: レシートが見つからない
- `INVALID_IMAGE_FORMAT`: 画像形式が不正
- `IMAGE_TOO_LARGE`: 画像サイズが大きすぎる
- `OCR_PROCESSING_FAILED`: OCR処理に失敗
- `RECEIPT_PROCESSING_TIMEOUT`: 処理タイムアウト

#### 食材関連

- `INGREDIENT_NOT_FOUND`: 食材が見つからない
- `INVALID_CATEGORY`: カテゴリが無効
- `INVALID_QUANTITY`: 数量が無効

#### レシピ関連

- `RECIPE_NOT_FOUND`: レシピが見つからない
- `NO_MATCHING_RECIPES`: マッチするレシピがない
- `INSUFFICIENT_INGREDIENTS`: 食材が不足

---

## レート制限

### 制限値

- 認証済みユーザー: 1000リクエスト/時間
- 未認証ユーザー: 100リクエスト/時間
- レシート画像アップロード: 50リクエスト/日

### レスポンスヘッダー

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1699275600
```

---

## ページネーション

リスト取得APIは以下のクエリパラメータをサポートします。

- `page`: ページ番号 (デフォルト: 1)
- `limit`: 1ページあたりの件数 (デフォルト: 20, 最大: 100)

レスポンスには以下の形式でページネーション情報が含まれます。

```json
{
  "data": [...],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "total_items": 87,
    "items_per_page": 20,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## WebSocket API (将来実装予定)

### レシート処理進捗通知

```
ws://localhost:8000/api/v1/ws/receipts/{receipt_id}/progress
```

**受信メッセージ形式**

```json
{
  "type": "progress_update",
  "receipt_id": "uuid-string",
  "progress": {
    "current_step": "ocr_processing",
    "percentage": 50,
    "message": "テキストを検出中..."
  },
  "timestamp": "2025-11-06T10:00:00Z"
}
```

---

## バージョニング

APIバージョンはURLパスに含めます（例: `/api/v1/`）。

- 現在のバージョン: `v1`
- 非推奨の機能は最低6ヶ月間サポート
- 破壊的変更は新バージョンとしてリリース

---

## セキュリティ

### HTTPS

本番環境では全ての通信をHTTPS経由で行います。

### CORS

許可されたオリジンからのリクエストのみ受け付けます。

```
Access-Control-Allow-Origin: https://receipt-recipe.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
```

### データ検証

- 全てのリクエストボディをPydanticで検証
- SQLインジェクション対策（SQLAlchemy ORM使用）
- XSS対策（適切なエスケープ処理）

---

## 付録

### サポートされる画像形式

- JPEG (.jpg, .jpeg)
- PNG (.png)
- 最大ファイルサイズ: 10MB
- 推奨解像度: 300 DPI以上

### サポートされる言語

OCR処理で以下の言語をサポート:

- 日本語 (ja)
- 英語 (en)

### カテゴリ一覧

食材カテゴリ:

- 野菜
- 果物
- 肉類
- 魚介類
- 乳製品
- 卵
- 穀物
- 調味料
- 加工食品
- その他

料理の種類:

- japanese (和食)
- western (洋食)
- chinese (中華)
- italian (イタリアン)
- french (フレンチ)
- korean (韓国料理)
- thai (タイ料理)
- other (その他)

---

**最終更新日**: 2025年11月6日
**APIバージョン**: v1.0.0
