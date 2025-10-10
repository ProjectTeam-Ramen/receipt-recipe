# Stage 1: builder - 依存関係をインストールし、仮想環境を構築する
# 計算機サーバーのCUDA 11.7ドライバと互換性のあるイメージを選定
FROM nvcr.io/nvidia/pytorch:22.07-py3 AS builder

# uvを公式イメージからコピーしてインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# ワーキングディレクトリを設定
WORKDIR /app

# ビルドに必要なファイルをすべてコピー
COPY pyproject.toml README.md ./
COPY uv.lock* ./

# 仮想環境を作成し、依存関係を同期
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Stage 2: final - 実行環境を構築する
FROM nvcr.io/nvidia/pytorch:22.07-py3

# uvをインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /workspace

# プロジェクトファイルをコピー
COPY . .

# uvを使用してpyproject.tomlから依存関係をシステムにインストール
RUN uv pip install --system --no-deps -e .

# 非ルートユーザーを作成
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /workspace

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]