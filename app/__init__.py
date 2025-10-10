"""Receipt Recipe Application Package"""

__version__ = "0.1.0"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Receipt Recipe API",
    description="Convert receipts to recipes using AI",
    version="0.1.0",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発時のみ。本番環境では適切に設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Receipt Recipe API is running!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
