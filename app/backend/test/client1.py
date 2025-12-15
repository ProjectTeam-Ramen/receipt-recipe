import httpx

base_url = "http://127.0.0.1:8000"

try:
    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        response = client.get("/items/10")

        if response.status_code == 200:
            data = response.json()
            print(f"APIからの応答: {data}")
        else:
            print(f"エラーが発生しました: {response.status_code}")
except httpx.RequestError:
    print("エラー: サーバーに接続できません。Uvicornが起動しているか確認してください。")
