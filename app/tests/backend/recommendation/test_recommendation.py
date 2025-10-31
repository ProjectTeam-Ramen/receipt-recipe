import pytest
import numpy as np
from typing import Dict, List, Set, Tuple

# 必要なクラスをインポート
from app.backend.services.recommendation.data_models import Ingredient, Recipe, UserParameters
from app.backend.services.recommendation.data_source import RecipeDataSource, InventoryManager, FEATURE_DIMENSIONS
from app.backend.services.recommendation.proposer_logic import RecipeProposer
from app.backend.services.recommendation.main import get_proposals_for_demo


# --- フィクスチャ (テスト用のデータの準備) ---

# Recipeオブジェクトのリストを返すフィクスチャ (変更なし)
@pytest.fixture
def recipe_list() -> List[Recipe]:
    """RecipeDataSourceからレシピをロードする"""
    source = RecipeDataSource()
    return source.load_and_vectorize_recipes()

# RecipeProposerのインスタンスを返すフィクスチャ (InventoryManagerからデータを取得するように変更)
@pytest.fixture
def proposer_instance(recipe_list) -> RecipeProposer:
    """RecipeProposerのインスタンスを作成する"""
    
    # データを data_source から直接ロード（最新の仮在庫データを使用）
    inv_manager = InventoryManager()
    current_inventory = inv_manager.get_current_inventory() 
    
    # Preference Vectorをダミーで生成
    user_profile = np.array([0.9, 0.2, 0.5, 0.8, 0.5, 0.3, 0.1, 0.7, 0.1, 0.4, 0.0, 0.0, 0.2, 0.8, 0.1, 0.8, 0.1, 0.3], dtype=np.float64)
    return RecipeProposer(recipe_list, current_inventory, user_profile)


# --- ユニットテストケース ---

def test_inventory_coverage_calculation(proposer_instance, recipe_list):
    """個々のレシピの在庫カバー率が正しく計算されるか検証 (豚の生姜焼きの問題箇所を修正)"""
    
    # 【在庫データの定義とインスタンスの生成】: 
    #   テストに必要な特定の在庫状況を再現するため、ここでInventoryManagerのデータとは異なる
    #   特定の在庫データを持つ新しいProposerインスタンスを生成する。
    
    # 1. テスト用の特定の在庫データを定義
    specific_mock_inventory = [
        Ingredient(name='豚肉', quantity=400.0),    
            Ingredient(name='玉ねぎ', quantity=150.0),   
            Ingredient(name='じゃがいも', quantity=1000.0),
            Ingredient(name='かぼちゃ', quantity=2000.0), 
            Ingredient(name='エビ', quantity=50.0),      
            Ingredient(name='豆腐', quantity=300.0),
            Ingredient(name='豚ひき肉', quantity=400.0),
    ]
    
    # 2. テスト専用のProposerインスタンスを作成
    proposer = RecipeProposer(recipe_list, specific_mock_inventory, proposer_instance.user_profile_vector)
    
    # 3. 豚の生姜焼きのテスト (豚肉不足: 10g/250g)
    recipe_shogayaki = recipe_list[0]
    
    # 必要総量: 250(豚肉) + 100(玉ねぎ) = 350g
    # 賄える量: 10(豚肉) + 100(玉ねぎ) = 110g
    expected_coverage = 110.0 / 350.0  # 約 0.314
    
    coverage, missing = proposer._calculate_inventory_coverage(recipe_shogayaki)
    
    assert coverage == pytest.approx(expected_coverage, abs=1e-3)
    assert "豚肉 (240.0g不足)" in missing
    assert "玉ねぎ" not in missing 

    # 4. 麻婆豆腐のテスト (豚ひき肉不足: 40g/50g)
    recipe_mabo = recipe_list[2]
    # 必要総量: 300(豆腐) + 50(豚ひき肉) = 350g
    # 賄える量: 300(豆腐) + 40(豚ひき肉) = 340g
    expected_coverage_mabo = 340.0 / 350.0 # 約 0.9714
    
    coverage_mabo, missing_mabo = proposer._calculate_inventory_coverage(recipe_mabo)
    
    assert coverage_mabo == pytest.approx(expected_coverage_mabo, abs=1e-3)
    assert "豚ひき肉 (10.0g不足)" in missing_mabo
    

