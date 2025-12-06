"""Router package for API endpoints."""

from .auth_routes import router as auth_routes
from .ingredients import router as ingredients
from .receipts import router as receipts
from .users import router as users

__all__ = ["auth_routes", "receipts", "users", "ingredients"]
