# API設計書

## 概要
Receipt-Recipe API は、レシート画像からテキストを抽出し（OCR）、抽出された食材情報をユーザーの所有食材と紐付け、最適なレシピを推薦する RESTful API です。

- バージョン: 1.1.0
- ベースURL: `https://api.example.com/api/v1`
- 最終更新日: 2025-11-28

注意: 本設計書ではすべての日時を ISO 8601 (UTC) 形式（例: `2025-11-06T11:00:00Z`）で扱い、フィールド名は snake_case で統一します。

---

## 目次
1. 認証
2. エンドポイント一覧
3. データモデル
4. エラーレスポンス
5. レート制限
6. 運用・ベストプラクティス
7. 変更履歴

---

## 1.認証

### 1.1 認証方式
- JWT (アクセストークン) + Refresh Token
- access_token 有効期限: 30 分
- refresh_token 有効期限: 7 日（サーバ側で失効管理推奨）

### 1.2 認証ヘッダー
```
Authorization: Bearer <access_token>
```

### 1.3 認証関連の追加エンドポイント（必須）
- POST /auth/register — ユーザー登録
- POST /auth/login — ログイン（email/password → access/refresh）
- POST /auth/refresh — refresh_token で access_token を再発行
- POST /auth/logout — トークン無効化（ログアウト）
- POST /auth/password-reset — パスワードリセット要求（メール送信）
- POST /auth/password-reset/confirm — リセット確定（token + new_password）
- POST /auth/verify-email — メール確認（token）
- POST /auth/resend-verification — 確認メール再送

各エンドポイントのボディ例やステータスは後述のエンドポイント一覧で示します。

---

## 2. エンドポイント一覧（主なもの）

注意: 各エンドポイントの認可要件（role: user/admin/owner）を明記しています。成功レスポンスでは可能な限り実データ例を用いて型を明示しています。

### 認証関連（詳細例）

#### POST /auth/register
- 説明: 新規ユーザー登録
- リクエスト:
```json
{
  "username": "taro",
  "email": "taro@example.com",
  "password": "Pa$$w0rd!"
}
```
- レスポンス (201 Created):
```json
{
  "user_id": 123,
  "username": "taro",
  "email": "taro@example.com",
  "created_at": "2025-11-28T10:00:00Z"
}
```

