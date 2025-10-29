import pytest
import numpy as np
from typing import Dict, List, Set

# ★ 必要なファイルのインポート ★
# 実行環境によって相対パスが変わるため、pytest実行パスに合わせたインポートが必要です
# プロジェクトのルートディレクトリから実行する場合、以下のように修正が必要になることがあります:
# from app.backend.services.recommendation.data_models import Ingredient, Recipe, UserParameters
# from app.backend.services.recommendation.data_source import RecipeDataSource, InventoryManager
# from app.backend.services.recommendation.proposer_logic import RecipeProposer

# 仮のインポート（実際の環境に合わせて調整してください）
from app.backend.services.recommendation.data_models import Ingredient, Recipe, UserParameters
from app.backend.services.recommendation.data_source import RecipeDataSource, InventoryManager
from app.backend.services.recommendation.proposer_logic import RecipeProposer


# --- フィクスチャ (テスト用のデータの準備) ---

# Ingredientオブジェクトを返すフィクスチャ
@pytest.fixture
def mock_inventory() -> List[Ingredient]:
    """テスト用の仮在庫データを作成する"""
    return [
        Ingredient(name='豚肉', quantity=10.0),    # 不足
        Ingredient(name='玉ねぎ', quantity=500.0), # 十分
        Ingredient(name='かぼちゃ', quantity=200.0), # 不足 (必要400g)
        Ingredient(name='豚ひき肉', quantity=40.0), # 不足 (必要50g)
        Ingredient(name='エビ', quantity=0.0),      # アレルギーテスト用
        Ingredient(name='パスタ', quantity=1000.0), # 調味料テスト用 (除外されるはず)
    ]

# Recipeオブジェクトのリストを返すフィクスチャ
@pytest.fixture
def recipe_list() -> List[Recipe]:
    """RecipeDataSourceからレシピをロードする"""
    source = RecipeDataSource()
    return source.load_and_vectorize_recipes()

# RecipeProposerのインスタンスを返すフィクスチャ
@pytest.fixture
def proposer_instance(recipe_list, mock_inventory) -> RecipeProposer:
    """RecipeProposerのインスタンスを作成する"""
    # Preference Vectorをダミーで生成
    user_profile = np.array([0.9, 0.2, 0.5, 0.8, 0.5, 0.3, 0.1, 0.7, 0.1, 0.4, 0.0, 0.0, 0.2, 0.8, 0.1, 0.8, 0.1, 0.3], dtype=np.float64)
    return RecipeProposer(recipe_list, mock_inventory, user_profile)


# --- テストケース ---

def test_inventory_coverage_calculation(proposer_instance, recipe_list):
    """個々のレシピの在庫カバー率が正しく計算されるか検証"""
    
    # 1. 豚の生姜焼きのテスト (豚肉不足: 10g/250g)
    recipe_shogayaki = recipe_list[0]
    # 豚肉が10/250=4%, 玉ねぎが100% (調味料除く)
    # 必要総量: 250(豚肉) + 100(玉ねぎ) = 350g
    # 賄える量: 10(豚肉) + 100(玉ねぎ) = 110g
    expected_coverage = 110.0 / 350.0  # 約 0.314
    
    coverage, missing = proposer_instance._calculate_inventory_coverage(recipe_shogayaki)
    
    assert coverage == pytest.approx(expected_coverage, abs=1e-3) # 許容誤差で比較
    assert "豚肉 (240.0g不足)" in missing
    assert "玉ねぎ" not in missing # 玉ねぎは足りているため含まれない

def test_allergy_filtering(proposer_instance):
    """アレルギー食材を含むレシピが提案から除外されるか検証"""
    
    # エビを含むシーフードパスタを除外するパラメータ
    params = UserParameters(max_time=60, max_calories=1000, allergies={'エビ'})
    
    proposals = proposer_instance.propose(params)
    
    # シーフードパスタ (id: 2) が提案リストに含まれていないことを確認
    recipe_names = [p['recipe_name'] for p in proposals]
    assert "シーフードパスタ" not in recipe_names
    
def test_time_and_calorie_filtering(proposer_instance):
    """時間制限（25分）でレシピが正しく除外されるか検証"""
    
    # 豚の生姜焼き(20分, 450kcal)はOK, かぼちゃの煮物(30分, 250kcal)はNG
    params = UserParameters(max_time=25, max_calories=1000, allergies=set())
    
    proposals = proposer_instance.propose(params)
    
    recipe_names = [p['recipe_name'] for p in proposals]
    assert "豚の生姜焼き" in recipe_names
    assert "かぼちゃの煮物" not in recipe_names

def test_final_score_ranking(proposer_instance):
    """最終スコアが正しく計算され、順位付けされるか検証"""
    
    # かぼちゃの煮物 (和食・甘味・煮込み高) は好みスコアが高いはず
    params = UserParameters(max_time=60, max_calories=1000, allergies=set())
    proposals = proposer_instance.propose(params)
    
    # すべてのレシピがMIN_COVERAGE_THRESHOLD(0.5)未満のため、デフォルトではリストが空になる可能性あり
    # => ProposerインスタンスのMIN_COVERAGE_THRESHOLDを一時的に0.0に設定してテスト
    proposer_instance.MIN_COVERAGE_THRESHOLD = 0.0 
    proposals_unfiltered = proposer_instance.propose(params)

    # 少なくとも2つ以上の提案があることを確認
    assert len(proposals_unfiltered) > 1

    # 最終スコアが降順（高い順）になっていることを確認
    scores = [p['final_score'] for p in proposals_unfiltered]
    assert scores == sorted(scores, reverse=True)

# app/tests/backend/recommendation/test_recommendation.py (追記)

# ... 既存のテスト関数群 ...

def test_demonstration_run(proposer_instance):
    """
    システムの統合的な動作を確認し、結果を出力するデモ用テスト。
    (main.pyの実行ロジックを再現)
    """
    # ユーザーパラメータの設定 (デモ用の制約)
    user_params = UserParameters(
        max_time=40,        # 40分以内
        max_calories=500,   # 500 kcal以内
        allergies={'かぼちゃ'}  # エビアレルギー
    )
    
    # RecipeProposerのインスタンスはフィクスチャ(proposer_instance)から取得済み
    proposer = proposer_instance 
    
    # 提案ロジックの実行
    proposals = proposer.propose(user_params)
    
    # ----------------------------------------------------
    # 提案が空でないことの検証（最低限のチェック）
    # ----------------------------------------------------
    assert len(proposals) > 0, "提案可能なレシピが一つもありませんでした。データセットを確認してください。"

    # ----------------------------------------------------
    # 結果の表示ロジック (プレゼン/デモ用)
    # ----------------------------------------------------
    print("\n\n" + "=" * 60)
    print("           中間発表デモ実行結果 (統合版)")
    print(f"制約: {user_params.max_time}分, {user_params.max_calories}kcal, アレルギー:{list(user_params.allergies)}")
    print("=" * 60)
    
    for i, p in enumerate(proposals):
        # main.py の表示ロジックをここに移植
        print(f"\n[{i+1}位] レシピ名: {p['recipe_name']}")
        print(f"  > 最終スコア: {p['final_score']:.4f}")
        print(f"  > 内訳: (カバー率: {p['coverage_score']:.2f} x 0.7) + (好みスコア: {p['preference_score']:.2f} x 0.3)")
        if p['missing_items']:
            print(f"  ⚠️ 不足食材: {', '.join(p['missing_items'])}")
        else:
            print("  ✅ 食材は全て揃っています！")
    print("=" * 60)    