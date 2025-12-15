import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# routers
from app.backend.api.routers.auth_routes import (
    router as auth_router,  # type: ignore[import]
)
from app.backend.api.routers.foods import router as foods_router  # type: ignore[import]
from app.backend.api.routers.ingredient_abstractions import (
    router as ingredient_abstractions_router,  # type: ignore[import]
)
from app.backend.api.routers.ingredients import (
    router as ingredients_router,  # type: ignore[import]
)
from app.backend.api.routers.receipts import (
    router as receipts_router,  # type: ignore[import]
)
from app.backend.api.routers.recipes import (
    router as recipes_router,  # type: ignore[import]
)
from app.backend.api.routers.recommendation import (
    router as recommendation_router,  # type: ignore[import]
)
from app.backend.api.routers.users import router as users_router  # type: ignore[import]
from app.backend.database import Base, engine
from app.backend.services.food_master_loader import sync_food_master
from app.backend.services.recipe_loader import (
    sync_recipe_master,  # type: ignore[import]
)

# アプリケーションインスタンス
app = FastAPI(title="Receipt-Recipe API v1")

# CORS(開発用) - 必要に応じて制限してください
_default_allowed_origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

_env_origins = os.getenv("ALLOWED_ORIGINS")
if _env_origins:
    allowed_origins = [
        origin.strip() for origin in _env_origins.split(",") if origin.strip()
    ]
else:
    allowed_origins = _default_allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
"""
if STATIC_RECIPE_HTML_DIR.exists():
    app.mount(
        RECIPE_PAGES_ROUTE,
        StaticFiles(directory=str(STATIC_RECIPE_HTML_DIR)),
        name="recipe-pages",
    )
"""

@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


# mount routers under the API version prefix to match the design doc base URL (/api/v1)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(foods_router, prefix="/api/v1/foods", tags=["foods"])
app.include_router(
    ingredients_router, prefix="/api/v1/ingredients", tags=["ingredients"]
)
app.include_router(
    ingredient_abstractions_router,
    prefix="/api/v1/ingredient-abstractions",
    tags=["ingredient-abstractions"],
)
app.include_router(
    recommendation_router,
    prefix="/api/v1/recommendation",
    tags=["recommendation"],
)
app.include_router(recipes_router, prefix="/api/v1/recipes", tags=["recipes"])
app.include_router(receipts_router, prefix="/api/v1/receipts", tags=["receipts"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    sync_food_master()
    sync_recipe_master()
