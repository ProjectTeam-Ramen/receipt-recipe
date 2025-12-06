from typing import Dict, List, Set, Tuple, Union
from collections import namedtuple
import numpy as np
from datetime import date
from pydantic import BaseModel # ★追加: PydanticのBaseModelをインポート★

# ----------------------------------------------------
# 実行ロジックの内部で使用するクラス (変更なし)
# ----------------------------------------------------

# ユーザーが設定するパラメータ 
UserParameters = namedtuple('UserParameters', ['max_time', 'max_calories', 'allergies'])

# 在庫アイテムの定義
class Ingredient:
    """現在の在庫アイテムの構造"""
    def __init__(self, name: str, quantity: float, expiration_date: Union[date, None] = None):
        self.name = name
        self.quantity = quantity
        self.expiration_date = expiration_date

# レシピの定義
class Recipe:
    """提案候補のレシピの構造"""
    def __init__(self, id: int, name: str, req_qty: Dict[str, float], 
                 prep_time: int, calories: int, feature_vector: np.ndarray):
        self.id = id
        self.name = name
        self.required_qty = req_qty
        self.prep_time = prep_time
        self.calories = calories
        self.feature_vector = feature_vector

# ----------------------------------------------------
# API入出力の定義 (Pydanticモデル)
# ----------------------------------------------------

class RecommendationRequest(BaseModel):
    """フロントエンドから受け取る提案リクエストのJSON構造"""
    user_id: int = 1
    max_time: int = 60
    max_calories: int = 1000
    allergies: Set[str] = set()
