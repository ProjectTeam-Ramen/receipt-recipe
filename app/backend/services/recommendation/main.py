from typing import Dict, List, Tuple, Union
# 依存するモジュールから必要なクラスをインポート
# ★修正: Ingredientを明示的にインポート★
from .data_models import UserParameters, Ingredient 
from .data_source import InventoryManager, RecipeDataSource 
from .proposer_logic import RecipeProposer 


# ★修正: Python 3.8と互換性のあるUnion構文を使用★
def get_proposals_for_demo(custom_inventory: Union[List[Ingredient], None] = None) -> Tuple[List[Dict], UserParameters]:
    """
    レシピ提案システムのコアロジックを実行し、結果の提案リストとパラメータを返す関数。
    
    custom_inventory: 外部から在庫データを注入するための引数。
    """
    
    # --- 1. データマネージャーの初期化 ---
    inv_manager = InventoryManager() 
    recipe_source = RecipeDataSource() 

    # --- 2. データの取得と前処理 ---
    all_recipes_data = recipe_source.load_and_vectorize_recipes()
    user_profile = recipe_source.create_user_profile_vector()

    # ★ 修正: custom_inventory が None でないかを確認して優先する ★
    if custom_inventory is not None:
        current_inventory_data = custom_inventory
    else:
        # デフォルトのデータソース（仮のデータ）を使用
        current_inventory_data = inv_manager.get_current_inventory()
    
    # --- 3. ユーザーパラメータの設定 (メイン実行時のデフォルト) ---
    user_params = UserParameters(
        max_time=60,
        max_calories=1000,
        allergies={'かぼちゃ'}
    )
    
    # --- 4. RecipeProposerを初期化し、提案を実行 ---
    proposer = RecipeProposer(
        all_recipes=all_recipes_data, 
        user_inventory=current_inventory_data, 
        user_profile_vector=user_profile
    )
    
    proposals: List[Dict] = proposer.propose(user_params)
    
    # 計算された提案リストと、使用したパラメータをセットで返す
    return proposals, user_params


def main_cli_execution():
    """
    スクリプトが直接実行された場合に、結果をコンソールに出力する関数 (デモ出力部分)。
    """
    
    # NOTE: ここではテストとは独立したロジックを実行するため、custom_inventory は渡さない（デフォルトの仮データを使う）
    proposals, user_params = get_proposals_for_demo()
    
    # --- 5. 結果の表示 (デモンストレーション出力) ---
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
            print(f"   不足食材: {', '.join(p['missing_items'])}")
        else:
            print("   食材は全て揃っています．")
    print("=" * 60)

# スクリプトが直接実行された場合に main_cli_execution() を呼び出す
if __name__ == "__main__":
    main_cli_execution()
