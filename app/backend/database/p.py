from typing import List, Optional

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    DECIMAL,
    TEXT,
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

# --- 1. データベース接続設定 ---

# Docker環境でMySQLに接続するためのURL
# "mysql+pymysql://[ユーザー名]:[パスワード]@[コンテナ名]/[データベース名]"
# rootで実行したSQLスクリプトに基づき、'user'と'your_password'を使う
# ホスト名は 'localhost' ではなく、Dockerコンテナ名 'db' を指定する
DATABASE_URL = "mysql+pymysql://user:password@db/receipt_recipe_db"
# (もしパスワードが違うなら 'your_password' の部分を修正してくれ)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. データベースモデル (9テーブルの定義) ---
# (SQLAlchemyに、MySQLのテーブルがどんな形か教える)


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    birthday = Column(Date, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")

    # 関連付け (UserからUserFoodやReceiptsを引けるようにする)
    user_foods = relationship("UserFood", back_populates="user")
    receipts = relationship("Receipt", back_populates="user")


class FoodCategory(Base):
    __tablename__ = "food_categories"
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False, unique=True)

    foods = relationship("Food", back_populates="category")


class Food(Base):
    __tablename__ = "foods"
    food_id = Column(Integer, primary_key=True, autoincrement=True)
    food_name = Column(String(200), nullable=False, unique=True)
    category_id = Column(
        Integer, ForeignKey("food_categories.category_id"), nullable=False
    )
    is_trackable = Column(
        Boolean, nullable=False, default=True
    )  # TINYINT(1) は Boolean で

    category = relationship("FoodCategory", back_populates="foods")
    recipe_foods = relationship("RecipeFood", back_populates="food")


class UserFood(Base):
    __tablename__ = "user_foods"
    user_food_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    food_id = Column(Integer, ForeignKey("foods.food_id"), nullable=False)
    quantity_g = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    expiration_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="user_foods")
    food = relationship("Food")  # food側からはuser_foodsを逆引きしない想定


class Recipe(Base):
    __tablename__ = "recipes"
    recipe_id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_name = Column(String(255), nullable=False)
    description = Column(TEXT, nullable=True)
    instructions = Column(TEXT, nullable=True)
    cooking_time = Column(Integer, nullable=True)  # UNSIGNED は Integer で
    image_url = Column(String(1000), nullable=True)

    recipe_foods = relationship("RecipeFood", back_populates="recipe")


class RecipeFood(Base):
    __tablename__ = "recipe_foods"
    recipe_food_id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.recipe_id"), nullable=False)
    food_id = Column(Integer, ForeignKey("foods.food_id"), nullable=False)
    quantity_g = Column(DECIMAL(10, 2), nullable=False, default=0.00)

    recipe = relationship("Recipe", back_populates="recipe_foods")
    food = relationship("Food", back_populates="recipe_foods")


class Receipt(Base):
    __tablename__ = "receipts"
    receipt_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    store_name = Column(String(255), nullable=True)
    purchase_datetime = Column(
        TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    user = relationship("User", back_populates="receipts")
    details = relationship("ReceiptDetail", back_populates="receipt")


class RawFoodMapping(Base):
    __tablename__ = "raw_food_mappings"
    mapping_id = Column(Integer, primary_key=True, autoincrement=True)
    raw_name = Column(String(255), nullable=False, unique=True)
    food_id = Column(Integer, ForeignKey("foods.food_id"), nullable=True)
    status = Column(String(50), nullable=False, default="未処理")

    food = relationship("Food")


class ReceiptDetail(Base):
    __tablename__ = "receipt_details"
    detail_id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey("receipts.receipt_id"), nullable=False)
    mapping_id = Column(
        Integer, ForeignKey("raw_food_mappings.mapping_id"), nullable=False
    )
    price = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    quantity = Column(DECIMAL(10, 2), nullable=False, default=1.00)

    receipt = relationship("Receipt", back_populates="details")
    mapping = relationship("RawFoodMapping")


# --- 3. APIスキーマ (Pydanticモデル) ---
# (APIがJSONでやり取りするデータの形を定義する)


# 冷蔵庫の中身
class UserFoodSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    food_name: str
    quantity_g: float
    expiration_date: Optional[date]


# レシピ提案に必要な材料
class ProposalIngredientSchema(BaseModel):
    food_name: str
    needed_g: float
    in_stock_g: float
    is_sufficient: bool
    is_trackable: bool  # 調味料かどうか


