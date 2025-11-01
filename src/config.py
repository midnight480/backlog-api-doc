"""設定管理モジュール"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# ベース設定
BASE_URL = "https://developer.nulab.com/ja/docs/backlog/"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/data"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# JINA Reader API設定
JINA_API_KEY = os.getenv("JINA_API_KEY")
JINA_API_URL = "https://r.jina.ai"

# スクレイピング設定
SCRAPING_DELAY = int(os.getenv("SCRAPING_DELAY", "1000"))  # ms
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))
REQUEST_TIMEOUT = 30  # 秒
MAX_RETRIES = 3

# MCPサーバー設定
MCP_PORT = int(os.getenv("MCP_PORT", "58080"))
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")

# データ管理
FORCE_REFRESH = os.getenv("FORCE_REFRESH", "false").lower() == "true"

# 優先ページ定義
PRIORITY_PAGES = [
    "authentication",
    "getting-started",
    "issues/overview",
    "issues/get-issue-list",
    "issues/get-issue",
    "issues/add-issue",
    "issues/update-issue",
    "projects/get-project-list",
    "projects/get-project",
    "users/get-user-list",
    "users/get-user",
    "error-codes",
]

# ディレクトリ構造
DOCS_STRUCTURE = {
    "authentication": "authentication",
    "endpoints": "endpoints",
    "errors": "errors",
    "sdks": "sdks",
}

# 出力ディレクトリの作成
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
for subdir in DOCS_STRUCTURE.values():
    (OUTPUT_DIR / subdir).mkdir(parents=True, exist_ok=True)


def validate_config():
    """設定の妥当性チェック"""
    if not JINA_API_KEY or JINA_API_KEY == "your_jina_api_key_here":
        raise ValueError(
            "JINA_API_KEY is not set. Please set it in .env file."
        )
    return True
