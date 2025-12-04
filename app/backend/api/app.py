from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# routers
from .routers import auth_routes, receipts, users

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
app.include_router(auth_routes, prefix="/api/v1/auth", tags=["auth"])
app.include_router(receipts, prefix="/api/v1/receipts", tags=["receipts"])
app.include_router(users, prefix="/api/v1/users", tags=["users"])
