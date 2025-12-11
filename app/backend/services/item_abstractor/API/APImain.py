import os
import sys
import time
import random
import requests
from pathlib import Path
from typing import List
from duckduckgo_search import DDGS
from dotenv import load_dotenv, find_dotenv

# --- 1. 環境設定 ---
env_path = find_dotenv()
if env_path:
    load_dotenv(env_path)

API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
BASE_DIR = Path("./data/ingredients")


# --- 2. 共通: 画像ダウンロード関数 ---
def download_images(urls: List[str], save_dir: Path, prefix: str):
    save_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0

    # 既存ファイルの枚数をチェック（既に50枚あるならダウンロードしない）
    existing = len(list(save_dir.glob("*.*")))
    if existing >= 50:
        print(f"⏩ {prefix} は既に {existing} 枚あるためスキップします。")
        return

    print(f"📥 ダウンロード開始: {len(urls)} 件 -> {save_dir}")

    for i, url in enumerate(urls):
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()

            ext = "jpg"
            if ".png" in url.lower():
                ext = "png"
            elif ".jpeg" in url.lower():
                ext = "jpeg"

            timestamp = int(time.time())
            # ファイル名重複防止の工夫
            filename = f"{prefix}_{success_count + 1 + existing:03d}_{timestamp}.{ext}"
            save_path = save_dir / filename

            with open(save_path, "wb") as f:
                f.write(res.content)

            success_count += 1
            # ダウンロード間隔も少しランダムにする
            time.sleep(random.uniform(0.5, 1.5))

        except Exception:
            pass

    print(f"🎉 完了: 今回 {success_count} 枚保存 (合計 {existing + success_count} 枚)")


# --- 3. Google検索 (確実な10枚) ---
def fetch_google_urls(query: str, count: int = 10) -> List[str]:
    if not API_KEY:
        return []

    print(f"🤖 [Google] '{query}' を検索中...")
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "searchType": "image",
        "num": 10,
        "start": 1,
        "safe": "off",
    }

    try:
        res = requests.get(search_url, params=params, timeout=10)
        res.raise_for_status()
        items = res.json().get("items", [])
        return [item["link"] for item in items][:count]
    except Exception as e:
        print(f"❌ [Google] エラー: {e}")
        return []


# --- 4. DuckDuckGo検索 (ステルス仕様) ---
def fetch_ddg_urls(query: str, count: int) -> List[str]:
    if count <= 0:
        return []

    #検索前にしっかり休憩する
    sleep_time = random.uniform(5, 10)
    print(f"💤 DDG警戒回避のため {sleep_time:.1f} 秒待機中...")
    time.sleep(sleep_time)

    print(f"🦆 [DuckDuckGo] '{query}' を検索中... (目標: {count}枚)")
    urls = []

    try:
        with DDGS() as ddgs:
            # max_resultsを指定して取得
            results = ddgs.images(keywords=query, max_results=count)
            urls = [r["image"] for r in results]
    except Exception as e:
        print(f"❌ [DuckDuckGo] 取得失敗: {e}")
        print("   -> 無理せずGoogleの分だけで進みます。")

    return urls


# --- 5. メイン処理 (20食材対応ループ) ---
def process_ingredients(target_list: List[str]):
    print(f"📋 全 {len(target_list)} 食材の処理を開始します。")

    for i, target in enumerate(target_list):
        print(f"\n[{i+1}/{len(target_list)}] Target: {target} " + "="*20)

        all_urls = []

        # 1. Google (必ず実行)
        google_urls = fetch_google_urls(target, count=10)
        all_urls.extend(google_urls)
        print(f"   -> Google: {len(google_urls)} 件")

        # 2. DDG (Googleで取れた分を差し引いて実行)
        remaining = 50 - len(all_urls)
        if remaining > 0:
            ddg_urls = fetch_ddg_urls(target, count=remaining)
            all_urls.extend(ddg_urls)
            print(f"   -> DDG: {len(ddg_urls)} 件")

        # 3. 保存
        unique_urls = list(set(all_urls))
        save_dir = BASE_DIR / target
        download_images(unique_urls, save_dir, target)

        # ★食材と食材の間にも長い休憩を入れる
        if i < len(target_list) - 1:
            rest_time = random.uniform(10, 20)
            print(f"☕ 次の食材まで {rest_time:.1f} 秒休憩します...")
            time.sleep(rest_time)


if __name__ == "__main__":
    # --- ここに20種類以上の食材リストを書いてください ---
    ingredients_list = [
        "パクチー",
        "トマト",
        "きゅうり",
        "キャベツ",
        "玉ねぎ",
        "じゃがいも",
        "人参",
        "大根",
        "なす",
        "ピーマン",
        # ... 他の食材を追加 ...
    ]

    # コマンドライン引数があればそれを優先、なければリストを実行
    if len(sys.argv) > 1:
        process_ingredients(sys.argv[1:])
    else:
        process_ingredients(ingredients_list)