#### POST /auth/login
- リクエスト:
```json
{
  "email": "taro@example.com",
  "password": "Pa$$w0rd!"
}
```
- レスポンス (200 OK):
```json
{
  "access_token": "ey...",
  "refresh_token": "rft...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

#### POST /auth/password-reset
- 説明: パスワードリセットのメール送信要求
- リクエスト:
```json
{ "email": "taro@example.com" }
```
- レスポンス (200 OK):
```json
{ "message": "Password reset email sent if account exists" }
```

#### POST /auth/password-reset/confirm
- リクエスト:
```json
{ "token": "abc123", "new_password": "NewPa$$w0rd" }
```

---

### 2.1 レシート処理

#### POST /receipts/upload
- 説明: レシート画像をアップロードして非同期解析を開始
- 認可: user
- Content-Type: multipart/form-data
- リクエストフォームフィールド:
  - file: 画像ファイル (jpeg/png)
  - callback_url: (任意) 解析完了時に通知する URL（Webhook）

- レスポンス (202 Accepted):
```json
{
  "receipt_id": 987,
  "status": "processing",
  "uploaded_at": "2025-11-28T10:05:00Z",
  "message": "Receipt uploaded. Processing started."
}
```

Notes:
- 大きなファイルは presigned URL を使った直接ストレージアップロードを推奨します。実装例: GET /receipts/upload-url → クライアントが署名付き URL に PUT。

#### GET /receipts/{receipt_id}/status
- 認可: owner (receipt 所有者)
- レスポンス (200 OK):
```json
{
  "receipt_id": 987,
  "status": "completed",
  "progress": 100,
  "current_step": "ocr_completed",
  "updated_at": "2025-11-28T10:06:30Z"
}
```

#### GET /receipts/{receipt_id}
- 認可: owner
- レスポンス (200 OK):（数値は数値、日時は ISO 文字列に修正）
```json
{
  "receipt_id": 987,
  "user_id": 123,
  "store_name": "Sato Mart",
  "purchase_date": "2025-11-27",
  "total_amount": 1250,
  "tax_amount": 100,
  "items": [
    {
      "item_id": 1,
      "raw_text": "トマト 3個 300円",
      "food_id": 10,
      "food_name": "トマト",
      "quantity": 3,
      "unit": "個",
      "price": 300,
      "category": "野菜",
      "confidence": 0.92
    }
  ],
  "ocr_confidence": 0.89,
  "image_url": "https://cdn.example.com/receipts/987/original.jpg",
  "created_at": "2025-11-28T10:05:00Z",
  "updated_at": "2025-11-28T10:06:30Z"
}
```

#### GET /receipts/{receipt_id}/image
- 説明: 解析済み/オリジナル画像を取得
- 認可: owner
- 返却: 302 でストレージの署名付き URL へリダイレクト、または直接バイナリ（要設計）

#### 明細編集
PATCH /receipts/{receipt_id}/items/{detail_id}
- 説明: OCR 結果の手動修正を行う（部分更新）
- リクエスト例:
```json
{ "raw_text": "トマト 2個", "food_id": 10, "quantity": 2, "price": 200 }
```

---

### 2.2 非同期通知 / Webhook
- 解析完了をプッシュしたいクライアント向けに、`callback_url`（receipt upload の任意パラメータ）を受け付けます。サーバは完了時に POST で JSON を通知します。
- Webhook 形式（例）:
```json
{ "receipt_id": 987, "status": "completed", "updated_at": "2025-11-28T10:06:30Z" }
```

セキュリティ: Webhook は署名 (HMAC) を付与し、受信側で検証できるようにすることを推奨。

---

### 2.3 レシート一覧
GET /receipts
- クエリ: page, limit, sort, from_date, to_date
- レスポンスに pagination の meta と links を含めます:
```json
{
  "meta": { "total": 120, "page": 1, "limit": 20, "total_pages": 6 },
  "links": { "self": "/receipts?page=1", "next": "/receipts?page=2" },
  "receipts": [ ... ]
}
```

DELETE /receipts/{receipt_id}
- デフォルトは 204 No Content を推奨。ただしクライアントに削除 id を返す設計の場合は 200 + body を選べます。どちらかに統一してください。

---

### 3. 食材管理（主要）
GET /ingredients — 一覧（フィルタ/ソート）
POST /ingredients — 手動追加
PATCH /ingredients/{user_food_id} — 部分更新（消費記録は専用 endpoint も残す）
DELETE /ingredients/{user_food_id}

POST /ingredients/{user_food_id}/consume — 消費記録（履歴を保存）

レスポンス例（GET /ingredients）:
```json
{
  "total": 3,
  "ingredients": [
    {
      "user_food_id": 321,
      "food_id": 10,
      "food_name": "トマト",
      "category": "野菜",
      "quantity": 2.0,
      "unit": "個",
      "expiry_date": "2025-12-01",
      "purchase_date": "2025-11-27",
      "receipt_id": 987,
      "days_until_expiry": 3,
      "created_at": "2025-11-27T09:00:00Z",
      "updated_at": "2025-11-28T10:10:00Z"
    }
  ]
}
```

---

### 4. レシピ推薦・検索
GET /recipes/recommendations — 推薦（mode: all/expiring/use_all）
GET /recipes/{recipe_id} — レシピ詳細
GET /recipes/search — 検索（query, category, cooking_time_max, difficulty, page, limit）
POST /recipes/{recipe_id}/favorite — お気に入り追加
DELETE /recipes/{recipe_id}/favorite — お気に入り削除
GET /recipes/favorites — 一覧

レスポンス例（recommendations）: 主要フィールドは実値で表記
```json
{
  "total": 1,
  "recommendations": [
    {
      "recipe_id": 555,
      "recipe_name": "トマトと卵の炒め物",
      "description": "簡単で早い",
      "cooking_time": 15,
      "difficulty": "easy",
      "servings": 2,
      "match_score": 0.85,
      "matched_ingredients": [ { "food_id": 10, "food_name": "トマト", "required_quantity": 2, "owned_quantity": 2, "unit": "個", "is_available": true } ],
      "missing_ingredients": [],
      "categories": ["和食"],
      "image_url": null
    }
  ]
}
```

---

### 5. ユーザー管理
GET /users/me — 自分情報取得
PUT /users/me — 情報更新
PUT /users/me/password — パスワード変更
DELETE /users/me — アカウント削除（確認フラグ必須）

レスポンス例: GET /users/me
```json
{
  "user_id": 123,
  "username": "taro",
  "email": "taro@example.com",
  "created_at": "2025-11-01T08:00:00Z",
  "updated_at": "2025-11-20T12:00:00Z",
  "preferences": { "dietary_restrictions": [], "allergens": ["peanut"], "favorite_categories": ["和食"] },
  "statistics": { "total_receipts": 42, "total_ingredients": 120, "favorite_recipes": 8 }
}
```

---

### 6. マスター管理（管理者用）
GET /master/categories
GET /master/foods
（管理者）POST/PUT/DELETE /master/foods/{food_id}
POST /master/foods/import — CSV/Bulk インポート

---

### 7. OCR 関連
POST /ocr/preprocess — 前処理
POST /ocr/detect-text — テキスト検出
GET /receipts/{receipt_id}/raw-ocr — OCR 生データ取得（編集用）

レスポンスは confidence と bounding_box（x,y,width,height）を含めます。

---

### 8. その他運用系
GET /health — ヘルスチェック（OK / 各依存状態）
GET /metrics — Prometheus 互換のメトリクス（必要に応じて）
GET /users/me/receipts/export?format=csv — データエクスポート

---

## 3. データモデル（要点）
（前節から継承。主要フィールドは snake_case、日時は ISO8601）
- User, Receipt, Food, UserFood, Recipe, RecipeIngredient など。

（省略: 既存の詳細モデルは同様だが、型の表記を実値例に修正済み）

---

## 4. エラーレスポンス

### 標準エラーフォーマット
```json
{
  "error": {
    "code": "AUTH_002",
    "message": "Access token has expired",
    "details": null,
    "timestamp": "2025-11-28T10:20:00Z"
  }
}
```

### HTTP ステータスと利用方針
- 200: 正常
- 201: リソース作成成功
- 202: 非同期処理受付（例: 画像アップロード）
- 204: 削除成功（レスポンスボディなしを推奨）
- 4xx: クライアントエラー
- 5xx: サーバエラー

### エラーコード（代表例に RATE_LIMIT を追加）
- AUTH_001..004: 認証関連
- VALIDATION_001..003: バリデーション
- RESOURCE_001..003: リソース関連
- OCR_001..004: OCR 関連
- SYSTEM_001..003: システム関連
- RATE_LIMIT_EXCEEDED: レート制限超過

### 例: 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": { "retry_after": 60 },
    "timestamp": "2025-11-28T10:21:00Z"
  }
}
```

ヘッダー:
```
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1700000000
```

---

## 5. レート制限

- 認証済み: 100 req/min
- 未認証: 20 req/min
- 画像アップロード: 10 req/min

仕様:
- レスポンスに `X-RateLimit-*` と `Retry-After` を付与してください。

---

## 6. 運用・ベストプラクティス

- 日時は ISO 8601 (UTC)
- フィールド名は snake_case に統一
- 大きなファイルは presigned upload を利用
- Webhook は HMAC 署名を付与
- API は OpenAPI 3.0 化して自動スキーマ生成を推奨

---

## 7. 変更履歴
- 2025-11-28 v1.1.0 — API 設計の整理、パスワードリセット・メール確認・明細編集・画像取得・Webhook・ヘルスチェックを追加、型表記の実データ化、重複削除
- 2025-11-6 v1.0.0 - 初版作成
