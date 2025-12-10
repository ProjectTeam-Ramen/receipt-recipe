# Receipt-Recipe API 設計書（実装同期版）

## 0. 概要
- **API 名**: Receipt-Recipe API v1
- **ベース URL**: `http://127.0.0.1:8000/api/v1`
- **バージョン**: 1.0.0（`FastAPI(title="Receipt-Recipe API v1")` より）
- **最終更新日**: 2025-12-10
- **主な機能**:
  - JWT 認証とユーザー管理
  - 食材（在庫）および食品マスタの参照・更新
  - レシート画像アップロード（モック実装）
  - レシピ詳細参照＆調理実績の登録
  - 在庫ベースのレシピレコメンド

> ⚠️ 本ドキュメントは `app/backend/api` 以下の FastAPI 実装を基準にしています。未実装の設計要素（メール認証、master 管理 API 等）は削除済みです。

---

## 1. 共通仕様
### 1.1 認証
- 方式: JWT (HS256)
  - access_token 有効期限: 30 分 (`ACCESS_TOKEN_EXPIRE_SECONDS = 1800`)
  - refresh_token 有効期限: 7 日 (`REFRESH_TOKEN_EXPIRE_DAYS = 7`)
- Header: `Authorization: Bearer <access_token>`
- `/api/v1/health` のみ無認証。その他はエンドポイント表に準ずる。

### 1.2 エラーフォーマット
- FastAPI 既定 `{ "detail": "..." }` を基本とし、HTTP ステータスは `HTTPException` の `status_code` に準拠。
- バリデーションエラーは 422 (FastAPI 既定)。

### 1.3 日時・命名規則
- 日時: ISO 8601 (UTC)。
- JSON フィールド: snake_case。

---

## 2. エンドポイント一覧

| 分類 | メソッド / パス | 説明 | 認証 |
| --- | --- | --- | --- |
| ヘルス | `GET /health` | 生存監視 | 不要 |
| 認証 | `POST /auth/register` | ユーザー登録 | 不要 |
|  | `POST /auth/login` | email/password → access & refresh | 不要 |
|  | `POST /auth/refresh` | refresh token で access 再発行 | 不要 |
|  | `POST /auth/logout` | refresh token の失効 | 不要 |
|  | `POST /auth/password-reset` | リセットメール送信（モック） | 不要 |
|  | `POST /auth/password-reset/confirm` | 新パスワード確定（モック） | 不要 |
| ユーザー | `GET /users/me` | 自分のプロフィール | 要 |
|  | `PUT /users/me/password` | パスワード変更 | 要 |
| 食品マスタ | `GET /foods` | 食材マスタ検索 | 要 |
| 在庫 | `GET /ingredients` | ユーザー在庫一覧 | 要 |
|  | `POST /ingredients` | 在庫追加/加算 | 要 |
|  | `PATCH /ingredients/{id}/status` | 状態変更 (unused/used/deleted) | 要 |
|  | `POST /ingredients/{id}/consume` | 在庫消費 | 要 |
|  | `DELETE /ingredients/{id}` | 在庫削除（status=deleted） | 要 |
| レシート | `POST /receipts/upload` | 画像アップロード → モック解析 | 不要 |
|  | `GET /receipts/{id}` | 解析結果の取得 | 不要 |
|  | `GET /receipts/{id}/status` | 処理状態 | 不要 |
|  | `GET /receipts/{id}/image` | 保存画像取得 | 不要 |
|  | `PATCH /receipts/{id}/items/{item_id}` | OCR 明細の手動修正 | 不要 |
| レシピ | `GET /recipes/static-catalog` | 静的 HTML カタログ | 不要 |
|  | `GET /recipes/{id}` | レシピ詳細＋在庫比較 | 任意 (付与で在庫比較) |
|  | `POST /recipes/{id}/cook` | 調理記録＋在庫消費 | 要 |
| レコメンド | `POST /recommendation/propose` | レシピ推薦 | 条件付き（後述） |

---

## 3. エンドポイント詳細

