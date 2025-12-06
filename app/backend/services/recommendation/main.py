import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from starlette.concurrency import run_in_threadpool # 同期処理を非同期環境で実行
from typing import Dict, List, Any, Set, Union, Tuple
from pydantic import BaseModel
import numpy as np

# 依存するモジュールから必要なクラスをインポート
from .data_models import UserParameters, Ingredient, RecommendationRequest, Recipe
from .data_source import InventoryManager, RecipeDataSource, FEATURE_DIMENSIONS
from .proposer_logic import RecipeProposer

# --- API設定と初期データロード ---
app = FastAPI(title="レシピ提案サービス API")
# DBホスト名を設定 (data_source.py の _execute_sync_http_request が参照する)
DB_API_HOST = "db-service" #ここにAPIアドレス！！！

# 静的データ（レシピマスターと好みベクトル）をメモリにロード
# NOTE: load_and_vectorize_recipes は、内部でAPIを呼び出す（または失敗する）
RECIPE_SOURCE = RecipeDataSource(db_api_url=DB_API_HOST)
ALL_RECIPES: List[Recipe] = RECIPE_SOURCE.load_and_vectorize_recipes()
USER_PROFILE_VECTOR: np.ndarray = RECIPE_SOURCE.create_user_profile_vector(user_id=1) 


# --- 依存性注入 (Dependency Injection) の準備 ---
def get_inventory_manager():
    """リクエストごとに InventoryManager のインスタンスを提供"""
    # 接続先のホスト名を渡す
    return InventoryManager(db_api_url=DB_API_HOST)


# --- アプリケーションAPIのエンドポイント ---

@app.post("/recommendation/propose", response_model=List[Dict[str, Any]])
async def propose_recipes_api(
    request_data: RecommendationRequest, # フロントエンドからのJSON入力をPydanticが自動検証・変換
    inv_manager: InventoryManager = Depends(get_inventory_manager)
) -> List[Dict[str, Any]]:
    """
    提案ロジックを実行するエンドポイント (同期DBアクセスをスレッドプールで実行)。
    """
    try:
        # 1. 動的な在庫データ（同期メソッド）の取得をスレッドプールで実行
        # run_in_threadpool: ブロッキングな処理を別スレッドで実行し、メインの非同期ループをブロックしない
        current_inventory = await run_in_threadpool(
            inv_manager.get_current_inventory, user_id=request_data.user_id
        )
        
        # 2. 提案ロジックへの入力パラメーターを準備
        params = UserParameters(
            max_time=request_data.max_time,
            max_calories=request_data.max_calories,
            allergies=request_data.allergies
        )
        
        # 3. RecipeProposerを初期化し、提案を実行 (コアロジック)
        proposer = RecipeProposer(
            all_recipes=ALL_RECIPES, 
            user_inventory=current_inventory, 
            user_profile_vector=USER_PROFILE_VECTOR
        )
        
        proposals = proposer.propose(params)
        
        if not proposals:
            # 提案がない場合は404エラーを返す
            raise HTTPException(status_code=404, detail="現在の在庫と制約を満たす提案はありませんでした。")

        # 提案リスト (List[Dict]) をJSONレスポンスとして返す
        return proposals
        
    except Exception as e:
        # データベース接続エラー、ロジックエラーなどをキャッチ
        print(f"ERROR during proposal: {e}")
        # 内部エラーとして500エラーを返す
        raise HTTPException(status_code=500, detail=f"レシピ提案処理中に内部エラーが発生しました。")


# --- CLI実行関数（テスト/デモ用）---
def get_proposals_for_demo(custom_inventory: Union[List[Ingredient], None] = None) -> Tuple[List[Dict], UserParameters]:
    """
    テストファイルから呼び出される実行関数。APIに依存せずローカルでデータを生成する。
    """
    inv_manager = InventoryManager(db_api_url='db-service') # モックホストで初期化
    recipe_source = RecipeDataSource(db_api_url='db-service')
    
    # Static data must be loaded first
    all_recipes_data = recipe_source.load_and_vectorize_recipes()
    user_profile = recipe_source.create_user_profile_vector(user_id=1) 
    
    if custom_inventory is not None:
        current_inventory_data = custom_inventory
    else:
        # デフォルトのデータソース（モック）を使用
        current_inventory_data = inv_manager.get_current_inventory()
    
    user_params = UserParameters(max_time=60, max_calories=1000, allergies={'かぼちゃ'})
    
    proposer = RecipeProposer(all_recipes=all_recipes_data, user_inventory=current_inventory_data, user_profile_vector=user_profile)
    
    proposals: List[Dict] = proposer.propose(user_params)
    return proposals, user_params


def main_cli_execution():
    """スクリプトが直接実行された場合のデモ出力関数。"""
    
    proposals, user_params = get_proposals_for_demo()
    
    print("=" * 60)
    print("           レシピ提案システム 中間発表デモ結果")
    print(f"制約: {user_params.max_time}分, {user_params.max_calories}kcal, アレルギー:{list(user_params.allergies)}")
    print("=" * 60)
    
    if not proposals:
        print("現在の在庫とパラメータを満たす提案可能なレシピはありませんでした。")
        return

    for i, p in enumerate(proposals):
        print(f"\n[{i+1}位] レシピ名: {p['recipe_name']}")
        print(f"  > 最終スコア: {p['final_score']:.4f}")
        print(f"  > 内訳: (カバー率: {p['coverage_score']:.2f} x 0.7) + (好みスコア: {p['preference_score']:.2f} x 0.3)")
        if p['missing_items']:
            print(f"  ⚠️ 不足食材: {', '.join(p['missing_items'])}")
        else:
            print("  ✅ 食材は全て揃っています！")
    print("=" * 60)

# --- サーバー起動 (uvicornで実行) ---
if __name__ == "__main__":
    # 実行: uvicorn main:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8000)
