#!/usr/bin/env python3
"""
Extend Your Memory MCP Server
Provides tools for Google Drive, Chrome History, and Mistral OCR integration
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastmcp import FastMCP
from pydantic import BaseModel

# ツールクラスのインポート
from google_drive_tool import GoogleDriveTool
from chrome_history_tool import ChromeHistoryTool
from mistral_ocr_tool import MistralOCRTool

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MCP サーバー初期化
mcp = FastMCP("ExtendMemory")

# ツールインスタンス
google_drive_tool = GoogleDriveTool()
chrome_history_tool = ChromeHistoryTool()
mistral_ocr_tool = MistralOCRTool()

class Document(BaseModel):
    content: str
    metadata: Dict[str, Any]
    file_id: Optional[str] = None
    title: Optional[str] = None
    mime_type: Optional[str] = None

class HistoryItem(BaseModel):
    url: str
    title: str
    visit_time: datetime
    visit_count: int

class DateRange(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@mcp.tool()
async def search_google_drive(
    keywords: List[str],
    file_types: Optional[List[str]] = None,
    folder_id: Optional[str] = "root",
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """Google Driveからキーワードに基づいてファイルを検索
    
    Args:
        keywords: 検索キーワードのリスト
        file_types: ファイルタイプのリスト (document, sheet, pdf, presentation)
        folder_id: 検索対象フォルダID (デフォルト: root)
        max_results: 最大結果数 (デフォルト: 50)
    
    Returns:
        検索結果のドキュメントリスト
    """
    try:
        logger.info(f"Google Drive search: keywords={keywords}, file_types={file_types}")
        
        documents = await google_drive_tool.search_files(
            keywords=keywords,
            file_types=file_types,
            folder_id=folder_id,
            max_results=max_results
        )
        
        logger.info(f"Found {len(documents)} documents in Google Drive")
        return documents
        
    except Exception as e:
        logger.error(f"Error in search_google_drive: {e}")
        return []

@mcp.tool()
async def search_chrome_history(
    keywords: List[str],
    days: int = 30,
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """Chrome履歴からキーワードに基づいて検索
    
    Args:
        keywords: 検索キーワードのリスト
        days: 検索対象日数 (デフォルト: 30)
        max_results: 最大結果数 (デフォルト: 50)
    
    Returns:
        検索結果の履歴アイテムリスト
    """
    try:
        logger.info(f"Chrome history search: keywords={keywords}, days={days}")
        
        history_items = await chrome_history_tool.search_history(
            keywords=keywords,
            days=days,
            max_results=max_results
        )
        
        logger.info(f"Found {len(history_items)} items in Chrome history")
        return history_items
        
    except Exception as e:
        logger.error(f"Error in search_chrome_history: {e}")
        return []

@mcp.tool()
async def ocr_pdf_to_markdown(
    file_content: bytes,
    file_name: str,
    language: str = "ja"
) -> str:
    """PDFファイルをMistral OCRでMarkdown変換
    
    Args:
        file_content: PDFファイルのバイナリコンテンツ
        file_name: ファイル名
        language: OCR言語設定 (デフォルト: ja)
    
    Returns:
        Markdown形式のテキスト
    """
    try:
        logger.info(f"OCR processing: {file_name} ({len(file_content)} bytes)")
        
        markdown_result = await mistral_ocr_tool.process_pdf_to_markdown(
            file_content=file_content,
            file_name=file_name,
            language=language
        )
        
        logger.info(f"OCR completed for {file_name}")
        return markdown_result
        
    except Exception as e:
        logger.error(f"Error in ocr_pdf_to_markdown: {e}")
        return f"# {file_name}\n\nError processing PDF: {str(e)}"

@mcp.tool()
async def ocr_image_to_markdown(
    image_content: bytes,
    image_name: str,
    language: str = "ja"
) -> str:
    """画像ファイルをMistral OCRでMarkdown変換
    
    Args:
        image_content: 画像ファイルのバイナリコンテンツ
        image_name: 画像ファイル名
        language: OCR言語設定 (デフォルト: ja)
    
    Returns:
        Markdown形式のテキスト
    """
    try:
        logger.info(f"Image OCR processing: {image_name} ({len(image_content)} bytes)")
        
        markdown_result = await mistral_ocr_tool.process_image_to_markdown(
            image_content=image_content,
            image_name=image_name,
            language=language
        )
        
        logger.info(f"Image OCR completed for {image_name}")
        return markdown_result
        
    except Exception as e:
        logger.error(f"Error in ocr_image_to_markdown: {e}")
        return f"# {image_name}\n\nError processing image: {str(e)}"

@mcp.tool()
async def list_google_drive_files(
    folder_id: str = "root"
) -> List[Dict[str, Any]]:
    """Google Driveの指定フォルダ内ファイル一覧を取得
    
    Args:
        folder_id: フォルダID (デフォルト: root)
    
    Returns:
        ファイル一覧
    """
    try:
        logger.info(f"Listing Google Drive files in folder: {folder_id}")
        
        files = await google_drive_tool.list_files_in_folder(folder_id)
        
        logger.info(f"Found {len(files)} files in folder {folder_id}")
        return files
        
    except Exception as e:
        logger.error(f"Error in list_google_drive_files: {e}")
        return []

@mcp.tool()
async def get_recent_chrome_history(
    hours: int = 24,
    max_results: int = 100
) -> List[Dict[str, Any]]:
    """最近のChrome履歴を取得
    
    Args:
        hours: 取得対象時間 (デフォルト: 24)
        max_results: 最大結果数 (デフォルト: 100)
    
    Returns:
        最近の履歴アイテムリスト
    """
    try:
        logger.info(f"Getting recent Chrome history: {hours} hours, max {max_results}")
        
        recent_history = await chrome_history_tool.get_recent_history(
            hours=hours,
            max_results=max_results
        )
        
        logger.info(f"Found {len(recent_history)} recent history items")
        return recent_history
        
    except Exception as e:
        logger.error(f"Error in get_recent_chrome_history: {e}")
        return []

@mcp.tool()
async def check_tools_status() -> Dict[str, Any]:
    """各ツールの状態をチェック
    
    Returns:
        ツール状態の辞書
    """
    try:
        status = {
            "google_drive": {
                "service_initialized": google_drive_tool.service is not None,
                "credentials_found": google_drive_tool.credentials is not None
            },
            "chrome_history": {
                "history_path_found": chrome_history_tool.chrome_history_path is not None,
                "history_path": chrome_history_tool.chrome_history_path
            },
            "mistral_ocr": await mistral_ocr_tool.check_api_status(),
            "mcp_server": {
                "status": "running",
                "tools_count": len(mcp.tools)
            }
        }
        
        logger.info("Tools status checked")
        return status
        
    except Exception as e:
        logger.error(f"Error checking tools status: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    logger.info("Starting Extend Your Memory MCP Server...")
    logger.info("Available tools:")
    for tool_name in ["search_google_drive", "search_chrome_history", "ocr_pdf_to_markdown", 
                      "ocr_image_to_markdown", "list_google_drive_files", 
                      "get_recent_chrome_history", "check_tools_status"]:
        logger.info(f"  - {tool_name}")
    
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        logger.error(f"MCP Server error: {e}")
        raise