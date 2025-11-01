"""Backlog APIドキュメント取得モジュール"""
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote
import httpx
from bs4 import BeautifulSoup

from src.config import (
    BASE_URL, OUTPUT_DIR, JINA_API_KEY, JINA_API_URL,
    SCRAPING_DELAY, MAX_CONCURRENT_REQUESTS, REQUEST_TIMEOUT,
    MAX_RETRIES, FORCE_REFRESH, PRIORITY_PAGES
)
from src.utils.retry import retry_with_backoff
from src.utils.markdown import html_to_markdown, add_frontmatter

logger = logging.getLogger(__name__)


class DocumentFetcher:
    """ドキュメント取得クラス"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        self.fetch_status_file = OUTPUT_DIR / ".fetch_status.json"
        self.fetch_status = self._load_fetch_status()
    
    def _load_fetch_status(self) -> Dict:
        """取得状況を読み込み"""
        if self.fetch_status_file.exists():
            with open(self.fetch_status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"fetched_pages": {}, "total_pages": 0, "last_fetch": None}
    
    def _save_fetch_status(self):
        """取得状況を保存"""
        with open(self.fetch_status_file, "w", encoding="utf-8") as f:
            json.dump(self.fetch_status, f, ensure_ascii=False, indent=2)
    
    async def discover_pages(self) -> List[Dict[str, str]]:
        """Backlog APIドキュメントページを発見"""
        logger.info("Scanning Backlog API documentation structure...")
        
        pages = []
        try:
            response = await self.client.get(BASE_URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # ドキュメントリンクを抽出
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/docs/backlog/' in href:
                    # 相対URLを絶対URLに変換
                    if href.startswith('/'):
                        full_url = f"https://developer.nulab.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    title = link.get_text(strip=True)
                    if title and full_url not in [p['url'] for p in pages]:
                        pages.append({
                            'url': full_url,
                            'title': title,
                            'slug': self._url_to_slug(full_url)
                        })
        except Exception as e:
            logger.error(f"Error discovering pages: {e}")
            # フォールバック: 基本的なページリスト
            pages = self._get_default_pages()
        
        logger.info(f"Found {len(pages)} pages to fetch")
        return pages
    
    def _get_default_pages(self) -> List[Dict[str, str]]:
        """デフォルトページリスト"""
        default_urls = [
            f"{BASE_URL}authentication/",
            f"{BASE_URL}getting-started/",
            f"{BASE_URL}issues/overview/",
            f"{BASE_URL}issues/get-issue-list/",
            f"{BASE_URL}issues/get-issue/",
            f"{BASE_URL}issues/add-issue/",
            f"{BASE_URL}issues/update-issue/",
            f"{BASE_URL}projects/get-project-list/",
            f"{BASE_URL}projects/get-project/",
            f"{BASE_URL}users/get-user-list/",
            f"{BASE_URL}users/get-user/",
            f"{BASE_URL}error-codes/",
        ]
        
        pages = []
        for url in default_urls:
            pages.append({
                'url': url,
                'title': self._url_to_title(url),
                'slug': self._url_to_slug(url)
            })
        return pages
    
    def _url_to_slug(self, url: str) -> str:
        """URLからスラッグを生成"""
        # URLのパス部分を取得
        path = url.replace(BASE_URL, "").rstrip('/')
        return path or "index"
    
    def _url_to_title(self, url: str) -> str:
        """URLからタイトルを生成"""
        slug = self._url_to_slug(url)
        return slug.replace('-', ' ').replace('/', ' - ').title()
    
    def _is_priority_page(self, slug: str) -> bool:
        """優先ページかどうかを判定"""
        return any(slug.startswith(priority) for priority in PRIORITY_PAGES)
    
    async def fetch_page(self, page_info: Dict[str, str], priority: bool = False) -> bool:
        """
        単一ページを取得
        
        Args:
            page_info: ページ情報（url, title, slug）
            priority: 優先ページかどうか
        
        Returns:
            取得成功かどうか
        """
        url = page_info['url']
        slug = page_info['slug']
        title = page_info['title']
        
        # 既に取得済みで、強制更新でない場合はスキップ
        if not FORCE_REFRESH and slug in self.fetch_status.get('fetched_pages', {}):
            logger.debug(f"Skipping already fetched page: {title}")
            return True
        
        try:
            # JINA Reader APIを使用してMarkdown取得
            async def fetch_with_jina():
                # JINA Reader APIのエンドポイント形式: https://r.jina.ai/{url}
                # URLをエンコード
                encoded_url = quote(url, safe='')
                jina_url = f"{JINA_API_URL}/{encoded_url}"
                response = await self.client.get(
                    jina_url,
                    headers={
                        "Authorization": f"Bearer {JINA_API_KEY}",
                        "X-Return-Format": "markdown"
                    }
                )
                response.raise_for_status()
                return response.text
            
            markdown_content = await retry_with_backoff(
                fetch_with_jina,
                max_retries=MAX_RETRIES,
                timeout=REQUEST_TIMEOUT,
                retryable_errors=(httpx.HTTPError, httpx.TimeoutException)
            )
            
            # フロントマターを追加
            metadata = {
                "title": title,
                "url": url,
                "slug": slug,
                "fetched_at": datetime.now().isoformat(),
                "priority": priority
            }
            markdown_content = add_frontmatter(markdown_content, metadata)
            
            # ファイルに保存
            output_path = self._get_output_path(slug)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            # 取得状況を更新
            self.fetch_status.setdefault('fetched_pages', {})[slug] = {
                'title': title,
                'url': url,
                'fetched_at': metadata['fetched_at'],
                'priority': priority
            }
            self._save_fetch_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fetch {title}: {e}")
            return False
    
    def _get_output_path(self, slug: str) -> Path:
        """出力パスを生成"""
        # カテゴリ別に分類
        if slug.startswith('authentication'):
            category = 'authentication'
        elif slug.startswith('error'):
            category = 'errors'
        elif any(slug.startswith(f'{sdk}') for sdk in ['sdks', 'sdk']):
            category = 'sdks'
        else:
            category = 'endpoints'
        
        filename = f"{slug.replace('/', '-')}.md"
        return OUTPUT_DIR / category / filename
    
    async def fetch_all_pages(
        self,
        pages: List[Dict[str, str]],
        priority_only: bool = False
    ) -> tuple[int, int]:
        """
        全ページを取得
        
        Args:
            pages: ページリスト
            priority_only: 優先ページのみ取得するか
        
        Returns:
            (成功数, 総数)
        """
        # 優先ページとそれ以外に分離
        priority_pages = [p for p in pages if self._is_priority_page(p['slug'])]
        other_pages = [p for p in pages if not self._is_priority_page(p['slug'])]
        
        if priority_only:
            target_pages = priority_pages
        else:
            target_pages = pages
        
        total = len(target_pages)
        success = 0
        completed_count = 0
        
        # セマフォで同時実行数を制限
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        
        async def fetch_with_semaphore(page_info, is_priority, page_num, total_pages):
            nonlocal success, completed_count
            async with semaphore:
                page_title = page_info['title']
                logger.info(f"Fetching documentation: [{page_num}/{total_pages}] {page_title}")
                result = await self.fetch_page(page_info, priority=is_priority)
                completed_count += 1
                if result:
                    success += 1
                else:
                    logger.error(f"✗ Skipped [{page_num}/{total_pages}] {page_title} after retries")
                return result
        
        # 優先ページを先に取得
        if not priority_only:
            logger.info(f"Fetching priority pages ({len(priority_pages)} pages)...")
            priority_tasks = [
                fetch_with_semaphore(p, True, i + 1, len(priority_pages))
                for i, p in enumerate(priority_pages)
            ]
            await asyncio.gather(*priority_tasks)
            logger.info(f"Essential documentation ready ({success}/{len(priority_pages)} pages available)")
        
        # 残りのページを取得
        if not priority_only and other_pages:
            logger.info(f"Background fetch: [{len(priority_pages)}/{total}] pages done, fetching remaining...")
            other_tasks = [
                fetch_with_semaphore(p, False, len(priority_pages) + i + 1, total)
                for i, p in enumerate(other_pages)
            ]
            await asyncio.gather(*other_tasks)
            logger.info(f"All documentation ready ({success}/{total} pages available)")
        elif priority_only:
            logger.info(f"Documentation fetch completed ({success}/{total} pages)")
        
        self.fetch_status['total_pages'] = total
        self.fetch_status['last_fetch'] = datetime.now().isoformat()
        self._save_fetch_status()
        
        return success, total
    
    async def close(self):
        """クライアントを閉じる"""
        await self.client.aclose()


async def fetch_documentation(priority_only: bool = False) -> tuple[int, int]:
    """
    ドキュメント取得のエントリーポイント
    
    Args:
        priority_only: 優先ページのみ取得するか
    
    Returns:
        (成功数, 総数)
    """
    fetcher = DocumentFetcher()
    try:
        pages = await fetcher.discover_pages()
        return await fetcher.fetch_all_pages(pages, priority_only=priority_only)
    finally:
        await fetcher.close()
