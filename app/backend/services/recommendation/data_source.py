# data_modelsからインポート
from .data_models import Ingredient, Recipe
import numpy as np
from typing import List

# コサイン類似度計算のための全次元の定義
FEATURE_DIMENSIONS = [
    '和食', '洋食', '中華', '主菜', '副菜', '肉類', '魚介類', 'ベジタリアン', '複合',
    '辛味', '煮込み', '揚げ物' # 議論で追加した味覚・調理法の傾向
]

class RecipeDataSource:
    """レシピデータセットからレシピを読み込み、ベクトル化するクラス"""
    
    def load_and_vectorize_recipes(self) -> List[Recipe]:
        # --- 実際はCSV/DBから読み込み、One-Hot Encodingでベクトルを生成 ---
        
        raw_recipes_data = [
            # 1. 豚の生姜焼き (和食, 主菜, 肉類)
            {'id': 1, 'name': '豚の生姜焼き', 'req': {'豚肉': 250.0, '玉ねぎ': 100.0, '生姜': 10.0}, 
             'time': 20, 'cal': 450, 'feats': {'和食': 1, '主菜': 1, '肉類': 1}},
            # 2. シーフードパスタ (洋食, 主菜, 魚介類) -> エビを含むためアレルギーテスト用
            {'id': 2, 'name': 'シーフードパスタ', 'req': {'エビ': 100.0, 'パスタ': 200.0, 'トマト': 150.0}, 
             'time': 40, 'cal': 650, 'feats': {'洋食': 1, '主菜': 1, '魚介類': 1}},
            # 3. 麻婆豆腐 (中華, 主菜, 辛味, 煮込み)
            {'id': 3, 'name': '麻婆豆腐', 'req': {'豆腐': 300.0, '豚ひき肉': 50.0, '豆板醤': 5.0}, 
             'time': 35, 'cal': 400, 'feats': {'中華': 1, '主菜': 1, '肉類': 1, '辛味': 1, '煮込み': 1}},
            # 4. ポテトサラダ (洋食, 副菜, ベジタリアン)
            {'id': 4, 'name': 'ポテトサラダ', 'req': {'じゃがいも': 500.0, 'マヨネーズ': 50.0}, 
             'time': 25, 'cal': 350, 'feats': {'洋食': 1, '副菜': 1, 'ベジタリアン': 1}},
        ]
        
        recipes = []
        for d in raw_recipes_data:
            # One-Hot Encodingの実行: 定義した全次元に合わせてベクトルを生成
            vector = np.array([d['feats'].get(dim, 0) for dim in FEATURE_DIMENSIONS], dtype=np.float64)
            recipes.append(Recipe(d['id'], d['name'], d['req'], d['time'], d['cal'], vector))
        return recipes

    def create_user_profile_vector(self) -> np.ndarray:
        """ユーザーの過去の行動履歴から平均ベクトル（好み）を生成"""
        # (デモ用) 和食・肉類・煮込みを強く好むユーザーのベクトルを仮定
        # 次元順: ['和食', '洋食', '中華', '主菜', '副菜', '肉類', '魚介類', 'ベジタリアン', '複合', '辛味', '煮込み', '揚げ物']
        preference_vector = np.array([0.9, 0.2, 0.5, 0.8, 0.2, 0.9, 0.1, 0.1, 0.0, 0.3, 0.7, 0.2], dtype=np.float64)
        return preference_vector

class InventoryManager:
    """データベースから在庫データを取得するクラス (DB班からの情報受け取り窓口)"""
    def get_current_inventory(self) -> List[Ingredient]:
        # --- 実際はDB接続やAPIコール ---
        
        return [
            Ingredient(name='豚肉', quantity=400.0),    # 在庫十分
            Ingredient(name='玉ねぎ', quantity=150.0),   # 在庫十分
            Ingredient(name='じゃがいも', quantity=1000.0),
            Ingredient(name='エビ', quantity=50.0),      # シーフードパスタ(100g必要)には不足
            Ingredient(name='豆腐', quantity=300.0),
            Ingredient(name='豚ひき肉', quantity=40.0), # 麻婆豆腐(50g必要)には不足
        ]