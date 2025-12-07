"""Utilities to sync recipe master data from JSON into the database."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session, joinedload

from app.backend.database import SessionLocal
from app.backend.models import Food
from app.backend.models.recipe import Recipe, RecipeFood  # type: ignore[import]

RECIPES_JSON_REL_PATH = Path("data") / "recipes.json"
RECIPE_HTML_REL_PATH = Path("data") / "recipe-list"

FLAG_FIELD_NAMES: Tuple[str, ...] = (
    "is_japanese",
    "is_western",
    "is_chinese",
    "is_main_dish",
    "is_side_dish",
    "is_soup",
    "is_dessert",
    "type_meat",
    "type_seafood",
    "type_vegetarian",
    "type_composite",
    "type_other",
    "flavor_sweet",
    "flavor_spicy",
    "flavor_salty",
    "texture_stewed",
    "texture_fried",
    "texture_stir_fried",
)

_CUISINE_KEYWORDS = {
    "is_western": [
        "ハンバーグ",
        "ムニエル",
        "グラタン",
        "パスタ",
        "シチュー",
        "ソテー",
        "サラダ",
        "ポテト",
        "ビーフシチュー",
        "クリーム",
        "ステーキ",
    ],
    "is_chinese": [
        "麻婆",
        "中華",
        "青椒",
        "酢豚",
        "回鍋",
        "担々",
        "油淋",
        "エビチリ",
        "チリ",
        "炒飯",
        "チャーハン",
        "餃子",
    ],
}

_SIDE_DISH_KEYWORDS = [
    "サラダ",
    "和え",
    "酢の物",
    "南蛮漬け",
    "漬け",
    "ピクルス",
    "マリネ",
]
_SOUP_KEYWORDS = ["スープ", "汁", "味噌汁", "みそ汁", "ポタージュ"]
_DESSERT_KEYWORDS = [
    "ケーキ",
    "プリン",
    "ゼリー",
    "ムース",
    "パフェ",
    "アイス",
    "タルト",
    "パンケーキ",
]

_MEAT_KEYWORDS = [
    "豚",
    "牛",
    "鶏",
    "肉",
    "ベーコン",
    "ハム",
    "ひき肉",
    "ハンバーグ",
    "ステーキ",
]
_SEAFOOD_KEYWORDS = [
    "鮭",
    "サーモン",
    "サバ",
    "鯖",
    "ブリ",
    "アジ",
    "マグロ",
    "タコ",
    "イカ",
    "エビ",
    "えび",
    "カニ",
    "かに",
    "アサリ",
    "あさり",
    "ホタテ",
    "牡蠣",
    "カキ",
    "魚",
]
_VEGETARIAN_KEYWORDS = [
    "野菜",
    "サラダ",
    "豆腐",
    "きのこ",
    "椎茸",
    "しめじ",
    "白菜",
    "キャベツ",
    "大根",
    "ほうれん草",
    "小松菜",
    "レンコン",
    "ごぼう",
    "じゃがいも",
    "ナス",
    "もやし",
]

_FLAVOR_KEYWORDS = {
    "flavor_sweet": ["甘", "蜜", "はちみつ", "ハニー", "照り焼き", "みりん", "砂糖"],
    "flavor_spicy": ["辛", "スパイシー", "カレー", "チリ", "麻婆", "担々", "キムチ"],
    "flavor_salty": ["塩", "塩焼き", "醤油", "しょうゆ", "味噌", "味噌煮"],
}

_TEXTURE_KEYWORDS = {
    "texture_stewed": ["煮", "煮物", "煮込み", "シチュー", "鍋", "カレー", "スープ"],
    "texture_fried": ["揚げ", "フライ", "唐揚", "天ぷら", "カツ", "竜田"],
    "texture_stir_fried": [
        "炒",
        "ソテー",
        "スタミナ",
        "チンジャオ",
        "炒飯",
        "チンジャオロース",
    ],
}

_HTML_DETAIL_CACHE: Optional[Dict[str, Dict[str, str]]] = None


@dataclass(frozen=True)
class _IngredientRow:
    name: str
    quantity_g: Optional[Decimal]


@dataclass(frozen=True)
class _RecipeRow:
    name: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    cooking_time: Optional[int] = None
    calories: Optional[int] = None
    image_url: Optional[str] = None
    ingredients: Sequence[_IngredientRow] = field(default_factory=list)
    flags: Dict[str, bool] = field(default_factory=dict)


def _resolve_json_path() -> Path:
    return Path(__file__).resolve().parents[3] / RECIPES_JSON_REL_PATH


def _resolve_recipe_html_dir() -> Path:
    return Path(__file__).resolve().parents[3] / RECIPE_HTML_REL_PATH


_H1_PATTERN = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_INGREDIENT_SECTION_PATTERN = re.compile(
    r'<div\s+class="ingredients"[^>]*>(.*?)</div>', re.IGNORECASE | re.DOTALL
)
_STEP_SECTION_PATTERN = re.compile(
    r'<div\s+class="steps"[^>]*>(.*?)</div>', re.IGNORECASE | re.DOTALL
)


def _load_recipe_rows() -> List[_RecipeRow]:
    path = _resolve_json_path()
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as fp:
        try:
            payload = json.load(fp)
        except json.JSONDecodeError:
            return []

    if not isinstance(payload, list):
        return []

    html_lookup = _load_html_detail_lookup()
    rows: List[_RecipeRow] = []
    for entry in payload:
        maybe_row = _parse_recipe_entry(entry)
        if maybe_row:
            rows.append(_apply_html_fallbacks(maybe_row, html_lookup))

    return rows


def _parse_recipe_entry(entry: object) -> Optional[_RecipeRow]:
    if not isinstance(entry, dict):
        return None

    name = _coerce_text(entry.get("name"))
    if not name:
        return None

    cooking_time_value = _safe_int(entry.get("cooking_time"))
    calories_value = _safe_int(entry.get("calories"))
    description_value = _coerce_text(entry.get("description"))
    instructions_value = _coerce_text(entry.get("instructions"))
    image_url_value = _coerce_text(entry.get("image_url"))

    ingredients_raw = entry.get("ingredients") or []
    if not isinstance(ingredients_raw, list):
        return None

    ingredients: List[_IngredientRow] = []
    for ingredient in ingredients_raw:
        parsed = _parse_ingredient_entry(ingredient)
        if parsed:
            ingredients.append(parsed)

    if not ingredients:
        return None

    return _RecipeRow(
        name=name,
        description=description_value,
        instructions=instructions_value,
        cooking_time=cooking_time_value,
        calories=calories_value,
        image_url=image_url_value,
        flags=_parse_flag_values(entry),
        ingredients=ingredients,
    )


def _parse_ingredient_entry(entry: object) -> Optional[_IngredientRow]:
    if not isinstance(entry, dict):
        return None
    raw_name = str(entry.get("name") or "").strip()
    if not raw_name:
        return None
    raw_quantity = entry.get("quantity_g")
    return _IngredientRow(name=raw_name, quantity_g=_safe_decimal(raw_quantity))


def _coerce_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        candidate = value.strip()
    else:
        candidate = str(value).strip()
    return candidate or None


def _parse_flag_values(entry: Dict[str, Any]) -> Dict[str, bool]:
    flags_section = entry.get("flags") if isinstance(entry.get("flags"), dict) else None
    result: Dict[str, bool] = {}
    for flag_name in FLAG_FIELD_NAMES:
        candidate: Any = None
        if isinstance(flags_section, dict) and flag_name in flags_section:
            candidate = flags_section[flag_name]
        elif flag_name in entry:
            candidate = entry.get(flag_name)
        result[flag_name] = _coerce_bool(candidate)
    inferred = _infer_flags_from_name(_coerce_text(entry.get("name")))
    for flag_name, inferred_value in inferred.items():
        if not result.get(flag_name) and inferred_value:
            result[flag_name] = True
    return result


def _infer_flags_from_name(name: Optional[str]) -> Dict[str, bool]:
    inferred: Dict[str, bool] = {flag: False for flag in FLAG_FIELD_NAMES}
    if not name:
        return inferred

    inferred.update(_infer_cuisine_flags(name))
    inferred.update(_infer_course_flags(name))
    inferred.update(_infer_type_flags(name))
    inferred.update(_infer_flavor_flags(name))
    inferred.update(_infer_texture_flags(name))
    return inferred


def _contains_keyword(name: str, keywords: Sequence[str]) -> bool:
    lowered = name.lower()
    for keyword in keywords:
        if not keyword:
            continue
        if keyword in name or keyword.lower() in lowered:
            return True
    return False


def _infer_cuisine_flags(name: str) -> Dict[str, bool]:
    result = {"is_japanese": False, "is_western": False, "is_chinese": False}
    if _contains_keyword(name, _CUISINE_KEYWORDS["is_chinese"]):
        result["is_chinese"] = True
    if _contains_keyword(name, _CUISINE_KEYWORDS["is_western"]):
        result["is_western"] = True
    if not result["is_chinese"] and not result["is_western"]:
        result["is_japanese"] = True
    return result


def _infer_course_flags(name: str) -> Dict[str, bool]:
    side = _contains_keyword(name, _SIDE_DISH_KEYWORDS)
    soup = _contains_keyword(name, _SOUP_KEYWORDS)
    dessert = _contains_keyword(name, _DESSERT_KEYWORDS)
    main = not (side or soup or dessert)
    return {
        "is_main_dish": main,
        "is_side_dish": side,
        "is_soup": soup,
        "is_dessert": dessert,
    }


def _infer_type_flags(name: str) -> Dict[str, bool]:
    meat = _contains_keyword(name, _MEAT_KEYWORDS)
    seafood = _contains_keyword(name, _SEAFOOD_KEYWORDS)
    vegetarian = _contains_keyword(name, _VEGETARIAN_KEYWORDS)
    composite = (meat and vegetarian) or (meat and seafood)
    veg_only = vegetarian and not meat and not seafood
    type_other = not (meat or seafood or veg_only or composite)
    return {
        "type_meat": meat,
        "type_seafood": seafood,
        "type_vegetarian": veg_only,
        "type_composite": composite,
        "type_other": type_other,
    }


def _infer_flavor_flags(name: str) -> Dict[str, bool]:
    result: Dict[str, bool] = {flag: False for flag in _FLAVOR_KEYWORDS}
    for flag_name, keywords in _FLAVOR_KEYWORDS.items():
        if _contains_keyword(name, keywords):
            result[flag_name] = True
    return result


def _infer_texture_flags(name: str) -> Dict[str, bool]:
    result: Dict[str, bool] = {flag: False for flag in _TEXTURE_KEYWORDS}
    for flag_name, keywords in _TEXTURE_KEYWORDS.items():
        if _contains_keyword(name, keywords):
            result[flag_name] = True
    return result


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "t"}
    return False


def _load_html_detail_lookup() -> Dict[str, Dict[str, str]]:
    global _HTML_DETAIL_CACHE
    if _HTML_DETAIL_CACHE is not None:
        return _HTML_DETAIL_CACHE

    directory = _resolve_recipe_html_dir()
    lookup: Dict[str, Dict[str, str]] = {}
    if not directory.exists():
        _HTML_DETAIL_CACHE = lookup
        return lookup

    for html_file in sorted(directory.glob("*.html")):
        try:
            raw = html_file.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover - filesystem guard
            continue
        title = _extract_section_text(_H1_PATTERN, raw)
        if not title:
            continue
        ingredients_text = _extract_section_text(_INGREDIENT_SECTION_PATTERN, raw)
        steps_text = _extract_section_text(_STEP_SECTION_PATTERN, raw)
        lookup[title] = {
            "ingredients": ingredients_text or "",
            "instructions": steps_text or "",
            "file_name": html_file.name,
        }

    _HTML_DETAIL_CACHE = lookup
    return lookup


def _extract_section_text(pattern: re.Pattern[str], raw_html: str) -> Optional[str]:
    match = pattern.search(raw_html)
    if not match:
        return None
    return _clean_html_text(match.group(1))


def _clean_html_text(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _apply_html_fallbacks(
    row: _RecipeRow, lookup: Dict[str, Dict[str, str]]
) -> _RecipeRow:
    if _has_text(row.description) and _has_text(row.instructions):
        return row
    details = lookup.get(row.name)
    if not details:
        return row
    description = row.description
    instructions = row.instructions
    if not _has_text(description) and _has_text(details.get("ingredients")):
        description = details.get("ingredients")
    if not _has_text(instructions) and _has_text(details.get("instructions")):
        instructions = details.get("instructions")
    if description is row.description and instructions is row.instructions:
        return row
    return replace(row, description=description, instructions=instructions)


def _has_text(value: Optional[str]) -> bool:
    return bool(value and str(value).strip())


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(round(float(value), 2)))
    except (TypeError, ValueError, ArithmeticError):
        return None


_QUANTITY_REGEX = re.compile(r"([0-9]+(?:\.[0-9]+)?)")


def _estimate_quantity(token: str) -> Decimal:
    match = _QUANTITY_REGEX.search(token)
    if match:
        value = float(match.group(1))
        lowered = token.lower()
        if "kg" in lowered:
            grams = value * 1000
        elif "g" in lowered or "ｇ" in token:
            grams = value
        elif "ml" in lowered:
            grams = value
        elif "大さじ" in token:
            grams = value * 15
        elif "小さじ" in token:
            grams = value * 5
        elif any(
            unit in token
            for unit in [
                "本",
                "個",
                "枚",
                "玉",
                "束",
                "袋",
                "丁",
                "缶",
                "尾",
                "切れ",
                "杯",
                "片",
            ]
        ):
            grams = value * 100
        else:
            grams = value * 50
    else:
        grams = 100.0
    return Decimal(str(round(grams, 2)))


def _normalize_ingredient_name(token: str) -> str:
    token = token.replace("　", " ")
    token = re.sub(r"\(.*?\)", "", token)
    token = re.sub(r"\[.*?\]", "", token)
    token = token.replace("（", "(").replace("）", ")")
    token = token.strip(" ・,，。.")
    parts = token.split()
    return parts[0].strip() if parts else token


def _map_ingredients(
    ingredients: Sequence[_IngredientRow], food_lookup: Dict[str, Food]
) -> List[Tuple[int, Decimal]]:
    mapped: List[Tuple[int, Decimal]] = []
    for ingredient in ingredients:
        name = _normalize_ingredient_name(ingredient.name)
        food = food_lookup.get(name)
        if not food:
            continue  # 非トラッキング食材(調味料など)はスキップ
        food_id = getattr(food, "food_id", None)
        if not isinstance(food_id, int):
            continue
        quantity = ingredient.quantity_g
        if quantity is None:
            quantity = _estimate_quantity(ingredient.name)
        mapped.append((food_id, quantity))
    return mapped


def _refresh_food_lookup(session: Session) -> Dict[str, Food]:
    foods = session.query(Food).all()
    lookup: Dict[str, Food] = {}
    for food in foods:
        name = getattr(food, "food_name", None)
        if isinstance(name, str):
            lookup[name] = food
    return lookup


def _sync_recipe_foods(
    session: Session,
    recipe: Recipe,
    mapped_ingredients: Iterable[Tuple[int, Decimal]],
):
    session.query(RecipeFood).filter(RecipeFood.recipe_id == recipe.recipe_id).delete()
    for ingredient in mapped_ingredients:
        food_id, quantity = ingredient
        session.add(
            RecipeFood(
                recipe_id=recipe.recipe_id,
                food_id=food_id,
                quantity_g=quantity,
            )
        )


def sync_recipe_master() -> None:
    rows = _load_recipe_rows()
    if not rows:
        return

    with SessionLocal() as session:
        food_lookup = _refresh_food_lookup(session)
        existing: Dict[str, Recipe] = {
            str(getattr(recipe, "recipe_name")): recipe
            for recipe in session.query(Recipe)
            .options(joinedload(Recipe.recipe_foods))
            .all()
            if getattr(recipe, "recipe_name", None)
        }

        for row in rows:
            mapped_ingredients = _map_ingredients(row.ingredients, food_lookup)
            recipe = existing.get(row.name)
            if not recipe:
                recipe = Recipe(recipe_name=row.name)
                session.add(recipe)
                session.flush([recipe])
                existing[row.name] = recipe
            _apply_recipe_metadata(recipe, row)
            _sync_recipe_foods(session, recipe, mapped_ingredients)

        session.commit()


def _apply_recipe_metadata(recipe: Recipe, row: _RecipeRow) -> None:
    if _has_text(row.description):
        setattr(recipe, "description", row.description)
    elif not _has_text(getattr(recipe, "description", None)):
        setattr(recipe, "description", f"{row.name}のレシピ")

    if _has_text(row.instructions):
        setattr(recipe, "instructions", row.instructions)

    if row.cooking_time is not None:
        setattr(recipe, "cooking_time", row.cooking_time)
    elif getattr(recipe, "cooking_time", None) is None:
        setattr(recipe, "cooking_time", 30)

    if row.calories is not None:
        setattr(recipe, "calories", row.calories)

    if _has_text(row.image_url):
        setattr(recipe, "image_url", row.image_url)

    for flag_name in FLAG_FIELD_NAMES:
        setattr(recipe, flag_name, bool(row.flags.get(flag_name, False)))
