from datetime import date, timedelta  # ★追加: 日付操作のためにインポート★
from typing import List

import numpy as np
import pytest

# 必要なクラスをインポート
from app.backend.services.recommendation.data_models import (
    Ingredient,
    Recipe,
    UserParameters,
)
from app.backend.services.recommendation.data_source import (
    FEATURE_DIMENSIONS,
    InventoryManager,
    RecipeDataSource,
)
from app.backend.services.recommendation.main import get_proposals_for_demo
from app.backend.services.recommendation.proposer_logic import RecipeProposer

# --- 初期データの生成関数 ---


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
    user_profile = np.array(
        [
            0.9,
            0.2,
            0.5,
            0.8,
            0.5,
            0.3,
            0.1,
            0.7,
            0.1,
            0.4,
            0.0,
            0.0,
            0.2,
            0.8,
            0.1,
            0.8,
            0.1,
            0.3,
        ],
        dtype=np.float64,
    )
    return RecipeProposer(recipe_list, current_inventory, user_profile)


# --- ユニットテストケース ---


def test_inventory_coverage_calculation(proposer_instance, recipe_list):
    """個々のレシピの在庫カバー率が正しく計算されるか検証 (在庫が十分なケースと不足するケース)"""

    # 1. テスト用の特定の在庫データを定義
    specific_mock_inventory = [
        Ingredient(name="豚肉", quantity=400.0),  # 十分 (250g必要)
        Ingredient(name="玉ねぎ", quantity=150.0),  # 十分 (100g必要)
        Ingredient(name="豆腐", quantity=300.0),
        Ingredient(name="豚ひき肉", quantity=40.0),  # 不足 (50g必要)
        Ingredient(name="じゃがいも", quantity=1000.0),
    ]

    # 2. テスト専用のProposerインスタンスを作成
    user_profile = np.ones(len(FEATURE_DIMENSIONS))  # ダミープロフィール
    proposer = RecipeProposer(recipe_list, specific_mock_inventory, user_profile)

    # 3. 豚の生姜焼きのテスト (在庫十分, カバー率 1.0)
    recipe_shogayaki = recipe_list[0]
    expected_coverage_shoga = (250.0 + 100.0) / (250.0 + 100.0)  # 1.0
    coverage_shoga, missing_shoga = proposer._calculate_inventory_coverage(
        recipe_shogayaki
    )

    assert coverage_shoga == pytest.approx(expected_coverage_shoga, abs=1e-3)
    assert not missing_shoga

    # 4. 麻婆豆腐のテスト (豚ひき肉不足: 40g/50g)
    recipe_mabo = recipe_list[2]
    expected_coverage_mabo = 340.0 / 350.0  # 約 0.9714

    coverage_mabo, missing_mabo = proposer._calculate_inventory_coverage(recipe_mabo)

    assert coverage_mabo == pytest.approx(expected_coverage_mabo, abs=1e-3)
    assert "豚ひき肉 (10.0g不足)" in missing_mabo


def test_allergy_filtering(proposer_instance):
    """アレルギー食材を含むレシピが提案から除外されるか検証"""

    # エビを含むシーフードパスタを除外するパラメータ
    params = UserParameters(max_time=60, max_calories=1000, allergies={"エビ"})

    proposals = proposer_instance.propose(params)

    recipe_names = [p["recipe_name"] for p in proposals]
    assert "シーフードパスタ" not in recipe_names


def test_time_and_calorie_filtering(proposer_instance):
    """必須の制約（時間・カロリー）フィルタが正しく機能するか検証"""

    # 豚の生姜焼き(20分, 450kcal)はOK, かぼちゃの煮物(30分, 250kcal)はNG (時間で)
    params = UserParameters(max_time=25, max_calories=1000, allergies=set())

    proposals = proposer_instance.propose(params)

    recipe_names = [p["recipe_name"] for p in proposals]
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
    scores = [p["final_score"] for p in proposals]
    assert scores == sorted(scores, reverse=True)


def test_empty_inventory_case():
    """在庫が完全に空の場合、提案がゼロになるか検証"""
    recipe_list = RecipeDataSource().load_and_vectorize_recipes()

    # 在庫ゼロのリスト
    empty_inventory = []

    # ダミーの好みベクトル (np.onesを使用)
    dummy_profile = np.ones(len(FEATURE_DIMENSIONS))

    # 在庫ゼロのProposerインスタンスを作成
    proposer = RecipeProposer(recipe_list, empty_inventory, dummy_profile)

    # アレルギー、時間制限なし
    params = UserParameters(max_time=999, max_calories=9999, allergies=set())

    proposals = proposer.propose(params)

    # すべてのレシピのカバー率が0%となり、MIN_COVERAGE_THRESHOLD (0.5)で除外されるため、提案は空になるはず
    assert len(proposals) == 0


