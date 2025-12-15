from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# routers
from app.backend.api.routers.auth_routes import (
    router as auth_router,  # type: ignore[import]
)
from app.backend.api.routers.foods import router as foods_router  # type: ignore[import]
from app.backend.api.routers.ingredients import (
    router as ingredients_router,  # type: ignore[import]
)
from app.backend.api.routers.receipts import (
    router as receipts_router,  # type: ignore[import]
)
from app.backend.api.routers.recipes import (
    RECIPE_PAGES_ROUTE,
    STATIC_RECIPE_HTML_DIR,
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
