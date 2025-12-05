from enum import Enum

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import relationship

from app.backend.database import Base


class IngredientStatus(str, Enum):
    UNUSED = "unused"
    USED = "used"
    DELETED = "deleted"


class FoodCategory(Base):
    __tablename__ = "food_categories"

    category_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_name = Column(String(100), nullable=False, unique=True)

    foods = relationship(
        "Food",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class Food(Base):
    __tablename__ = "foods"

    food_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    food_name = Column(String(200), nullable=False, unique=True)
    category_id = Column(
        Integer,
        ForeignKey(
            "food_categories.category_id", ondelete="RESTRICT", onupdate="CASCADE"
        ),
        nullable=False,
    )
    is_trackable = Column(Boolean, nullable=False, default=True)

    category = relationship("FoodCategory", back_populates="foods")
    user_foods = relationship("UserFood", back_populates="food")


class UserFood(Base):
    __tablename__ = "user_foods"

    user_food_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    food_id = Column(
        Integer,
        ForeignKey("foods.food_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity_g = Column(Numeric(10, 2), nullable=False, default=0)
    expiration_date = Column(Date, nullable=True)
    purchase_date = Column(Date, nullable=True)
    status = Column(
        SqlEnum(IngredientStatus, name="ingredient_status", native_enum=False),
        nullable=False,
        default=IngredientStatus.UNUSED,
        server_default=IngredientStatus.UNUSED.value,
    )

    food = relationship("Food", back_populates="user_foods")
    user = relationship("User", back_populates="user_foods")
