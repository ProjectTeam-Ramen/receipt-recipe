from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.backend.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    recipe_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipe_name = Column(String(255), nullable=False, unique=True)
    description = Column(String(2000), nullable=True)
    instructions = Column(String(4000), nullable=True)
    cooking_time = Column(Integer, nullable=True)
    calories = Column(Integer, nullable=True)
    image_url = Column(String(1000), nullable=True)
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

    recipe_foods = relationship(
        "RecipeFood",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
    history_entries = relationship(
        "UserRecipeHistory",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )


class RecipeFood(Base):
    __tablename__ = "recipe_foods"

    recipe_food_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    food_id = Column(
        Integer,
        ForeignKey("foods.food_id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity_g = Column(Numeric(10, 2), nullable=False, default=0)

    recipe = relationship("Recipe", back_populates="recipe_foods")
    food = relationship("Food", back_populates="recipe_foods")


class UserRecipeHistory(Base):
    __tablename__ = "user_recipe_history"

    history_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    servings = Column(Numeric(6, 2), nullable=False, default=1.0)
    calories_total = Column(Integer, nullable=True)
    cooked_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    note = Column(String(255), nullable=True)

    recipe = relationship("Recipe", back_populates="history_entries")
    user = relationship("User", back_populates="recipe_history")