### 3.1 ヘルスチェック
- `GET /api/v1/health`
  - レスポンス: `{ "status": "ok" }`

### 3.2 認証 (`/auth`)
- `POST /register`
  - 入力: `{ "username": "demo", "email": "demo@example.com", "password": "ChangeMe123", "birthday": "1995-05-05" }`
  - 出力: ユーザー情報 (`user_id`, `username`, `email`, `birthday`, `created_at`)
- `POST /login`
  - 入力: `{ "email": "demo@example.com", "password": "ChangeMe123" }`
  - 出力: `{ "access_token": "...", "refresh_token": "...", "token_type": "Bearer", "expires_in": 1800 }`
- `POST /refresh`
  - 入力: `{ "refresh_token": "..." }`
  - 出力: 新しい access token（refresh は再発行しない）
- `POST /logout`
  - 入力: `{ "refresh_token": "..." }`
  - 出力: `{ "message": "Successfully logged out" }`
- `POST /password-reset` / `/password-reset/confirm`
  - いずれもモック実装で固定メッセージを返す。

### 3.3 ユーザー (`/users`)
- `GET /users/me`
  - 認証必須。`UserResponse`（`user_id`, `username`, `email`, `birthday`, `created_at`）。
- `PUT /users/me/password`
  - 入力: `{ "old_password": "ChangeMe123", "new_password": "MoreSecure456" }`
  - ハッシュを更新し `{ "message": "Password updated" }`。

### 3.4 食品マスタ (`/foods`)
- 認証必須。`q` (部分一致), `limit` クエリをサポート。
- `FoodListResponse`:
```json
{
  "total": 1,
  "foods": [
    { "food_id": 1, "food_name": "にんじん", "category_id": 3, "category_name": "野菜" }
  ]
}
```

### 3.5 在庫 (`/ingredients`)
- 作成 (`POST /`): `food_id`, `quantity_g`, 任意で `purchase_date`, `expiration_date`。
- 一覧 (`GET /`): デフォルトは `status=unused` のみ。`?status=used` 等で切替。
- 状態更新 (`PATCH /{user_food_id}/status`): `status` を `unused|used|deleted` に変更。
- 消費 (`POST /{user_food_id}/consume`): 数量を減算し、0 以下で `status=used`。
- 削除 (`DELETE /{user_food_id}`): `status=deleted` + `quantity_g=0`。削除済みなら冪等で 204。

レスポンス例 (`GET /ingredients`):
```json
{
  "total": 2,
  "ingredients": [
    {
      "user_food_id": 10,
      "food_id": 1,
      "food_name": "にんじん",
      "quantity_g": 250.0,
      "purchase_date": "2025-12-01",
      "expiration_date": "2025-12-10",
      "status": "unused"
    }
  ]
}
```

### 3.6 レシート (`/receipts`)
> 現状はインメモリ実装で認証も行っていません。アプリ再起動でデータが消えます。

- `POST /upload` (multipart/form-data)
  - `file` 必須、`callback_url` 任意。
  - ステータス 202。`{"receipt_id": 1, "status": "processing", "message": "Receipt uploaded. Processing started."}`
- `GET /{id}/status`
  - `{ "receipt_id": 1, "status": "completed", "progress": 100 }`
- `GET /{id}`
  - 解析済みデータ（`items` はモック）。`image_path` はレスポンスから除去。
- `GET /{id}/image`
  - 保存済みファイルをストリーム返却（FastAPI `FileResponse`）。
- `PATCH /{id}/items/{item_id}`
  - 明細 dict を部分更新して返却。

### 3.7 レシピ (`/recipes`)
- `GET /static-catalog`
  - `data/recipes.json` と静的 HTML (`data/recipe-list/*.html`) が揃っている分のみ返す。`[{ id, title, detail_path, ingredients, cooking_time, calories }]`
- `GET /{recipe_id}`
  - 認証任意。認証済みのときは在庫と突合、`available_quantity_g`/`missing_quantity_g` を付与。
