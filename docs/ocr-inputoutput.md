# 文字認識チーム連携仕様書 v2.0

## 概要
前処理済みレシート画像から分割された文字領域（`text_detector.py`の出力）を受け取り、
各文字を認識してGNN処理に必要な情報を返却する。

## 入力仕様

### 入力元
`ReceiptOCRProcessor.save_character_images()` が生成する以下のファイル:
- **メタデータファイル**: `{output_dir}/metadata.json`
- **文字画像ファイル**: `{output_dir}/char_XXXX.png`

### 入力JSON構造 (metadata.json)
```json
{
  "source_image": "/path/to/receipt_image.png",
  "total_characters": 50,
  "characters": [
    {
      "char_id": 0,
      "region_id": 0,
      "char": "牛",
      "char_index_in_region": 0,
      "bbox": [100, 50, 120, 80],
      "center": [110.0, 65.0],
      "confidence": 0.95,
      "image_shape": [30, 20, 3],
      "image_path": "/path/to/output/char_0000.png"
    }
  ]
}
```

### フィールド説明（入力）
- `char_id`: 文字の一意識別子（グローバルID）
- `region_id`: 文字が属するテキスト領域のID
- `char`: EasyOCRによる初期認識結果（参考値）
- `char_index_in_region`: 領域内での文字インデックス
- `bbox`: バウンディングボックス `[x_min, y_min, x_max, y_max]`
- `center`: 中心座標 `[x, y]`
- `confidence`: EasyOCRの信頼度（参考値）
- `image_shape`: 切り出し画像のshape `[height, width, channels]`
- `image_path`: 切り出し済み文字画像のパス

## 出力仕様

### 出力ファイル
入力と同じディレクトリに `recognition_results.json` として保存

### 出力JSON構造
```json
{
  "source_metadata": "/path/to/output/metadata.json",
  "model_info": {
    "model_name": "char_recognizer_v1",
    "model_version": "1.0.0",
    "framework": "pytorch",
    "input_size": [64, 64]
  },
  "recognition_results": [
    {
      "char_id": 0,
      "recognized_char": "牛",
      "confidence": 0.98,
      "char_code": 29275,
      "bbox": [100, 50, 120, 80],
      "center": [110.0, 65.0],
      "alternatives": [
        {"char": "牛", "confidence": 0.98},
        {"char": "午", "confidence": 0.01},
        {"char": "生", "confidence": 0.005}
      ],
      "font_features": [0.123, -0.456, 0.789, "... (128次元)"],
      "processing_status": "success"
    },
    {
      "char_id": 1,
      "recognized_char": "",
      "confidence": 0.0,
      "char_code": 0,
      "bbox": [125, 50, 145, 80],
      "center": [135.0, 65.0],
      "alternatives": [],
      "font_features": null,
      "processing_status": "failed",
      "error_message": "Image too blurry"
    }
  ],
  "summary": {
    "total_characters": 50,
    "successfully_recognized": 48,
    "failed": 2,
    "average_confidence": 0.94,
    "processing_time_ms": 1250.5
  }
}
```

## フィールド説明（出力）

### 必須フィールド
- `char_id`: 入力と同じchar_id（紐付け用）
- `recognized_char`: 認識された文字（UTF-8）。失敗時は空文字列
- `confidence`: 認識信頼度 [0.0-1.0]
- `char_code`: Unicodeコードポイント。失敗時は0
- `bbox`: 入力と同じバウンディングボックス（座標の保持）
- `center`: 入力と同じ中心座標（位置情報の保持）
- `processing_status`: `"success"` | `"failed"`

### 推奨フィールド
- `alternatives`: 認識候補Top-3以上
  - `char`: 候補文字
  - `confidence`: 候補の信頼度
- `font_features`: フォント特徴ベクトル（128次元または256次元を想定）
  - CNNの中間層出力などを利用
  - GNNのノード特徴量として使用

### オプションフィールド
- `error_message`: 失敗時のエラーメッセージ
- その他、モデル固有の情報

## データフロー

```
[text_detector.py]
    ↓ save_character_images()
[metadata.json + char_XXXX.png]
    ↓
[文字認識チーム]
    ↓ 文字認識処理
[recognition_results.json]
    ↓
[graph_builder.py (GNN)]
```

## エラーハンドリング

### 入力ファイル不正
- `metadata.json` が存在しない → HTTP 400
- 画像ファイルが存在しない → 該当char_idを `processing_status: "failed"` でスキップ

### 認識失敗時
```json
{
  "char_id": X,
  "recognized_char": "",
  "confidence": 0.0,
  "char_code": 0,
  "processing_status": "failed",
  "error_message": "Reason for failure"
}
```

## 性能要件
- **処理時間**: 文字数50個のレシートで2秒以内（目標値）
- **精度**: 日本語文字の認識精度90%以上（目標値）
- **GPU利用**: 推奨（バッチ処理で高速化）

## API仕様（オプション）

REST APIとして実装する場合:

### エンドポイント
```
POST /api/v1/recognize
```

### リクエスト
```json
{
  "metadata_path": "/path/to/metadata.json"
}
```

または

```json
{
  "receipt_id": "receipt_001",
  "characters": [ /* metadata.jsonの中身 */ ]
}
```

### レスポンス
```json
{
  "status": "success",
  "data": { /* recognition_results.jsonの中身 */ }
}
```

## 納期・マイルストーン
- **Week 1**: I/F仕様の最終確認、モックデータでの動作確認
- **Week 2**: 初期モデルの実装、精度検証
- **Week 3**: 統合テスト、性能チューニング
- **Week 4**: 本番環境デプロイ

## テストデータ
- サンプル `metadata.json` を提供（次セクション参照）
- 期待される出力サンプルも提供

## 問い合わせ先
- GNN担当: [あなたの連絡先]
- 統合テスト担当: [担当者連絡先]