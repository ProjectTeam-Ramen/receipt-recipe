from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.database import Base, engine

# routers
from .routers.auth_routes import router as auth_router
from .routers.ingredients import router as ingredients_router
from .routers.receipts import router as receipts_router
from .routers.users import router as users_router

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


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


# mount routers under the API version prefix to match the design doc base URL (/api/v1)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(
    ingredients_router, prefix="/api/v1/ingredients", tags=["ingredients"]
)
app.include_router(receipts_router, prefix="/api/v1/receipts", tags=["receipts"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
