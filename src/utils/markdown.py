"""Markdown変換ユーティリティ"""
import re
from typing import Optional
from markdownify import markdownify as md
from bs4 import BeautifulSoup


def clean_markdown(text: str) -> str:
    """Markdownテキストのクリーンアップ"""
    # 余分な空行を削除
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 先頭・末尾の空白を削除
    text = text.strip()
    return text


def html_to_markdown(html: str, base_url: Optional[str] = None) -> str:
    """
    HTMLをMarkdownに変換
    
    Args:
        html: HTML文字列
        base_url: 相対URLを絶対URLに変換する際のベースURL
    
    Returns:
        Markdown形式の文字列
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # ナビゲーション要素を削除
    for nav in soup.find_all(['nav', 'header', 'footer']):
        nav.decompose()
    
    # 不要な要素を削除
    for elem in soup.find_all(['script', 'style', 'noscript']):
        elem.decompose()
    
    # Markdownに変換
    markdown_text = md(
        str(soup),
        heading_style="ATX",
        bullets="-",
        strip=['a', 'img'],
    )
    
    # クリーンアップ
    markdown_text = clean_markdown(markdown_text)
    
    return markdown_text


def add_frontmatter(content: str, metadata: dict) -> str:
    """
    Markdownコンテンツにフロントマターを追加
    
    Args:
        content: Markdownコンテンツ
        metadata: メタデータ辞書
    
    Returns:
        フロントマター付きMarkdown
    """
    yaml_lines = ["---"]
    for key, value in metadata.items():
        yaml_lines.append(f"{key}: {value}")
    yaml_lines.append("---")
    yaml_lines.append("")
    
    return "\n".join(yaml_lines) + content
