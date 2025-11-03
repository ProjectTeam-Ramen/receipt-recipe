from .data_models import Recipe, Ingredient, UserParameters
from typing import List, Dict, Set, Tuple, Union
import numpy as np
from datetime import date, timedelta # ★追加: 日付操作のためにインポート★

class RecipeProposer:
    def __init__(self, all_recipes: List[Recipe], user_inventory: List[Ingredient], user_profile_vector: np.ndarray):
        self.all_recipes = all_recipes
        
        # ★修正: 在庫を辞書に変換 {食材名: (残量, 期限)} のタプルを持たせる ★
        self.inventory_dict = {
            ing.name: (ing.quantity, ing.expiration_date) 
            for ing in user_inventory
        }
        self.user_profile_vector = user_profile_vector

        self.WEIGHT_INVENTORY = 0.7
        self.WEIGHT_PREFERENCE = 0.3
        self.MIN_COVERAGE_THRESHOLD = 0.2

        # 賞味期限ブーストの定数 (3日以内ならブースト)
        self.EXPIRATION_BOOST_DAYS = 3 
        self.EXPIRATION_BONUS_FACTOR = 0.1 # スコアに10%のボーナス

        # ★修正: 調味料リストを__init__で定義し、self.SEASONING_NAMESとしてクラス全体で利用可能にする★
        self.SEASONING_NAMES = {'醤油', '塩', '砂糖', 'みりん', '酒', '料理酒', '胡椒', 'ごま油', 'オリーブオイル', '酢', '味噌', 'だし', '鶏ガラスープの素', '片栗粉', '小麦粉', '豆板醤'}


    # --- コサイン類似度計算 (好みスコア) ---
    def _calculate_cosine_similarity(self, recipe_vector: np.ndarray) -> float:
        dot_product = np.dot(self.user_profile_vector, recipe_vector)
        norm_user = np.linalg.norm(self.user_profile_vector)
        norm_recipe = np.linalg.norm(recipe_vector)
        
        denominator = norm_user * norm_recipe
        if denominator == 0:
            return 0.0
            
        return dot_product / denominator

    # --- 食材カバー率計算 (在庫スコア) ---
    def _calculate_inventory_coverage(self, recipe: Recipe) -> Tuple[float, Set[str]]:
        """数量ベースの食材カバー率を計算 (調味料は除外)"""
        # ★修正: SEASONING_NAMES のローカル定義を削除し、self.SEASONING_NAMES を使用★
        total_required_amount = 0.0
        total_covered_amount = 0.0
        missing_ingredients = set()

        for name, required_qty in recipe.required_qty.items():
            if name in self.SEASONING_NAMES: # ★修正後: self.SEASONING_NAMES を使用★
                continue

            # 期限情報も取得するためタプルで取得し、数量のみ使用
            inventory_info = self.inventory_dict.get(name)
            stock_qty = inventory_info[0] if inventory_info else 0.0
            
            # (1) 必要総量に加算
            total_required_amount += required_qty
            
            # (2) 在庫で賄える量を決定
            if stock_qty >= required_qty:
                total_covered_amount += required_qty
            elif stock_qty > 0:
                total_covered_amount += stock_qty
                missing_ingredients.add(f"{name} ({required_qty - stock_qty:.1f}g不足)")
            else:
                missing_ingredients.add(f"{name} ({required_qty:.1f}g必要)")

        if total_required_amount == 0:
            return 0.0, missing_ingredients
            
        coverage_rate = total_covered_amount / total_required_amount
        return coverage_rate, missing_ingredients

    # --- 【新規メソッド】賞味期限ブースト係数の計算 ---
    def _get_expiration_boost_factor(self, recipe: Recipe) -> float:
        """
        レシピに必要な食材の中で、期限切れが近いものがあるかチェックし、ボーナス係数を返す。
        """
        today = date.today()
        
        for name in recipe.required_qty.keys():
            if name in self.SEASONING_NAMES: # ★修正後: self.SEASONING_NAMES を使用★
                continue

            # 在庫辞書から量と期限を取得 (タプル形式)
            inventory_info = self.inventory_dict.get(name)
            
            if inventory_info is None:
                continue # 在庫がない場合、チェックをスキップ

            # 期限切れ日の情報を取り出す
            quantity, expiry_date = inventory_info
            
            # 在庫量がゼロ以下の場合、ブーストしない
            if quantity <= 0:
                continue

            # 期限が設定されており、かつブースト期間内（N日以内）かチェック
            if expiry_date and (expiry_date >= today) and (expiry_date <= (today + timedelta(days=self.EXPIRATION_BOOST_DAYS))):
                # 期限が今日以降で、かつブースト期間内の場合、ボーナスを適用
                return self.EXPIRATION_BONUS_FACTOR # 10%のボーナス係数を返す
            
        return 0.0 # ボーナスなし
        
    # --- メインメソッド：提案実行 ---
    def propose(self, params: UserParameters) -> List[Dict]:
        final_proposals = []

        for recipe in self.all_recipes:
            
            # 1. 食材カバー率の計算
            coverage_score, missing = self._calculate_inventory_coverage(recipe)

            # 1.1 最低カバー率チェック 
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
            final_score_base = (coverage_score * self.WEIGHT_INVENTORY) + (preference_score * self.WEIGHT_PREFERENCE)
            
            # 【追加】賞味期限ブーストの適用
            boost_factor = self._get_expiration_boost_factor(recipe)
            final_score = final_score_base * (1 + boost_factor)

            final_proposals.append({
                'recipe_id': recipe.id,
                'recipe_name': recipe.name,
                'final_score': final_score,
                'coverage_score': coverage_score,
                'preference_score': preference_score,
                'prep_time': recipe.prep_time,
                'calories': recipe.calories,
                # 【追加】ブーストが適用されたかどうか
                'is_boosted': True if boost_factor > 0 else False, 
                'missing_items': missing
            })

        # 5. 最終提案スコアが高い順にソートして返す
        final_proposals.sort(key=lambda x: x['final_score'], reverse=True)
        
        return final_proposals