def test_allergy_filtering(proposer_instance):
    """アレルギー食材を含むレシピが提案から除外されるか検証"""
    
    # エビを含むシーフードパスタを除外するパラメータ
    params = UserParameters(max_time=60, max_calories=1000, allergies={'エビ'})
    
    proposals = proposer_instance.propose(params)
    
    recipe_names = [p['recipe_name'] for p in proposals]
    assert "シーフードパスタ" not in recipe_names 
    assert "豚の生姜焼き" in recipe_names
    
def test_time_and_calorie_filtering(proposer_instance):
    """必須の制約（時間・カロリー）フィルタが正しく機能するか検証"""
    
    # 豚の生姜焼き(20分, 450kcal)はOK, かぼちゃの煮物(30分, 250kcal)はNG (時間で)
    params = UserParameters(max_time=25, max_calories=1000, allergies=set())
    
    proposals = proposer_instance.propose(params)
    
    recipe_names = [p['recipe_name'] for p in proposals]
    assert "豚の生姜焼き" in recipe_names
    assert "かぼちゃの煮物" not in recipe_names
    
def test_final_score_ranking(proposer_instance):
    """最終スコアが正しく計算され、順位付けされるか検証"""
    
    # 全レシピがカバー率のしきい値(0.5)を上回る設定にする
    # かぼちゃの煮物はカバー率が0.5ちょうどで除外される可能性があるため、max_coverage_thresholdを一時的に下げる
    proposer_instance.MIN_COVERAGE_THRESHOLD = 0.49
    
    params = UserParameters(max_time=60, max_calories=1000, allergies=set())
    
    proposals = proposer_instance.propose(params)
    
    # 最終スコアが降順（高い順）になっていることを確認
    scores = [p['final_score'] for p in proposals]
    assert scores == sorted(scores, reverse=True)
    
    # 変更を元に戻す
    proposer_instance.MIN_COVERAGE_THRESHOLD = 0.5 

def test_empty_inventory_case():
    """在庫が完全に空の場合、提案がゼロになるか検証"""
    recipe_list = RecipeDataSource().load_and_vectorize_recipes()
    
    # 在庫ゼロのリスト
    empty_inventory = []
    
    proposer = RecipeProposer(recipe_list, empty_inventory, np.ones(len(FEATURE_DIMENSIONS)))
    
    # アレルギー、時間制限なし
    params = UserParameters(max_time=999, max_calories=9999, allergies=set())
    
    proposals = proposer.propose(params)
    
    # すべてのレシピのカバー率が0%となり、MIN_COVERAGE_THRESHOLD (0.5)で除外されるため、提案は空になるはず
    assert len(proposals) == 0

# --- デモンストレーション実行関数 (main.py のロジックを呼び出す) ---

def test_demonstration_run():
    """
    システムの統合的な動作を確認し、結果を出力するデモ用テスト。
    """
    
    # main.py の実行関数を呼び出し
    proposals, user_params = get_proposals_for_demo()
    
    # 提案が空でないことの検証
    assert len(proposals) > 0, "提案可能なレシピが一つもありませんでした。データセットを確認してください。"

    # 結果の表示ロジック (プレゼン/デモ用)
    print("\n\n" + "=" * 60)
    print("           中間発表デモ実行結果 (main.py ロジック)")
    print(f"制約: {user_params.max_time}分, {user_params.max_calories}kcal, アレルギー:{list(user_params.allergies)}")
    print("=" * 60)
    
    for i, p in enumerate(proposals):
        print(f"\n[{i+1}位] レシピ名: {p['recipe_name']}")
        print(f"  > 最終スコア: {p['final_score']:.4f}")
        print(f"  > 内訳: (カバー率: {p['coverage_score']:.2f} x 0.7) + (好みスコア: {p['preference_score']:.2f} x 0.3)")
        if p['missing_items']:
            print(f"  ⚠️ 不足食材: {', '.join(p['missing_items'])}")
        else:
            print("  ✅ 食材は全て揃っています！")
    print("=" * 60)
