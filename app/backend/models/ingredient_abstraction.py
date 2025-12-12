from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.backend.database import Base


class IngredientAbstraction(Base):
    __tablename__ = "ingredient_abstractions"

    abstraction_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    normalized_text = Column(String(255), nullable=False, unique=True, index=True)
    original_text = Column(String(255), nullable=True)
    resolved_food_name = Column(String(255), nullable=False)
    food_id = Column(
        Integer,
        ForeignKey("foods.food_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    confidence = Column(Numeric(5, 4), nullable=True)
    source = Column(String(50), nullable=False, default="ocr_predict")
    metadata_payload = Column("metadata", JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    food = relationship("Food", backref="ingredient_abstractions")
