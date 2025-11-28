import os
import time
import requests
import base64
from pathlib import Path

# 画像を保存するフォルダ
SAVE_DIR = Path("images")

def fetch_images(query, total_num=50):
    """
    指定されたクエリで画像を検索し、保存する関数
    """
    print(f"🔍 '{query}' の画像を収集開始...")
    
    # 1. 環境変数の取得
    api_key = os.environ.get("GOOGLE_API_KEY")
    cx = os.environ.get("SEARCH_ENGINE_ID")

    if not api_key or not cx:
        print("❌ エラー: .envファイルの設定を確認してください")
        return

    # 保存用ディレクトリ作成 (例: images/アボカド/)
    save_path = SAVE_DIR / query
    save_path.mkdir(parents=True, exist_ok=True)

    count = 0        # 保存した枚数
    start_index = 1  # 検索開始位置 (1, 11, 21...)

    # 2. 50枚集まるまでAPIを叩き続けるループ
    while count < total_num:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "searchType": "image", # 画像検索モード
            "num": 10,             # 1回のリクエストで最大10件
            "start": start_index   # ページ送り
        }

        try:
            # APIリクエスト
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 検索結果がもうない場合
            if "items" not in data:
                print("⚠️ これ以上画像が見つかりませんでした")
                break

            items = data["items"]

            # 3. 画像のダウンロード処理
            for item in items:
                if count >= total_num:
                    break
                
                image_url = item["link"]
                
                try:
                    # 画像データの取得（3秒タイムアウト設定）
                    img_data = requests.get(image_url, timeout=3).content
                    
                    # ファイル名: 001.jpg のように連番にする
                    file_extension = os.path.splitext(image_url)[-1]
                    if not file_extension: file_extension = ".jpg"
                    
                    filename = f"{count + 1:03}{file_extension}"
                    file_path = save_path / filename

                    with open(file_path, "wb") as f:
                        f.write(img_data)
                    
                    print(f"✅ 保存完了 ({count+1}/{total_num}): {filename}")
                    count += 1
                    
                except Exception as e:
                    print(f"⚠️ ダウンロード失敗: {e}")
                    continue

            # 次の10件へ進む
            start_index += 10
            
            # API制限を避けるため少し待機
            time.sleep(1)

        except Exception as e:
            print(f"❌ APIエラー: {e}")
            break

    print(f"🎉 完了！ 合計 {count} 枚の画像を保存しました。")

if __name__ == "__main__":
    # ここに探したい食材名を入れる
    target_food = "パクチー" 
    fetch_images(target_food, total_num=50)