# 最終的に返すレシピ提案
class RecipeProposalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recipe_id: int
    recipe_name: str
    description: Optional[str]
    image_url: Optional[str]
    cover_rate: float  # 在庫カバー率 (0.0 〜 1.0)
    ingredients: List[ProposalIngredientSchema]


# --- 4. データベースセッションの管理 ---


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 5. FastAPI アプリ本体 ---
app = FastAPI()

# --- 6. APIエンドポイントの定義 ---


@app.get("/")
def read_root():
    return {"message": "レシピ提案APIへようこそ"}


# 【君がやりたいこと】
# レシピ提案ロジックがDBから情報を呼び出し、APIがそれを返す
@app.get("/users/{user_id}/proposals", response_model=List[RecipeProposalSchema])
def get_recipe_proposals(user_id: int, db: Session = Depends(get_db)):
    # 1. ユーザーの冷蔵庫の中身(user_foods)を取得
    fridge_items_raw = db.query(UserFood).filter(UserFood.user_id == user_id).all()

    # 扱いやすいように、{food_id: quantity_g} の辞書(dict)に変換
    fridge_stock = {item.food_id: float(item.quantity_g) for item in fridge_items_raw}

    # 2. 全レシピ(recipes)と、それに必要な材料(recipe_foods)を取得
    #    (N+1問題を避けるため 'joinedload' を使うが、まずはシンプルに)
    all_recipes = db.query(Recipe).all()

    proposals = []

    # 3. レシピ提案ロジック (プレゼン資料p.18 [cite: 260-264] の「在庫カバー率」を計算)
    for recipe in all_recipes:
        total_needed_trackable_items = 0
        covered_items = 0
        ingredients_detail_list = []

        if not recipe.recipe_foods:  # 必要な材料が登録されてないレシピはスキップ
            continue

        for req_ingredient in recipe.recipe_foods:
            food_master = req_ingredient.food
            needed_g = float(req_ingredient.quantity_g)

            # (A) 調味料など (is_trackable=false) の場合
            if not food_master.is_trackable:
                ingredients_detail_list.append(
                    ProposalIngredientSchema(
                        food_name=food_master.food_name,
                        needed_g=needed_g,
                        in_stock_g=float("inf"),  # 無限にある
                        is_sufficient=True,
                        is_trackable=False,
                    )
                )
                continue  # カバー率の計算対象外

            # (B) 管理対象 (is_trackable=true) の場合
            total_needed_trackable_items += 1
            in_stock_g = fridge_stock.get(
                req_ingredient.food_id, 0.0
            )  # 冷蔵庫にあればg、なければ0

            is_sufficient = in_stock_g >= needed_g

            if is_sufficient:
                covered_items += 1

            ingredients_detail_list.append(
                ProposalIngredientSchema(
                    food_name=food_master.food_name,
                    needed_g=needed_g,
                    in_stock_g=in_stock_g,
                    is_sufficient=is_sufficient,
                    is_trackable=True,
                )
            )

        # 4. 在庫カバー率の計算
        if total_needed_trackable_items > 0:
            cover_rate = covered_items / total_needed_trackable_items
        else:
            # 必要な材料がすべて調味料だった場合
            cover_rate = 1.0

        # プレゼン資料p.18の「実行性フィルタ: カバー率が20%未満のレシピを除外」
        if cover_rate < 0.2:
            continue

        # 5. 最終的な提案リストに追加
        proposals.append(
            RecipeProposalSchema(
                recipe_id=recipe.recipe_id,
                recipe_name=recipe.recipe_name,
                description=recipe.description,
                image_url=recipe.image_url,
                cover_rate=cover_rate,
                ingredients=ingredients_detail_list,
            )
        )

    # 6. カバー率が高い順に並び替えて返す
    sorted_proposals = sorted(proposals, key=lambda p: p.cover_rate, reverse=True)

    return sorted_proposals


# (おまけ) 冷蔵庫の中身をJSONで確認するAPI
@app.get("/users/{user_id}/fridge", response_model=List[UserFoodSchema])
def get_user_fridge(user_id: int, db: Session = Depends(get_db)):
    fridge_items = db.query(UserFood).filter(UserFood.user_id == user_id).all()

    # スキーマに変換
    results = []
    for item in fridge_items:
        results.append(
            UserFoodSchema(
                food_name=item.food.food_name,  # 関連付け(relationship)を使って名前を取得
                quantity_g=float(item.quantity_g),
                expiration_date=item.expiration_date,
            )
        )

    return results
