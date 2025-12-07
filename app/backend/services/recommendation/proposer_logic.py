from datetime import date, timedelta
from typing import Dict, List, Set, Tuple

import numpy as np

from .data_models import Ingredient, Recipe, UserParameters
from .data_source import FEATURE_DIMENSIONS


class RecipeProposer:
    def __init__(
        self,
        all_recipes: List[Recipe],
        user_inventory: List[Ingredient],
        user_profile_vector: np.ndarray,
    ) -> None:
        self.all_recipes = all_recipes
        self.inventory_dict = {
            ingredient.name: (ingredient.quantity, ingredient.expiration_date)
            for ingredient in user_inventory
        }
        self.user_profile_vector = user_profile_vector
        self.feature_labels = list(FEATURE_DIMENSIONS)

        self.WEIGHT_INVENTORY = 0.7
        self.WEIGHT_PREFERENCE = 0.3
        self.MIN_COVERAGE_THRESHOLD = 0.2
        self.EXPIRATION_BOOST_DAYS = 3
        self.EXPIRATION_BONUS_FACTOR = 0.1

        self.SEASONING_NAMES = {
            "醤油",
            "塩",
            "砂糖",
            "みりん",
            "酒",
            "料理酒",
            "胡椒",
            "こしょう",
            "ごま油",
            "オリーブオイル",
            "酢",
            "味噌",
            "だし",
            "鶏ガラスープの素",
            "片栗粉",
            "小麦粉",
            "豆板醤",
            "ケチャップ",
            "ソース",
            "バター",
            "マヨネーズ",
            "白ごま",
            "すりごま",
            "カレールウ",
            "ケチャップ・ソース",
            "揚げ油",
            "水",
        }

    def _calculate_cosine_similarity(self, recipe_vector: np.ndarray) -> float:
        dot_product = float(np.dot(self.user_profile_vector, recipe_vector))
        norm_user = float(np.linalg.norm(self.user_profile_vector))
        norm_recipe = float(np.linalg.norm(recipe_vector))

        denominator = norm_user * norm_recipe
        if denominator == 0:
            return 0.0
        return dot_product / denominator

    def _calculate_inventory_coverage(self, recipe: Recipe) -> Tuple[float, Set[str]]:
        total_required_amount = 0.0
        total_covered_amount = 0.0
        missing_ingredients: Set[str] = set()

        for name, required_qty in recipe.required_qty.items():
            if name in self.SEASONING_NAMES:
                continue
            inventory_info = self.inventory_dict.get(name)
            stock_qty = inventory_info[0] if inventory_info else 0.0
            total_required_amount += required_qty
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

    def _get_expiration_boost_factor(self, recipe: Recipe) -> float:
        today = date.today()
        deadline = today + timedelta(days=self.EXPIRATION_BOOST_DAYS)

        for name in recipe.required_qty.keys():
            if name in self.SEASONING_NAMES:
                continue
            inventory_info = self.inventory_dict.get(name)
            if not inventory_info:
                continue
            quantity, expiry_date = inventory_info
            if quantity <= 0 or not expiry_date:
                continue
            if today <= expiry_date <= deadline:
                return self.EXPIRATION_BONUS_FACTOR
        return 0.0

    def propose(self, params: UserParameters) -> List[Dict]:
        final_proposals: List[Dict] = []
        try:
            user_vector_values = [float(v) for v in np.ravel(self.user_profile_vector)]
        except Exception:
            user_vector_values = []

        for recipe in self.all_recipes:
            coverage_score, missing = self._calculate_inventory_coverage(recipe)
            if coverage_score < self.MIN_COVERAGE_THRESHOLD:
                continue

            allergies = getattr(params, "allergies", set()) or set()
            if any(ingredient in allergies for ingredient in recipe.required_qty):
                continue

            if (
                recipe.prep_time > params.max_time
                or recipe.calories > params.max_calories
            ):
                continue

            preference_score = self._calculate_cosine_similarity(recipe.feature_vector)
            final_score_base = (
                coverage_score * self.WEIGHT_INVENTORY
                + preference_score * self.WEIGHT_PREFERENCE
            )
            boost_factor = self._get_expiration_boost_factor(recipe)
            final_score = final_score_base * (1 + boost_factor)

            final_proposals.append(
                {
                    "recipe_id": recipe.id,
                    "recipe_name": recipe.name,
                    "final_score": final_score,
                    "coverage_score": coverage_score,
                    "preference_score": preference_score,
                    "user_preference_vector": user_vector_values.copy(),
                    "user_preference_labels": self.feature_labels,
                    "prep_time": recipe.prep_time,
                    "calories": recipe.calories,
                    "is_boosted": boost_factor > 0,
                    "missing_items": sorted(missing),
                    "required_qty": recipe.required_qty,
                    "req_count": len(recipe.required_qty),
                    "image_url": getattr(recipe, "image_url", None),
                }
            )

        final_proposals.sort(key=lambda item: item["final_score"], reverse=True)
        return final_proposals
