from fastapi import FastAPI

# 1. FastAPIのインスタンスを作成
app = FastAPI()

# 2. ルート（/）へのGETリクエストに対する処理
@app.get("/")
def read_root():
    return {"Hello": "World"}

# 3. /items/ というエンドポイントへのGETリクエスト
@app.get("/items/")
def read_items():
    # 実際にはここでデータベースからデータを取得する
    return [{"name": "Item 1"}, {"name": "Item 2"}]

# 4. パスパラメータ（/items/5 など）を受け取る
# {item_id} の部分が動的に変わる
@app.get("/items/{item_id}")
def read_item(item_id: int):  # 型ヒント(int)で自動的にバリデーション
    return {"item_id": item_id, "description": f"This is item number {item_id}"}