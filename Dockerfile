# Stage 1: builder - 依存関係をインストールし、仮想環境を構築する
# 計算機サーバーのCUDA 11.7ドライバと互換性のあるイメージを選定
FROM nvcr.io/nvidia/pytorch:22.07-py3 AS builder

# ビルド時に PyPI インデックスを切り替えられるようにする
ARG UV_PYPI_INDEX="https://pypi.org/simple"
ENV UV_PYPI_INDEX=${UV_PYPI_INDEX}

# uvを公式イメージからコピーしてインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# ワーキングディレクトリを設定
WORKDIR /workspace

# ビルドに必要なファイルをすべてコピー
COPY pyproject.toml README.md ./
COPY uv.lock* ./

# 仮想環境を作成し、依存関係を同期
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    uv sync --frozen

# Stage 2: final - 実行環境を構築する
FROM nvcr.io/nvidia/pytorch:22.07-py3

# 実行ステージでもビルド時にインデックスを切り替えられるようにARG/ENVを用意
ARG UV_PYPI_INDEX="https://pypi.org/simple"
ENV UV_PYPI_INDEX=${UV_PYPI_INDEX}

# uvをインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# MySQLクライアントをインストール
RUN apt-get update && apt-get install -y mysql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# プロジェクトファイルをコピー
COPY . .

# 開発環境かどうかを判定するARG
ARG INSTALL_DEV=true
# UV の PyPI インデックスを切り替可能にする（ビルド時に --build-arg UV_PYPI_INDEX=... を渡す）

# pyproject.tomlから依存関係をインストール
RUN if [ "$INSTALL_DEV" = "true" ]; then \
    uv sync --extra dev --frozen; \
    else \
    uv sync --frozen; \
    fi

# 開発環境では常にdev依存関係をインストール
RUN uv sync --extra dev --frozen

# 非ルートユーザーを作成
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /workspace

USER appuser

EXPOSE 8000

# devcontainer用: コンテナを起動したままにする
CMD ["tail", "-f", "/dev/null"]