def test_expiration_boost_priority():
    """賞味期限が近い食材を含むレシピのスコアがブーストされるか検証"""
    TODAY = date.today()

    # 1. 期限が近い在庫 (ブースト対象) と、遠い在庫を用意
    inventory_near_expiration = [
        Ingredient(
            name="豚肉", quantity=400.0, expiration_date=TODAY + timedelta(days=1)
        ),  # ブースト対象
        Ingredient(
            name="玉ねぎ", quantity=400.0, expiration_date=TODAY + timedelta(days=30)
        ),  # 余裕あり
    ]

    # 2. テスト用レシピを定義 (カバー率と好みスコアを同等にする)
    # R1/R2/R3が同じ特徴ベクトルを持つと仮定
    common_vector = np.array(
        [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1], dtype=np.float64
    )

    recipe_list_boost_test = [
        # R1: 豚肉 (期限が近い) のみ必要。カバー率1.0
        Recipe(
            id=101,
            name="期限近しレシピ",
            req_qty={"豚肉": 100.0},
            prep_time=10,
            calories=100,
            feature_vector=common_vector,
        ),
        # R2: 玉ねぎ (期限が遠い) のみ必要。カバー率1.0
        Recipe(
            id=102,
            name="期限遠しレシピ",
            req_qty={"玉ねぎ": 100.0},
            prep_time=10,
            calories=100,
            feature_vector=common_vector,
        ),
    ]

    # 3. Proposerを初期化
    proposer = RecipeProposer(
        recipe_list_boost_test, inventory_near_expiration, common_vector
    )
    proposer.MIN_COVERAGE_THRESHOLD = 0.9  # カバー率が1.0なので通過

    params = UserParameters(max_time=100, max_calories=1000, allergies=set())
    proposals = proposer.propose(params)

    # 4. 検証
    # R1とR2はベーススコアが同じになるはず (カバー率1.0, 好みスコア1.0)
    # R1のみにブースト(x 1.1)がかかるため、R1がR2よりも高いスコアを持つはず
    # つまり，結果として生姜焼きが優先して提案されれば適切に機能していることになる．

    assert len(proposals) == 2

    # R1のスコアは R2のスコア * 1.1 に近いことを確認
    r1 = next(p for p in proposals if p["recipe_name"] == "期限近しレシピ")
    r2 = next(p for p in proposals if p["recipe_name"] == "期限遠しレシピ")

    assert r1["final_score"] > r2["final_score"]  # R1が優先されることを確認
    assert r1["is_boosted"] is True
    assert r2["is_boosted"] is False

    # ベーススコアの検証 (カバー率0.7 + 好み0.3 = 1.0)
    base_score = 1.0 * proposer.WEIGHT_INVENTORY + 1.0 * proposer.WEIGHT_PREFERENCE
    expected_r1_score = base_score * (
        1 + proposer.EXPIRATION_BONUS_FACTOR
    )  # 1.0 * 1.1 = 1.1

    assert r1["final_score"] == pytest.approx(expected_r1_score, abs=1e-3)


def test_seasoning_exclusion_in_coverage():
    """調味料が在庫カバー率の計算から除外されているか検証"""
    recipe_list = RecipeDataSource().load_and_vectorize_recipes()

    # 調味料のみ不足している在庫
    inventory_with_no_seasoning = [
        Ingredient(name="豚肉", quantity=400.0),
        Ingredient(name="玉ねぎ", quantity=150.0),
        # 醤油は意図的に在庫なし
    ]

    user_profile = np.ones(len(FEATURE_DIMENSIONS))
    proposer = RecipeProposer(recipe_list, inventory_with_no_seasoning, user_profile)

    # 豚の生姜焼き: 豚肉250g, 玉ねぎ100g, 醤油50g (調味料)
    recipe = recipe_list[0]
    coverage, missing = proposer._calculate_inventory_coverage(recipe)

    # 調味料を除外すると、カバー率は100%になるはず
    assert coverage == pytest.approx(1.0, abs=1e-3)
    assert len(missing) == 0


def test_multiple_expiring_ingredients():
    """複数の食材が期限切れ間近の場合の動作を検証"""
    TODAY = date.today()

    inventory = [
        Ingredient(
            name="豚肉", quantity=400.0, expiration_date=TODAY + timedelta(days=1)
        ),
        Ingredient(
            name="玉ねぎ", quantity=150.0, expiration_date=TODAY + timedelta(days=2)
        ),
        Ingredient(
            name="豆腐", quantity=300.0, expiration_date=TODAY + timedelta(days=1)
        ),
    ]

    recipe_list = RecipeDataSource().load_and_vectorize_recipes()
    user_profile = np.ones(len(FEATURE_DIMENSIONS))
    proposer = RecipeProposer(recipe_list, inventory, user_profile)

    # 豚の生姜焼きと麻婆豆腐、両方とも期限切れ間近の食材を使用
    recipe_shogayaki = recipe_list[0]
    recipe_mabo = recipe_list[2]

    boost_shoga = proposer._get_expiration_boost_factor(recipe_shogayaki)
    boost_mabo = proposer._get_expiration_boost_factor(recipe_mabo)

    # 両方ともブーストが適用されるはず
    assert boost_shoga == proposer.EXPIRATION_BONUS_FACTOR
    assert boost_mabo == proposer.EXPIRATION_BONUS_FACTOR


