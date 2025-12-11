import sys
import time
import random
import urllib.request
import urllib.parse
import urllib.error
import json
from pathlib import Path
from typing import List
from dotenv import load_dotenv, find_dotenv
import os

# --- 1. 環境設定 ---
env_path = find_dotenv()
if env_path:
    load_dotenv(env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

BASE_DIR = Path("./data/ingredients")
GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


# --- 2. 共通: 画像ダウンロード関数 ---
def download_images(urls: List[str], save_dir: Path, prefix: str, target_count: int):
    save_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    existing = len(list(save_dir.glob("*.*")))

    if existing >= target_count:
        print(f"⏩ {prefix} は既に {existing} 枚あるためダウンロードをスキップします。")
        return

    print(f"📥 ダウンロード開始: {len(urls)} 件 -> {save_dir}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for i, url in enumerate(urls):
        if existing + success_count >= target_count:
            break

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()

                ext = "jpg"
                if ".png" in url.lower():
                    ext = "png"
                elif ".jpeg" in url.lower():
                    ext = "jpeg"
                elif ".gif" in url.lower():
                    ext = "gif"

                timestamp = int(time.time())
                filename = (
                    f"{prefix}_{success_count + 1 + existing:03d}_{timestamp}.{ext}"
                )
                save_path = save_dir / filename

                with open(save_path, "wb") as f:
                    f.write(content)

                success_count += 1
                time.sleep(random.uniform(0.5, 1.0))

        except Exception:
            pass

    print(f"🎉 完了: 今回 {success_count} 枚保存 (合計 {existing + success_count} 枚)")


# --- 3. Google Custom Search API 検索ロジック ---
def fetch_google_image_urls(query: str, count: int) -> List[str]:
    if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
        print("❌ APIキーまたは検索エンジンIDが設定されていません。")
        return []

    print(f"🔍 [Google API] '{query}' を検索中... (目標: {count}枚)")

    urls = []
    start_index = 1

    # 10枚以下なら1回のリクエストで済むため、ループ条件もシンプルになります
    while len(urls) < count:
        params = {
            "q": query,
            "key": GOOGLE_API_KEY,
            "cx": SEARCH_ENGINE_ID,
            "searchType": "image",
            "num": 10,  # MAX10件
            "start": start_index,
            "safe": "off",
            "fileType": "jpg",
        }

        query_string = urllib.parse.urlencode(params)
        request_url = f"{GOOGLE_SEARCH_URL}?{query_string}"

        try:
            with urllib.request.urlopen(request_url, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))

                items = data.get("items", [])
                if not items:
                    print("⚠️ これ以上の結果がありません。")
                    break

                for item in items:
                    link = item.get("link")
                    if link:
                        urls.append(link)

                # API制限: startパラメータの上限などを考慮しつつ次へ
                start_index += 10

                # countが10以下の場合は1回でbreakして無駄なリクエストを防ぐ
                if count <= 10:
                    break

                time.sleep(1)

        except urllib.error.HTTPError as e:
            print(f"❌ APIリクエストエラー: {e.code} - {e.reason}")
            if e.code == 403:
                print("   -> APIの利用枠上限、またはキーの設定ミスです。")
            break
        except Exception as e:
            print(f"❌ エラー: {e}")
            break

    return urls[:count]


# --- 4. メイン処理 ---
def process_ingredients(target_list: List[str]):
    # ★ ここを50から10に変更しました ★
    TARGET_COUNT = 10

    print(
        f"📋 全 {len(target_list)} 食材の処理を開始します (目標: 各{TARGET_COUNT}枚)。"
    )

    for i, target in enumerate(target_list):
        print(f"\n[{i + 1}/{len(target_list)}] Target: {target} " + "=" * 20)

        save_dir = BASE_DIR / target
        save_dir.mkdir(parents=True, exist_ok=True)
        existing = len(list(save_dir.glob("*.*")))
        needed = TARGET_COUNT - existing

        if needed <= 0:
            print(f"⏩ {target} は既に {existing} 枚あるため検索をスキップします。")
        else:
            g_urls = fetch_google_image_urls(target, count=needed)
            print(f"   -> 取得URL数: {len(g_urls)} 件")

            if g_urls:
                download_images(g_urls, save_dir, target, TARGET_COUNT)
            else:
                print("   -> 画像が見つかりませんでした。")

        if i < len(target_list) - 1:
            time.sleep(1)  # 待機時間も少し短縮


if __name__ == "__main__":
    ingredients_list = [
        "tomato",
        "cucumber",
        "onion",
        "carrot",
        # ...
    ]

    if len(sys.argv) > 1:
        process_ingredients(sys.argv[1:])
    else:
        process_ingredients(ingredients_list)
