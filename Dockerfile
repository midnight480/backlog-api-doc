FROM python:3.11-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY src/ ./src/
COPY mcp-server-stdio.py ./

# 非rootユーザー作成
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# データディレクトリ作成
RUN mkdir -p /app/data

# ポート公開
EXPOSE 58080

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:58080/health || exit 1

# 起動コマンド
CMD ["python", "-m", "uvicorn", "src.mcp_server:app", "--host", "0.0.0.0", "--port", "58080"]
