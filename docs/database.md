import os
import io
import cv2  # opencv-python-headless
import numpy as np
import easyocr
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, Boolean, ForeignKey, DECIMAL, TIMESTAMP, TEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, joinedload
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from fastapi.middleware.cors import CORSMiddleware

# --- 1. データベース接続設定 ---
# Docker環境のMySQL('db'コンテナ)に接続
DATABASE_URL = "mysql+pymysql://user:password@db/receipt_recipe_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- EasyOCRリーダーの初期化 (GPUなし) ---
print("EasyOCRリーダーを初期化しています...")
ocr_reader = easyocr.Reader(['ja', 'en'], gpu=False)
print("EasyOCRリーダーの準備が完了しました。")


# --- 2. データベースモデル (SQLAlchemy) ---

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    birthday = Column(Date, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")
    
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
    category_id = Column(Integer, ForeignKey("food_categories.category_id"), nullable=False)
    is_trackable = Column(Boolean, nullable=False, default=True)
    
    category = relationship("FoodCategory", back_populates="foods")
    recipe_foods = relationship("RecipeFood", back_populates="food")

class UserFood(Base):
    __tablename__ = "user_foods"
    user_food_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    food_id = Column(Integer, ForeignKey("foods.food_id"), nullable=False)
    quantity_g = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    expiration_date = Column(Date, nullable=True)
    purchase_date = Column(Date, nullable=True)
    
    user = relationship("User", back_populates="user_foods")
    food = relationship("Food")

class Recipe(Base):
    __tablename__ = "recipes"
    recipe_id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_name = Column(String(255), nullable=False)
    description = Column(TEXT, nullable=True)
    instructions = Column(TEXT, nullable=True)
    cooking_time = Column(Integer, nullable=True)
    image_url = Column(String(1000), nullable=True)
    calories = Column(Integer, nullable=True)

    # 特徴フラグ
    is_japanese = Column(Boolean, nullable=False, default=False)
    is_western = Column(Boolean, nullable=False, default=False)
    is_chinese = Column(Boolean, nullable=False, default=False)
    
    is_main_dish = Column(Boolean, nullable=False, default=False)
    is_side_dish = Column(Boolean, nullable=False, default=False)
    is_soup = Column(Boolean, nullable=False, default=False)
    is_dessert = Column(Boolean, nullable=False, default=False)
    
    type_meat = Column(Boolean, nullable=False, default=False)
    type_seafood = Column(Boolean, nullable=False, default=False)
    type_vegetarian = Column(Boolean, nullable=False, default=False)
    type_composite = Column(Boolean, nullable=False, default=False)
    type_other = Column(Boolean, nullable=False, default=False)
    
    flavor_sweet = Column(Boolean, nullable=False, default=False)
    flavor_spicy = Column(Boolean, nullable=False, default=False)
    flavor_salty = Column(Boolean, nullable=False, default=False)
    
    texture_stewed = Column(Boolean, nullable=False, default=False)
    texture_fried = Column(Boolean, nullable=False, default=False)
    texture_stir_fried = Column(Boolean, nullable=False, default=False)

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
    purchase_datetime = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")
    
    user = relationship("User", back_populates="receipts")
    details = relationship("ReceiptDetail", back_populates="receipt")

class RawFoodMapping(Base):
    __tablename__ = "raw_food_mappings"
    mapping_id = Column(Integer, primary_key=True, autoincrement=True)
    raw_name = Column(String(255), nullable=False, unique=True)
    food_id = Column(Integer, ForeignKey("foods.food_id"), nullable=True)
    status = Column(String(50), nullable=False, default='未処理')
    
    food = relationship("Food")

class ReceiptDetail(Base):
    __tablename__ = "receipt_details"
    detail_id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey("receipts.receipt_id"), nullable=False)
    mapping_id = Column(Integer, ForeignKey("raw_food_mappings.mapping_id"), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    quantity = Column(DECIMAL(10, 2), nullable=False, default=1.00)
    
    receipt = relationship("Receipt", back_populates="details")
    mapping = relationship("RawFoodMapping")


# --- 3. APIスキーマ (Pydanticモデル) ---

class UserFoodSchema(BaseModel):
    food_name: str
    quantity_g: float
    expiration_date: Optional[date]
    class Config:
        orm_mode = True 

class ProposalIngredientSchema(BaseModel):
    food_name: str
    needed_g: float
    in_stock_g: float
    is_sufficient: bool
    is_trackable: bool

class RecipeProposalSchema(BaseModel):
    recipe_id: int
    recipe_name: str
    description: Optional[str]
    image_url: Optional[str]
    cooking_time: Optional[int]
    calories: Optional[int]
    
    # 特徴フラグ
    is_japanese: bool
    is_western: bool
    is_chinese: bool
    is_main_dish: bool
    is_side_dish: bool
    is_soup: bool
    is_dessert: bool
    type_meat: bool
    type_seafood: bool
    type_vegetarian: bool
    type_composite: bool
    type_other: bool
    flavor_sweet: bool
    flavor_spicy: bool
    flavor_salty: bool
    texture_stewed: bool
    texture_fried: bool
    texture_stir_fried: bool

    cover_rate: float
    ingredients: List[ProposalIngredientSchema]

    class Config:
        orm_mode = True

# 【更新】OCR処理結果の詳細スキーマ
class ReceiptProcessItemSchema(BaseModel):
    raw_name: str
    confidence: float
    status: str          # 'mapped' (紐付け済), 'unprocessed' (未処理), 'new' (新規登録)
    mapped_food_id: Optional[int] = None
    mapped_food_name: Optional[str] = None

    class Config:
        orm_mode = True


# --- 4. DBセッション管理 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 5. FastAPI アプリ本体 ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 6. APIエンドポイント ---

@app.get("/")
def read_root():
    return {"message": "レシピ提案APIへようこそ"}

# --- 【更新】レシートOCR & 辞書確認 API ---
# 画像を受け取り、OCRし、辞書(raw_food_mappings)と照合して結果を返す
@app.post("/receipts/upload", response_model=List[ReceiptProcessItemSchema])
async def upload_receipt_for_ocr(
    user_id: int = 1, # クエリパラメータ (テスト用デフォルト: 1)
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # 1. 画像読み込み
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="無効な画像ファイルです。")

        # 2. OCR実行 (前処理: グレースケール化)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ocr_results = ocr_reader.readtext(gray_img, detail=1, paragraph=False)
        
        if not ocr_results:
            return []

        # 3. レシートヘッダー作成 (履歴用)
        new_receipt = Receipt(user_id=user_id, purchase_datetime=datetime.now())
        db.add(new_receipt)
        db.flush() # IDを取得するためにflush

        processed_items = []

        for (bbox, text, prob) in ocr_results:
            raw_text = text.strip()
            if not raw_text:
                continue

            # 4. 辞書(raw_food_mappings) を検索
            mapping = db.query(RawFoodMapping).filter(RawFoodMapping.raw_name == raw_text).first()
            
            current_status = "new"
            food_id = None
            food_name = None

            if mapping:
                # A. 辞書に存在する
                if mapping.food_id:
                    # 紐付け済み ('mapped')
                    current_status = "mapped"
                    food_id = mapping.food_id
                    # Food情報を取得して名前を入れる
                    food_master = db.query(Food).filter(Food.food_id == food_id).first()
                    if food_master:
                        food_name = food_master.food_name
                else:
                    # 辞書にあるが未紐付け ('unprocessed')
                    current_status = "unprocessed"
                    # TODO: ここでスクレイピングを再実行するか検討
            
            else:
                # B. 辞書に存在しない (新規登録 'new')
                # -> ここで「データセットにない場合はスクレイピング」の処理が入る場所
                
                # 例: scrape_result = scraping_module.search(raw_text)
                # if scrape_result:
                #     ...
                
                new_mapping = RawFoodMapping(
                    raw_name=raw_text,
                    status="未処理" # まずは未処理として登録
                )
                db.add(new_mapping)
                db.flush() # mapping_id取得
                
                mapping = new_mapping
                current_status = "new"

            # 5. レシート明細に追加
            new_detail = ReceiptDetail(
                receipt_id=new_receipt.receipt_id,
                mapping_id=mapping.mapping_id,
                quantity=1.00, # 個数や価格はOCRからは難しいので仮置き
                price=0.00
            )
            db.add(new_detail)

            # 6. 結果リストに追加
            processed_items.append(ReceiptProcessItemSchema(
                raw_name=raw_text,
                confidence=float(prob),
                status=current_status,
                mapped_food_id=food_id,
                mapped_food_name=food_name
            ))

        db.commit()
        return processed_items

    except Exception as e:
        db.rollback()
        print(f"OCR/DB Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- レシピ提案 API ---
@app.get("/users/{user_id}/proposals", response_model=List[RecipeProposalSchema])
def get_recipe_proposals(user_id: int, db: Session = Depends(get_db)):
    
    fridge_items = db.query(UserFood).filter(UserFood.user_id == user_id).all()
    fridge_stock = {item.food_id: float(item.quantity_g) for item in fridge_items}

    all_recipes = db.query(Recipe).all()
    proposals = []

    for recipe in all_recipes:
        total_needed = 0
        covered_count = 0
        ingredients_list = []

        if not recipe.recipe_foods:
            continue

        for req in recipe.recipe_foods:
            food_master = req.food
            needed = float(req.quantity_g)
            
            if not food_master.is_trackable:
                ingredients_list.append(ProposalIngredientSchema(
                    food_name=food_master.food_name,
                    needed_g=needed,
                    in_stock_g=float('inf'),
                    is_sufficient=True,
                    is_trackable=False
                ))
                continue

            total_needed += 1
            in_stock = fridge_stock.get(req.food_id, 0.0)
            is_sufficient = (in_stock >= needed)
            
            if is_sufficient:
                covered_count += 1
            
            ingredients_list.append(ProposalIngredientSchema(
                food_name=food_master.food_name,
                needed_g=needed,
                in_stock_g=in_stock,
                is_sufficient=is_sufficient,
                is_trackable=True
            ))

        if total_needed > 0:
            cover_rate = covered_count / total_needed
        else:
            cover_rate = 1.0

        if cover_rate < 0.2:
            continue

        proposals.append(RecipeProposalSchema(
            recipe_id=recipe.recipe_id,
            recipe_name=recipe.recipe_name,
            description=recipe.description,
            image_url=recipe.image_url,
            cooking_time=recipe.cooking_time,
            calories=recipe.calories,
            
            is_japanese=recipe.is_japanese,
            is_western=recipe.is_western,
            is_chinese=recipe.is_chinese,
            is_main_dish=recipe.is_main_dish,
            is_side_dish=recipe.is_side_dish,
            is_soup=recipe.is_soup,
            is_dessert=recipe.is_dessert,
            type_meat=recipe.type_meat,
            type_seafood=recipe.type_seafood,
            type_vegetarian=recipe.type_vegetarian,
            type_composite=recipe.type_composite,
            type_other=recipe.type_other,
            flavor_sweet=recipe.flavor_sweet,
            flavor_spicy=recipe.flavor_spicy,
            flavor_salty=recipe.flavor_salty,
            texture_stewed=recipe.texture_stewed,
            texture_fried=recipe.texture_fried,
            texture_stir_fried=recipe.texture_stir_fried,

            cover_rate=cover_rate,
            ingredients=ingredients_list
        ))

    return sorted(proposals, key=lambda p: p.cover_rate, reverse=True)


# --- 冷蔵庫確認 API ---
@app.get("/users/{user_id}/fridge", response_model=List[UserFoodSchema])
def get_user_fridge(user_id: int, db: Session = Depends(get_db)):
    items = db.query(UserFood).filter(UserFood.user_id == user_id).all()
    return [
        UserFoodSchema(
            food_name=item.food.food_name,
            quantity_g=float(item.quantity_g),
            expiration_date=item.expiration_date
        ) for item in items
    ]