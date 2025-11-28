"""Router package for API endpoints."""

from .auth_routes import router as auth_routes
from .receipts import router as receipts

__all__ = ["auth_routes", "receipts"]
