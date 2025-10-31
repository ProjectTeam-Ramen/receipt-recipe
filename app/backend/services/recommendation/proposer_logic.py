from .data_models import Recipe, Ingredient, UserParameters
from typing import List, Dict, Set, Tuple
import numpy as np

class RecipeProposer:
    def __init__(self, all_recipes: List[Recipe], user_inventory: List[Ingredient], user_profile_vector: np.ndarray):
        self.all_recipes = all_recipes
        # 在庫を辞書に変換 {食材名: 残量}
        self.inventory_dict = {ing.name: ing.quantity for ing in user_inventory}
        self.user_profile_vector = user_profile_vector

        self.WEIGHT_INVENTORY = 0.7
        self.WEIGHT_PREFERENCE = 0.3

        # 提案の最低ライン (在庫カバー率が20%未満のものは提案から除外)
        self.MIN_COVERAGE_THRESHOLD = 0.2

    # --- コサイン類似度計算 (好みスコア) ---
    def _calculate_cosine_similarity(self, recipe_vector: np.ndarray) -> float:
        dot_product = np.dot(self.user_profile_vector, recipe_vector)
        norm_user = np.linalg.norm(self.user_profile_vector) #コサイン類似度を計算するときの分母となるノルムの計算
        norm_recipe = np.linalg.norm(recipe_vector) #1行上と同様
        
        denominator = norm_user * norm_recipe
        if denominator == 0:
            return 0.0 #ゼロ除算エラーの回避
            
        return dot_product / denominator # 0から1の範囲

    # --- 食材カバー率計算 (在庫スコア) ---
    def _calculate_inventory_coverage(self, recipe: Recipe) -> Tuple[float, Set[str]]:
        """数量ベースの食材カバー率を計算 (99g/100g -> 0.99)"""
        SEASONING_NAMES = {'醤油', '塩', '砂糖', 'みりん', '酒', '料理酒', '胡椒', 'ごま油', 'オリーブオイル', '酢', '味噌', 'だし', '鶏ガラスープの素', '片栗粉', '小麦粉', '豆板醤'} # 調味料リスト
        total_required_amount = 0.0
        total_covered_amount = 0.0
        missing_ingredients = set() # 不足している食材のリスト

        for name, required_qty in recipe.required_qty.items():
            if name in SEASONING_NAMES:
                continue

            stock_qty = self.inventory_dict.get(name, 0.0) # 在庫がなければ 0
            
            # (1) 必要総量に加算
            total_required_amount += required_qty
            
            # (2) 在庫で賄える量を決定
            if stock_qty >= required_qty:
                total_covered_amount += required_qty
            elif stock_qty > 0:
                # 不足しているが、残量がある場合: 在庫分だけを賄えるとカウント
                total_covered_amount += stock_qty
                missing_ingredients.add(f"{name} ({required_qty - stock_qty:.1f}g不足)")
            else:
                # 在庫が全くない場合
                missing_ingredients.add(f"{name} ({required_qty:.1f}g必要)")

        if total_required_amount == 0:
            return 0.0, missing_ingredients
            
        coverage_rate = total_covered_amount / total_required_amount
        return coverage_rate, missing_ingredients

    # --- メインメソッド：提案実行 ---
    def propose(self, params: UserParameters) -> List[Dict]:
        final_proposals = []

        for recipe in self.all_recipes:
            
            # 1. 食材カバー率の計算
            coverage_score, missing = self._calculate_inventory_coverage(recipe)

            # 1.1 最低カバー率チェック  <- 迷い中
            if coverage_score < self.MIN_COVERAGE_THRESHOLD:
               continue 
                        
            # 2.1 アレルギーチェック 
            is_allergic = any(ing in params.allergies for ing in recipe.required_qty.keys())
            if is_allergic:
                continue 

            # 2.2 時間・カロリーチェック 
            if recipe.prep_time > params.max_time or recipe.calories > params.max_calories:
                continue
            
            # 3. 好みスコアの計算 
            preference_score = self._calculate_cosine_similarity(recipe.feature_vector)

            # 4. 最終提案スコアの算出 
            final_score = (coverage_score * self.WEIGHT_INVENTORY) + (preference_score * self.WEIGHT_PREFERENCE)
            
            final_proposals.append({
                'recipe_name': recipe.name,
                'final_score': final_score,
                'coverage_score': coverage_score,
                'preference_score': preference_score,
                'prep_time': recipe.prep_time,
                'calories': recipe.calories,
                'missing_items': missing
            })

        # 5. 最終提案スコアが高い順にソートして返す
        final_proposals.sort(key=lambda x: x['final_score'], reverse=True)
        
        return final_proposals