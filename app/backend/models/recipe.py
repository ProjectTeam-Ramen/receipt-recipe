from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

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

    recipe_foods = relationship(
        "RecipeFood",
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
