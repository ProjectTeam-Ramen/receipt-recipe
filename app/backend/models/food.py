from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import relationship

from app.backend.database import Base


class IngredientStatus(str, Enum):
    UNUSED = "unused"
    USED = "used"
    DELETED = "deleted"


class InventoryChangeSource(str, Enum):
    MANUAL_ADD = "manual_add"
    MANUAL_CONSUME = "manual_consume"
    OCR_IMPORT = "ocr_import"
    SYNC = "sync"
    ADJUSTMENT = "adjustment"


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
    transactions = relationship(
        "UserFoodTransaction", back_populates="food", cascade="all, delete-orphan"
    )
    recipe_foods = relationship(
        "RecipeFood",
        back_populates="food",
        cascade="all, delete-orphan",
    )


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
        SqlEnum(
            IngredientStatus,
            name="ingredient_status",
            native_enum=False,
            values_callable=lambda enum_cls: [status.value for status in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=IngredientStatus.UNUSED,
        server_default=IngredientStatus.UNUSED.value,
    )

    food = relationship("Food", back_populates="user_foods")
    user = relationship("User", back_populates="user_foods")
    transactions = relationship(
        "UserFoodTransaction",
        back_populates="user_food",
        cascade="all, delete-orphan",
    )


class UserFoodTransaction(Base):
    __tablename__ = "user_food_transactions"

    transaction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
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
    user_food_id = Column(
        Integer,
        ForeignKey("user_foods.user_food_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    delta_g = Column(Numeric(10, 2), nullable=False)
    quantity_after_g = Column(Numeric(10, 2), nullable=False)
    source_type = Column(
        SqlEnum(
            InventoryChangeSource,
            name="inventory_change_source",
            native_enum=False,
            values_callable=lambda enum_cls: [status.value for status in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    source_reference = Column(String(255), nullable=True)
    note = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="transactions")
    food = relationship("Food", back_populates="transactions")
    user_food = relationship("UserFood", back_populates="transactions")
