"""MCPサーバー実装"""
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config import (
    OUTPUT_DIR, FORCE_REFRESH, validate_config, MCP_PORT, MCP_HOST
)
from src.fetch_docs import fetch_documentation

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# グローバル状態
fetch_status = {
    "initialized": False,
    "fetching": False,
    "total_pages": 0,
    "available_pages": 0
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    global fetch_status
    
    # 起動時の処理
    logger.info("Starting Backlog API MCP Server...")
    
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and set JINA_API_KEY")
        raise
    
    # データ存在チェック（実際のMarkdownファイルがあるか確認）
    status_file = OUTPUT_DIR / ".fetch_status.json"
    md_files = list(OUTPUT_DIR.rglob("*.md"))
    data_exists = len(md_files) > 0
    
    logger.info(f"Data check: status_file={status_file.exists()}, md_files={len(md_files)}, data_exists={data_exists}")
    
    if not data_exists or FORCE_REFRESH:
        logger.info("Documentation not found locally. Starting fetch...")
        fetch_status["fetching"] = True
        
        # 即座にMCPサーバーを利用可能にするため、非同期で取得を開始
        async def background_fetch():
            try:
                # 優先ページを先に取得
                priority_success, priority_total = await fetch_documentation(priority_only=True)
                fetch_status["available_pages"] = priority_success
                logger.info(f"Essential documentation ready ({priority_success}/{priority_total} pages available)")
                
                # 残りをバックグラウンドで取得
                total_success, total = await fetch_documentation(priority_only=False)
                fetch_status["total_pages"] = total
                fetch_status["available_pages"] = total_success
                logger.info(f"All documentation ready ({total_success}/{total} pages available)")
            except Exception as e:
                logger.error(f"Error fetching documentation: {e}")
            finally:
                fetch_status["fetching"] = False
                fetch_status["initialized"] = True
        
        # バックグラウンドタスクとして起動
        asyncio.create_task(background_fetch())
    else:
        logger.info("Using existing documentation")
        # 既存データからページ数をカウント
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status = json.load(f)
                    fetch_status["total_pages"] = status.get("total_pages", 0)
                    fetch_status["available_pages"] = len(status.get("fetched_pages", {}))
            except Exception as e:
                logger.warning(f"Error reading status file: {e}")
                # 実際のMarkdownファイル数をカウント
                md_files = list(OUTPUT_DIR.rglob("*.md"))
                fetch_status["total_pages"] = len(md_files)
                fetch_status["available_pages"] = len(md_files)
        else:
            # ステータスファイルがない場合は実際のファイル数をカウント
            md_files = list(OUTPUT_DIR.rglob("*.md"))
            fetch_status["total_pages"] = len(md_files)
            fetch_status["available_pages"] = len(md_files)
        fetch_status["initialized"] = True
    
    logger.info(f"MCP server ready on port {MCP_PORT}")
    
    yield
    
    # シャットダウン時の処理
    logger.info("Shutting down MCP server...")


# FastAPIアプリケーション作成
app = FastAPI(
    title="Backlog API MCP Server",
    description="MCP server for Backlog API documentation",
    lifespan=lifespan
)


# リクエスト/レスポンスモデル
class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None


class GetApiSpecRequest(BaseModel):
    endpoint: str


class GetErrorInfoRequest(BaseModel):
    error_code: str


class HealthResponse(BaseModel):
    status: str
    initialized: bool
    fetching: bool
    total_pages: int
    available_pages: int


# エンドポイント実装
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェック"""
    return HealthResponse(
        status="healthy",
        initialized=fetch_status["initialized"],
        fetching=fetch_status["fetching"],
        total_pages=fetch_status["total_pages"],
        available_pages=fetch_status["available_pages"]
    )


@app.post("/mcp/search_backlog_api")
async def search_backlog_api(request: SearchRequest):
    """Backlog APIドキュメントを検索"""
    try:
        results = await _search_documents(request.query, request.category)
        return JSONResponse({
            "results": results,
            "total": len(results)
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/get_api_spec")
async def get_api_spec(request: GetApiSpecRequest):
    """特定APIの詳細仕様を取得"""
    try:
        logger.info(f"Getting API spec for endpoint: {request.endpoint}")
        spec = await _get_api_spec(request.endpoint)
        if not spec:
            logger.warning(f"API spec not found for endpoint: {request.endpoint}")
            raise HTTPException(status_code=404, detail="API spec not found")
        logger.info(f"API spec found: {spec.get('title', 'Unknown')}")
        return JSONResponse(spec)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get API spec error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/list_api_categories")
async def list_api_categories():
    """APIカテゴリ一覧を取得"""
    try:
        categories = await _list_categories()
        return JSONResponse({"categories": categories})
    except Exception as e:
        logger.error(f"List categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/get_error_info")
async def get_error_info(request: GetErrorInfoRequest):
    """エラーコード情報を取得"""
    try:
        error_info = await _get_error_info(request.error_code)
        if not error_info:
            raise HTTPException(status_code=404, detail="Error code not found")
        return JSONResponse(error_info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get error info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 内部実装関数
async def _search_documents(query: str, category: Optional[str] = None) -> List[Dict]:
    """ドキュメントを検索"""
    results = []
    
    # 検索対象ディレクトリ
    search_dirs = [OUTPUT_DIR]
    if category:
        category_map = {
            "authentication": "authentication",
            "endpoints": "endpoints",
            "errors": "errors",
            "sdks": "sdks"
        }
        if category in category_map:
            search_dirs = [OUTPUT_DIR / category_map[category]]
    
    # Markdownファイルを検索
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        for md_file in search_dir.rglob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 簡単なテキストマッチング（本番環境では全文検索エンジンを使用推奨）
                if query.lower() in content.lower():
                    # フロントマターからメタデータを抽出
                    metadata = _extract_frontmatter(content)
                    results.append({
                        "title": metadata.get("title", md_file.stem),
                        "slug": metadata.get("slug", md_file.stem),
                        "url": metadata.get("url", ""),
                        "category": search_dir.name,
                        "path": str(md_file.relative_to(OUTPUT_DIR))
                    })
            except Exception as e:
                logger.warning(f"Error reading {md_file}: {e}")
                continue
    
    return results


async def _get_api_spec(endpoint: str) -> Optional[Dict]:
    """API仕様を取得"""
    # エンドポイントから検索キーワードを生成
    # 例: "GET /api/v2/issues" -> ["issue", "get", "list"]
    # 例: "GET /api/v2/projects/:projectIdOrKey/files/metadata/:path" -> ["project", "file", "metadata", "get"]
    endpoint_lower = endpoint.lower()
    keywords = []
    
    # HTTPメソッドを取得
    if endpoint_lower.startswith(("get ", "post ", "put ", "delete ", "patch ")):
        method, path = endpoint_lower.split(" ", 1)
        keywords.append(method)
        # パスからキーワードを抽出（パスパラメータを除去）
        # :projectIdOrKey のようなパスパラメータを除去
        path_cleaned = path.replace("/api/v2/", "").replace("/api/2/", "")
        # パスパラメータ（:で始まる部分）を除去
        path_cleaned = re.sub(r':[^/]+', '', path_cleaned)
        # スラッシュをスペースに置換してキーワードを抽出
        path_parts = path_cleaned.replace("/", " ").strip().split()
        keywords.extend([p for p in path_parts if p and p not in ["api", "v2", "2"]])
    else:
        # メソッドがない場合は、パスから直接抽出
        path = endpoint_lower.replace("/api/v2/", "").replace("/api/2/", "")
        path = re.sub(r':[^/]+', '', path)  # パスパラメータを除去
        keywords = path.replace("/", " ").strip().split()
        keywords = [p for p in keywords if p and p not in ["api", "v2", "2"]]
    
    logger.info(f"Searching for API spec with keywords: {keywords}, endpoint: {endpoint}")
    
    # 候補ファイルを検索（関連性スコア付き）
    candidates = []
    for category_dir in ["endpoints", "authentication"]:
        search_dir = OUTPUT_DIR / category_dir
        if not search_dir.exists():
            continue
        
        for md_file in search_dir.rglob("*.md"):
            file_stem = md_file.stem.lower()
            file_path_str = str(md_file).lower()
            
            # 関連性スコアを計算
            score = 0
            matched_keywords = set()
            
            for keyword in keywords:
                # キーワードがファイル名に含まれる
                if keyword in file_stem:
                    score += 3
                    matched_keywords.add(keyword)
                # 単数形・複数形の対応（例: "issues" -> "issue"）
                if keyword.endswith("s") and keyword[:-1] in file_stem:
                    score += 2
                    matched_keywords.add(keyword[:-1])
                elif not keyword.endswith("s") and (keyword + "s") in file_stem:
                    score += 2
                    matched_keywords.add(keyword + "s")
                # ハイフン区切りのチェック（例: "issue-list" に "issue" と "list"）
                if "-" in file_stem:
                    parts = file_stem.split("-")
                    if keyword in parts:
                        score += 2
                        matched_keywords.add(keyword)
                    # 複数形の単語パーツのチェック
                    if keyword.endswith("s") and keyword[:-1] in parts:
                        score += 2
                        matched_keywords.add(keyword[:-1])
            
            # すべての主要キーワードがマッチした場合にボーナス
            method_keywords = [k for k in keywords if k in ["get", "post", "put", "delete", "patch"]]
            path_keywords = [k for k in keywords if k not in method_keywords]
            if method_keywords and any(k in matched_keywords or k in file_stem for k in method_keywords):
                score += 1
            if path_keywords and len([k for k in path_keywords if k in matched_keywords or any(k in part or k[:-1] if k.endswith("s") else (k+"s") in part for part in file_stem.split("-"))]) >= len(path_keywords) * 0.5:
                score += 2
            
            if score > 0:
                candidates.append((score, md_file))
    
    # スコアが高い順にソート、ただしより具体的なマッチを優先
    # 例: "get-issue-list" は "get-list-of-recently-viewed-issues" より優先
    def sort_key(candidate):
        score, md_file = candidate
        file_stem = md_file.stem.lower()
        # より短いファイル名（具体的）を優先
        length_bonus = max(0, 50 - len(file_stem)) / 10
        # 主要キーワードが連続して含まれる場合にボーナス
        keyword_bonus = 0
        if len(keywords) >= 2:
            joined = "-".join(k if not k.endswith("s") else k[:-1] for k in keywords[1:])  # メソッド除く
            if joined in file_stem:
                keyword_bonus = 2
        return score + length_bonus + keyword_bonus
    
    candidates.sort(reverse=True, key=sort_key)
    
    if candidates:
        logger.info(f"Found {len(candidates)} candidates. Top 3: {[(s, str(f.relative_to(OUTPUT_DIR))) for s, f in candidates[:3]]}")
    else:
        logger.warning(f"No candidates found for endpoint: {endpoint}")
    
    # 最適なマッチを見つける
    for score, md_file in candidates:
        try:
            logger.debug(f"Checking candidate: {md_file.name}, score={score}")
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            metadata = _extract_frontmatter(content)
            
            # エンドポイントがコンテンツに含まれているか確認
            # パスパラメータを除去したバージョンも検索対象に追加
            endpoint_no_params = re.sub(r':[^/\s]+', '', endpoint.lower())
            endpoint_patterns = [
                endpoint.lower(),
                endpoint.lower().replace("/api/v2/", ""),
                endpoint.lower().replace("/api/v2/", "/api/2/"),  # バージョン表記の違いに対応
                endpoint_no_params,
                endpoint_no_params.replace("/api/v2/", ""),
                endpoint_no_params.replace("/api/v2/", "/api/2/"),
                " ".join(keywords),
                "/".join(keywords),  # GET/issues 形式
                "/".join([k for k in keywords if k not in ["get", "post", "put", "delete", "patch"]]),  # パス部分のみ
            ]
            # パスパラメータを含むパターン（例: projects.*files.*metadata）
            if len(keywords) >= 3:
                path_keywords = [k for k in keywords if k not in ["get", "post", "put", "delete", "patch"]]
                if len(path_keywords) >= 2:
                    # 順序を考慮したパターン
                    endpoint_patterns.append(".*".join(path_keywords))  # projects.*files.*metadata
                    endpoint_patterns.append("/".join(path_keywords))  # projects/files/metadata
            
            content_lower = content.lower()
            # エンドポイントがコンテンツに含まれているか確認（正規表現パターンもサポート）
            content_has_endpoint = False
            for pattern in endpoint_patterns:
                if ".*" in pattern:
                    # 正規表現パターンの場合
                    if re.search(pattern, content_lower):
                        content_has_endpoint = True
                        break
                else:
                    # 通常の文字列マッチ
                    if pattern in content_lower:
                        content_has_endpoint = True
                        break
            
            # より柔軟なマッチング: スコアが十分高い（4以上）、またはコンテンツにエンドポイントが含まれる
            # ただし、コンテンツにエンドポイントが含まれている場合は優先
            logger.debug(f"  content_has_endpoint={content_has_endpoint}, score={score}")
            if content_has_endpoint:
                logger.info(f"Found match by content: {md_file.name}")
                return {
                    "endpoint": endpoint,
                    "title": metadata.get("title", md_file.stem),
                    "content": content,
                    "metadata": metadata,
                    "path": str(md_file.relative_to(OUTPUT_DIR))
                }
            elif score >= 10:
                logger.info(f"Found match by score: {md_file.name}, score={score}")
                # スコアが非常に高い（10以上）場合は返す
                return {
                    "endpoint": endpoint,
                    "title": metadata.get("title", md_file.stem),
                    "content": content,
                    "metadata": metadata,
                    "path": str(md_file.relative_to(OUTPUT_DIR))
                }
            elif score >= 4:
                # スコアが中程度（4-9）で、コンテンツにエンドポイントがない場合は次の候補を確認
                continue
        except Exception as e:
            logger.warning(f"Error reading {md_file}: {e}")
            continue
    
    # 見つからなかった場合、最初の候補を返す（スコアが十分高い場合、または主要キーワードがマッチする場合）
    if candidates:
        score, md_file = candidates[0]
        # 主要キーワード（path_keywords）がファイル名に含まれている場合は優先
        path_keywords = [k for k in keywords if k not in ["get", "post", "put", "delete", "patch"]]
        file_stem = md_file.stem.lower()
        has_important_keywords = len(path_keywords) >= 2 and any(
            kw in file_stem or (kw.endswith("s") and kw[:-1] in file_stem) 
            for kw in path_keywords[:2]
        )
        
        logger.info(f"Fallback check: {md_file.name}, score={score}, has_important_keywords={has_important_keywords}, path_keywords={path_keywords[:2]}")
        if score >= 8 or has_important_keywords:
            logger.info(f"Returning best candidate (fallback): {md_file.name}, score={score}")
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                metadata = _extract_frontmatter(content)
                return {
                    "endpoint": endpoint,
                    "title": metadata.get("title", md_file.stem),
                    "content": content,
                    "metadata": metadata,
                    "path": str(md_file.relative_to(OUTPUT_DIR))
                }
            except Exception as e:
                logger.warning(f"Error reading {md_file}: {e}")
                import traceback
                logger.warning(traceback.format_exc())
    
    logger.warning(f"No candidates found for endpoint: {endpoint}")
    return None


async def _list_categories() -> List[Dict]:
    """カテゴリ一覧を取得"""
    categories = []
    
    for category_dir in ["authentication", "endpoints", "errors", "sdks"]:
        cat_path = OUTPUT_DIR / category_dir
        if cat_path.exists():
            count = len(list(cat_path.glob("*.md")))
            categories.append({
                "name": category_dir,
                "count": count
            })
    
    return categories


async def _get_error_info(error_code: str) -> Optional[Dict]:
    """エラーコード情報を取得"""
    error_dir = OUTPUT_DIR / "errors"
    if not error_dir.exists():
        return None
    
    # エラーコードを含むファイルを検索
    for md_file in error_dir.rglob("*.md"):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        if error_code in content:
            metadata = _extract_frontmatter(content)
            return {
                "error_code": error_code,
                "content": content,
                "metadata": metadata
            }
    
    return None


def _extract_frontmatter(content: str) -> Dict:
    """フロントマターを抽出"""
    if not content.startswith("---"):
        return {}
    
    try:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_content = parts[1].strip()
            # 簡単なYAMLパース（本番環境ではPyYAMLを使用推奨）
            metadata = {}
            for line in yaml_content.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip().strip('"').strip("'")
            return metadata
    except Exception:
        pass
    
    return {}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
