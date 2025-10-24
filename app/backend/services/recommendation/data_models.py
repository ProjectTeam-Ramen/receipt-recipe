from typing import Dict, List, Set, Tuple
from collections import namedtuple
import numpy as np

# ユーザーが設定するパラメータ 
UserParameters = namedtuple('UserParameters', ['max_time', 'max_calories', 'allergies'])

# 在庫アイテムの定義
class Ingredient:
    """現在の在庫アイテム（データベースから取得）"""
    def __init__(self, name: str, quantity: float, expiration_date = None):
        self.name = name
        self.quantity = quantity # 単位はグラム(g)に統一
        self.expiration_date = expiration_date

# レシピの定義
class Recipe:
    """提案候補のレシピ"""
    def __init__(self, id: int, name: str, req_qty: Dict[str, float], 
                 prep_time: int, calories: int, feature_vector: np.ndarray):
        self.id = id
        self.name = name
        self.required_qty = req_qty  # {'食材名': 必要量(g)}
        self.prep_time = prep_time   # 調理時間（分）
        self.calories = calories     # カロリー（kcal）
        self.feature_vector = feature_vector # コサイン類似度計算用の特徴ベクトル