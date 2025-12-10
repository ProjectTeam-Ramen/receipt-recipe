import requests

base_url = "http://127.0.0.1:8000"

try:
    # GETリクエストを送信
    response = requests.get(f"{base_url}/items/10")

    # ステータスコードが200 (OK) か確認
    if response.status_code == 200:
        # 結果をJSONとして受け取る
        data = response.json()
        print(f"APIからの応答: {data}")
    else:
        print(f"エラーが発生しました: {response.status_code}")

except requests.exceptions.ConnectionError:
    print("エラー: サーバーに接続できません。Uvicornが起動しているか確認してください。")