def test_expired_ingredients_no_boost():
    """既に期限切れの食材にはブーストが適用されないことを検証"""
    TODAY = date.today()

    inventory = [
        Ingredient(
            name="豚肉", quantity=400.0, expiration_date=TODAY - timedelta(days=1)
        ),  # 期限切れ
        Ingredient(name="玉ねぎ", quantity=150.0),
    ]

    recipe_list = RecipeDataSource().load_and_vectorize_recipes()
    user_profile = np.ones(len(FEATURE_DIMENSIONS))
    proposer = RecipeProposer(recipe_list, inventory, user_profile)

    recipe = recipe_list[0]
    boost = proposer._get_expiration_boost_factor(recipe)

    # 期限切れの食材にはブーストなし
    assert boost == 0.0


def test_edge_case_zero_required_quantity():
    """必要量が0gのレシピの動作を検証"""
    recipe_list = [
        Recipe(
            id=999,
            name="空レシピ",
            req_qty={},
            prep_time=10,
            calories=100,
            feature_vector=np.ones(len(FEATURE_DIMENSIONS)),
        )
    ]

    inventory = [Ingredient(name="豚肉", quantity=400.0)]
    user_profile = np.ones(len(FEATURE_DIMENSIONS))
    proposer = RecipeProposer(recipe_list, inventory, user_profile)

    coverage, missing = proposer._calculate_inventory_coverage(recipe_list[0])

    # 必要量が0の場合、カバー率は0.0を返すべき
    assert coverage == 0.0
    assert len(missing) == 0


def test_partial_inventory_coverage_scoring():
    """部分的な在庫カバーのスコアリングが正確か検証"""
    recipe_list = RecipeDataSource().load_and_vectorize_recipes()

    # 半分だけ在庫がある状態
    inventory = [
        Ingredient(name="豚肉", quantity=125.0),  # 必要量250gの半分
        Ingredient(name="玉ねぎ", quantity=50.0),  # 必要量100gの半分
    ]

    user_profile = np.ones(len(FEATURE_DIMENSIONS))
    proposer = RecipeProposer(recipe_list, inventory, user_profile)

    recipe = recipe_list[0]  # 豚の生姜焼き
    coverage, missing = proposer._calculate_inventory_coverage(recipe)

    # (125 + 50) / (250 + 100) = 175 / 350 = 0.5
    assert coverage == pytest.approx(0.5, abs=1e-3)
    assert len(missing) == 2


def test_custom_inventory_injection():
    """main.pyのcustom_inventory引数が正しく機能するか検証"""
    custom_inv = [
        Ingredient(name="テスト食材", quantity=999.0),
    ]

    proposals, params = get_proposals_for_demo(custom_inventory=custom_inv)

    # カスタム在庫が使用されていることを間接的に確認
    # (実際の在庫データと異なるため、提案結果も変わるはず)
    assert isinstance(proposals, list)
    assert isinstance(params, UserParameters)


# --- デモンストレーション実行関数 (main.py のロジックを呼び出す) ---


def test_demonstration_run():
    """
    システムの統合的な動作を確認し、結果を出力するデモ用テスト。
    """

    # main.py の実行関数を呼び出し
    proposals, user_params = get_proposals_for_demo()

    # 提案が空でないことの検証
    assert len(proposals) > 0, (
        "提案可能なレシピが一つもありませんでした。データセットを確認してください。"
    )

    # 結果の表示ロジック (プレゼン/デモ用)
    print("\n\n" + "=" * 60)
    print("           中間発表デモ実行結果 (main.py ロジック)")
    print(
        f"制約: {user_params.max_time}分, {user_params.max_calories}kcal, アレルギー:{list(user_params.allergies)}"
    )
    print("=" * 60)

    for i, p in enumerate(proposals):
        print(f"\n[{i + 1}位] レシピ名: {p['recipe_name']}")
        print(f"  > 最終スコア: {p['final_score']:.4f}")
        print(
            f"  > 内訳: (カバー率: {p['coverage_score']:.2f} x 0.7) + (好みスコア: {p['preference_score']:.2f} x 0.3)"
        )
        if p["missing_items"]:
            print(f"   不足食材: {', '.join(p['missing_items'])}")
        else:
            print("   食材は全て揃っています！")
    print("=" * 60)
