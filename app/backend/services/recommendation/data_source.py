import http.client # 標準のHTTPクライアント
import json        # JSONのパース用
import ssl         # HTTPS通信用
import numpy as np
from typing import List, Dict, Union, Any, Tuple
from datetime import date, datetime, timedelta 
from .data_models import Ingredient, Recipe # Ingredient, Recipe クラスをインポート

# 最終的なレシピ特徴ベクトルの次元定義 (18次元) - 定数として保持
FEATURE_DIMENSIONS = [
    '和食', '洋食', '中華', '主菜', '副菜', '汁物', 'デザート',
    '肉類', '魚介類', 'ベジタリアン', '複合', 'その他', 
    '辛味', '甘味', '酸味', '煮込み', '揚げ物', '炒め物' 
]

class RecipeDataSource:
    """レシピマスター、特徴ベクトル、ユーザー行動履歴を取得・加工する"""
    
    def __init__(self, db_api_url: str = 'db-service'): # ホスト名のみを保持
        self.db_api_host = db_api_url
        self._recipe_vector_map: Dict[int, np.ndarray] = {}

    def _execute_sync_http_request(self, path: str) -> List[Dict[str, Any]]:
        """同期的にAPIに接続し、データを取得する（標準ライブラリ版）"""
        
        conn = http.client.HTTPConnection(self.db_api_host, timeout=10)
        
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            
            if 200 <= response.status < 300:
                data = response.read().decode('utf-8')
                return json.loads(data) # JSONをパースして返す
            else:
                print(f"HTTP ERROR: {response.status} for {path}")
                return []
        except Exception as e:
            # 接続失敗、タイムアウト、JSONパースエラーなどをキャッチ
            print(f"CONNECTION ERROR: Failed to fetch data from {path}. Reason: {e}")
            return []
        finally:
            conn.close()


    def _fetch_data_from_api(self, endpoint: str) -> List[Dict[str, Any]]:
        """APIに接続し、データを取得するロジック"""
        # APIパスを定義: /api/v1/{endpoint}
        path = f"/api/v1/{endpoint}" 
        return self._execute_sync_http_request(path)


    def load_and_vectorize_recipes(self) -> List[Recipe]:
        """APIから全レシピデータとその特徴を取得し、Recipeオブジェクトに変換する。"""
        
        # APIからレシピマスターデータを取得
        raw_recipes_data = self._fetch_data_from_api("recipes/master")
        
        recipes = []
        for d in raw_recipes_data:
            # 1. 特徴ベクトルを生成
            vector = np.array([d['features'].get(dim, 0) for dim in FEATURE_DIMENSIONS], dtype=np.float64)
            
            # 2. Recipeオブジェクトを生成
            recipe_obj = Recipe(
                id=d['id'],
                name=d['name'],
                prep_time=d['prep_time'],
                calories=d['calories'],
                req_qty=d['required_qty'],
                feature_vector=vector
            )
            recipes.append(recipe_obj)
            self._recipe_vector_map[d['id']] = vector
            
        return recipes

    def create_user_profile_vector(self, user_id: int) -> np.ndarray:
        """APIからユーザーの行動履歴を取得し、重み付き平均ベクトルを生成する。"""
        
        # 1. 履歴データを取得
        raw_history = self._fetch_data_from_api(f"user/{user_id}/history")
        
        total_preference_vector = np.zeros(len(FEATURE_DIMENSIONS), dtype=np.float64)
        total_weight = 0.0
        now = datetime.now()
        
        # 2. 履歴をループし、重み付き平均を計算
        for record in raw_history:
            recipe_id = record.get('recipe_id')
            if not isinstance(recipe_id, int):
                 continue 

            recipe_vector = self._recipe_vector_map.get(recipe_id)
            if recipe_vector is None:
                continue 
            
            completed_at_str = record.get('completed_at')
            if not completed_at_str:
                continue

            try:
                completed_at = datetime.fromisoformat(completed_at_str.replace('Z', '+00:00'))
            except ValueError:
                continue 

            time_difference_days = (now - completed_at).total_seconds() / (60 * 60 * 24)
            
            WEIGHT_DECAY_RATE = 0.05 
            weight = np.exp(-WEIGHT_DECAY_RATE * time_difference_days)
            
            total_preference_vector += recipe_vector * weight
            total_weight += weight

        if total_weight > 0:
            return total_preference_vector / total_weight
        else:
            # 履歴がない場合、または計算に必要なデータがない場合はゼロベクトルを返す
            return np.zeros(len(FEATURE_DIMENSIONS), dtype=np.float64)


class InventoryManager:
    """データベース側の在庫APIと連携し、最新の集計済み在庫を取得する"""
    
    def __init__(self, db_api_url: str = 'db-service'):
        self.db_api_host = db_api_url
        
    def _execute_sync_http_request(self, path: str) -> List[Dict[str, Any]]:
        """同期的にAPIに接続し、データを取得する（標準ライブラリ版）"""
        
        conn = http.client.HTTPConnection(self.db_api_host, timeout=10)
        
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            
            if 200 <= response.status < 300:
                data = response.read().decode('utf-8')
                return json.loads(data) # JSONをパースして返す
            else:
                print(f"HTTP ERROR: {response.status} for {path}")
                return []
        except Exception as e:
            print(f"CONNECTION ERROR: Failed to fetch data from {path}. Reason: {e}")
            return []
        finally:
            conn.close()

    def get_current_inventory(self, user_id: int = 1) -> List[Ingredient]:
        """
        DBの在庫サマリービューを参照するAPIコールを実行し、在庫データ (Ingredientリスト) を取得する。
        """

        # APIパス: /api/v1/inventory/{user_id}
        path = f"/api/v1/inventory/{user_id}"
        raw_inventory_data = self._execute_sync_http_request(path) # 同期アクセスを実行
        
        inventory_list = []
        for d in raw_inventory_data:
            expiry_date_obj = None
            if 'expiration_date' in d and d['expiration_date'] is not None:
                try:
                    # JSONから得た "YYYY-MM-DD" 形式の文字列をdateオブジェクトに変換
                    expiry_date_obj = datetime.strptime(d['expiration_date'], "%Y-%m-%d").date()
                except ValueError:
                    print(f"Warning: Invalid date format for {d.get('name')}")
                    
            inventory_list.append(
                Ingredient(
                    name=d['name'], 
                    quantity=d['quantity'], 
                    expiration_date=expiry_date_obj 
                )
            )
        return inventory_list
