from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# routers
from .routers import auth_routes, receipts

# アプリケーションインスタンス
app = FastAPI(title="Receipt-Recipe API")

# CORS(開発用) - 必要に応じて制限してください
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_routes, prefix="/auth", tags=["auth"])
app.include_router(receipts, prefix="/receipts", tags=["receipts"])
