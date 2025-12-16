"""Router package for API endpoints."""

from . import recipes as recipes  # export module instead of router instance
from .auth_routes import router as auth_routes
from .ingredient_abstractions import router as ingredient_abstractions
from .ingredients import router as ingredients
from .receipts import router as receipts
from .users import router as users

__all__ = [
    "auth_routes",
    "receipts",
    "users",
    "ingredients",
    "recipes",
    "ingredient_abstractions",
]
