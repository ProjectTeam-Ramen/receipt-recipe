# Stage 1: builder
# Python 3.8.13 slim (Debian Bullseye)
FROM python:3.8.13-slim AS builder

# uvのインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /workspace

# 依存関係定義ファイルのみコピー (uv.lockはコピーしない！)
COPY pyproject.toml README.md ./

# 仮想環境を作成
RUN uv venv /opt/venv

# 【重要】CPU版のPyTorchを先にインストールして容量を節約
# これにより数GBのGPUライブラリ(CUDA)が除外されます
RUN uv pip install torch torchvision torchaudio \
    --python /opt/venv \
    --index-url https://download.pytorch.org/whl/cpu

# 残りの依存関係をインストール
# すでにtorchが入っているため、そこはスキップされ、他がインストールされます
RUN uv pip install . --python /opt/venv

# Stage 2: final
FROM python:3.8.13-slim

# 必要なシステムパッケージ (OpenCV等用)
RUN apt-get update && apt-get install -y \
    default-mysql-client \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# ビルドした仮想環境をコピー
COPY --from=builder /opt/venv /opt/venv

# パスを通す (これで python コマンドが仮想環境のものになります)
ENV PATH="/opt/venv/bin:$PATH"

# アプリケーションコードをコピー
COPY . .

# ユーザー設定
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /workspace

USER appuser

EXPOSE 8000

# 起動コマンド
CMD ["python", "-m", "uvicorn", "app.backend.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