- `POST /{recipe_id}/cook`
  - 認証必須。`{ "servings": 2 }`
  - 在庫を `with_for_update` でロックし不足時 400。成功すると `CookRecipeResponse`（消費した食材情報）を返す。

### 3.8 レコメンド (`/recommendation/propose`)
- メソッド: POST
- 認証: 任意
  - **認証あり**: `user_id` と `inventory` フィールドは無視され、サーバー在庫 (`InventoryManager`) を利用。
  - **未認証**: `user_id` (int) と `inventory` (食材配列) が必須。
- リクエストスキーマ（`RecommendationRequest`）主フィールド:
  - `user_id: int`
  - `max_time: int`
  - `max_calories: int`
  - `allergies: List[str]`
  - `inventory: List[{ name: str, quantity: number, expiration_date?: "YYYY-MM-DD" }]`
  - `recipes`, `history`: 任意で嗜好ベクトルを上書きするための過去データ。
- レスポンス例:
```json
[
  {
    "recipe_id": 202,
    "recipe_name": "豚肉炒め",
    "final_score": 0.88,
    "coverage_score": 0.95,
    "preference_score": 0.72,
    "user_preference_vector": [0.1, 0.4, 0.5],
    "user_preference_labels": ["is_japanese", "is_main_dish"],
    "prep_time": 20,
    "calories": 450,
    "is_boosted": true,
    "missing_items": ["たまねぎ (50.0g必要)"],
    "required_qty": { "豚肉": 240.0, "たまねぎ": 50.0 },
    "req_count": 2,
    "inventory_source": "server",
    "inventory_count": 5,
    "inventory_label": "サーバー在庫 5件"
  }
]
```
- 提案 0 件: `404` + `detail="現在の在庫と条件に合うレシピが見つかりません。"`
- 未認証で `inventory` 省略時は 400。
- 認証済みで他ユーザー `user_id` を指定すると 403。

---

## 4. 主要データモデル

| モデル | フィールド | 備考 |
| --- | --- | --- |
| `IngredientResponse` | `user_food_id`, `food_id`, `food_name`, `quantity_g`, `purchase_date`, `expiration_date`, `status` | `/ingredients` 系レスポンス |
| `FoodResponse` | `food_id`, `food_name`, `category_id`, `category_name` | `/foods` |
| `RecipeDetailResponse` | レシピ基本情報 + 旗フラグ + `ingredients[]` | `/recipes/{id}` |
| `CookRecipeResponse` | `consumed[]` (食材ごとの required/consumed/remaining) | `/recipes/{id}/cook` |
| `RecommendationResult` | スコア、欠品、`inventory_*` メタ情報 | `/recommendation/propose` |

各モデル定義は `app/backend/api/routers` および `app/backend/services/recommendation/data_models.py` を参照。

---

## 5. エラー・品質ゲート
- FastAPI 既定フォーマット `{ "detail": "..." }` を利用。
- 在庫/レコメンド関連では日本語メッセージ（例: `"在庫が足りません: ..."`）。
- 500 系は基本的に `HTTPException(status_code=500, detail="...")` を直接送出。

---

## 6. 開発・運用メモ
- `receipts` エンドポイントは学習/デモ用途であり、永続化や認証が未実装。
- `recipes/static-catalog` は `data/recipe-list` に HTML が存在するファイルのみ返す。データ追加時は HTML/JSON をセットで配置。
- レコメンドでは在庫ソースを `inventory_source` で明示。フロントは同フィールドで UI ラベルを切替。
- 起動時 `sync_food_master()` と `sync_recipe_master()` が呼ばれるため、マスタ JSON が更新された際は再起動で反映。

---

## 7. 変更履歴
| 日付 | 内容 |
| --- | --- |
| 2025-12-10 | FastAPI 実装に沿って全面更新。未実装 API を削除し、レコメンドの multi-user 仕様を明文化。 |
| 2025-11-28 | 旧版。メール認証や管理 API など未実装の記述を含んでいた。 |

今後の更新は `app/backend/api` の変更に合わせて本ドキュメントも同期してください。

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
