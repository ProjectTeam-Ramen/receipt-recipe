from .data_models import Ingredient, Recipe
import numpy as np
from typing import List
from datetime import date, timedelta  # 追加: 日付操作のためにインポート

# 最終的なレシピ特徴ベクトルの次元定義 (18次元)
FEATURE_DIMENSIONS = [
    "和食",
    "洋食",
    "中華",
    "主菜",
    "副菜",
    "汁物",
    "デザート",
    "肉類",
    "魚介類",
    "ベジタリアン",
    "複合",
    "その他",
    "辛味",
    "甘味",
    "酸味",
    "煮込み",
    "揚げ物",
    "炒め物",
]


class RecipeDataSource:
    """レシピデータセットからレシピを読み込み、ベクトル化するクラス"""

    def load_and_vectorize_recipes(self) -> List[Recipe]:
        # --- 実際はCSV/DBから読み込み、One-Hot Encodingでベクトルを生成 ---

        raw_recipes_data = [
            # 1. 豚の生姜焼き (和食, 主菜, 肉類, 炒め物)
            {
                "id": 1,
                "name": "豚の生姜焼き",
                "req": {"豚肉": 250.0, "玉ねぎ": 100.0, "醤油": 50.0},
                "time": 20,
                "cal": 450,
                "feats": {"和食": 1, "主菜": 1, "肉類": 1, "炒め物": 1},
            },
            # 2. シーフードパスタ (洋食, 主菜, 魚介類, 煮込み)
            {
                "id": 2,
                "name": "シーフードパスタ",
                "req": {"エビ": 100.0, "パスタ": 200.0, "トマト": 150.0},
                "time": 40,
                "cal": 650,
                "feats": {"洋食": 1, "主菜": 1, "魚介類": 1, "煮込み": 1},
            },
            # 3. 麻婆豆腐 (中華, 主菜, 肉類, 辛味, 煮込み)
            {
                "id": 3,
                "name": "麻婆豆腐",
                "req": {"豆腐": 300.0, "豚ひき肉": 50.0, "豆板醤": 5.0},
                "time": 35,
                "cal": 400,
                "feats": {"中華": 1, "主菜": 1, "肉類": 1, "辛味": 1, "煮込み": 1},
            },
            # 4. かぼちゃの煮物 (和食, 副菜, ベジタリアン, 甘味, 煮込み)
            {
                "id": 4,
                "name": "かぼちゃの煮物",
                "req": {"かぼちゃ": 400.0, "砂糖": 30.0},
                "time": 30,
                "cal": 250,
                "feats": {
                    "和食": 1,
                    "副菜": 1,
                    "ベジタリアン": 1,
                    "甘味": 1,
                    "煮込み": 1,
                },
            },
            # 5. エビマヨ (中華, 副菜, 魚介類, 甘味, 揚げ物)
            {
                "id": 5,
                "name": "エビマヨ",
                "req": {"エビ": 150.0, "マヨネーズ": 50.0, "片栗粉": 20.0},
                "time": 20,
                "cal": 400,
                "feats": {"中華": 1, "副菜": 1, "魚介類": 1, "甘味": 1, "揚げ物": 1},
            },
            # 6. グリーンサラダ (洋食, 副菜, ベジタリアン, 酸味, 生食は無し)
            {
                "id": 6,
                "name": "グリーンサラダ",
                "req": {"レタス": 200.0, "トマト": 100.0, "酢": 10.0},
                "time": 10,
                "cal": 150,
                "feats": {"洋食": 1, "副菜": 1, "ベジタリアン": 1, "酸味": 1},
            },
            # 7. タコライス (複合, 主菜, 炒め物)
            {
                "id": 7,
                "name": "タコライス",
                "req": {"合いびき肉": 200.0, "ご飯": 300.0, "チーズ": 50.0},
                "time": 30,
                "cal": 600,
                "feats": {"複合": 1, "主菜": 1, "肉類": 1, "炒め物": 1},
            },  # 合いびき肉は肉類、チーズは複合ではないが、肉と野菜の複合として扱う
            # 8. キャベツのスープ (洋食, 汁物, ベジタリアン, 煮込み)
            {
                "id": 8,
                "name": "キャベツのスープ",
                "req": {"キャベツ": 300.0, "ブイヨン": 10.0, "水": 500.0},
                "time": 45,
                "cal": 100,
                "feats": {"洋食": 1, "汁物": 1, "ベジタリアン": 1, "煮込み": 1},
            },
        ]

        recipes = []
        for d in raw_recipes_data:
            # One-Hot Encodingの実行: 定義した全次元に合わせてベクトルを生成
            vector = np.array(
                [d["feats"].get(dim, 0) for dim in FEATURE_DIMENSIONS], dtype=np.float64
            )
            recipes.append(
                Recipe(d["id"], d["name"], d["req"], d["time"], d["cal"], vector)
            )
        return recipes

    def create_user_profile_vector(self) -> np.ndarray:
        """ユーザーの過去の行動履歴から平均ベクトル（好み）を生成"""

        # FEATURE_DIMENSIONSの順序と一致する18次元のベクトル
        # (デモ用) 和食・煮込み・甘味を好むユーザーのベクトルを仮定
        # [和食,洋食,中華,主菜,副菜,汁物,デザート,肉類,魚介類,ベジタリアン,複合,その他,辛味,甘味,酸味,煮込み,揚げ物,炒め物]
        preference_vector = np.array(
            [
                0.9,
                0.2,
                0.5,  # ジャンル
                0.8,
                0.5,
                0.3,
                0.1,  # 役割
                0.7,
                0.1,
                0.4,
                0.0,
                0.0,  # 種類
                0.2,
                0.8,
                0.1,  # 味覚 (甘味高)
                0.8,
                0.1,
                0.3,  # テクスチャ (煮込み高)
            ],
            dtype=np.float64,
        )
        return preference_vector


class InventoryManager:
    """データベースから在庫データを取得するクラス"""

    def get_current_inventory(self, user_id: int = 1) -> List[Ingredient]:
        # --- 実際はDBのinventory_summary_viewを参照するAPIコールなど ---

        TODAY = date.today()

        # サンプル在庫データ
        return [
            Ingredient(
                name="豚肉", quantity=400.0, expiration_date=TODAY + timedelta(days=2)
            ),
            Ingredient(
                name="玉ねぎ",
                quantity=150.0,
                expiration_date=TODAY + timedelta(days=15),
            ),
            Ingredient(
                name="じゃがいも",
                quantity=1000.0,
                expiration_date=TODAY + timedelta(days=30),
            ),
            Ingredient(
                name="かぼちゃ",
                quantity=2000.0,
                expiration_date=TODAY + timedelta(days=1),
            ),
            Ingredient(
                name="エビ", quantity=50.0, expiration_date=TODAY + timedelta(days=10)
            ),
            Ingredient(name="豆腐", quantity=300.0, expiration_date=None),
            Ingredient(
                name="豚ひき肉",
                quantity=400.0,
                expiration_date=TODAY + timedelta(days=4),
            ),
            Ingredient(
                name="レタス", quantity=500.0, expiration_date=TODAY + timedelta(days=2)
            ),
            Ingredient(
                name="合いびき肉",
                quantity=500.0,
                expiration_date=TODAY + timedelta(days=7),
            ),
            Ingredient(
                name="キャベツ",
                quantity=500.0,
                expiration_date=TODAY + timedelta(days=5),
            ),
        ]
