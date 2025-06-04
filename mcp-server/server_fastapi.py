#!/usr/bin/env python3
"""
Extend Your Memory MCP Server (FastAPI Implementation)
Provides tools for Google Drive, Chrome History, and Mistral OCR integration
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ツールクラスのインポート
from google_drive_tool import GoogleDriveTool
from chrome_history_tool_v2 import ChromeHistoryTool
from mistral_ocr_tool import MistralOCRTool

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI アプリケーション初期化
app = FastAPI(
    title="Extend Your Memory MCP Server",
    description="MCP Tools for Google Drive, Chrome History, and Mistral OCR",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ツールインスタンス
google_drive_tool = GoogleDriveTool()
chrome_history_tool = ChromeHistoryTool()
mistral_ocr_tool = MistralOCRTool()

# Pydantic モデル
class SearchGoogleDriveRequest(BaseModel):
    keywords: List[str]
    file_types: Optional[List[str]] = None
    folder_id: Optional[str] = "root"
    max_results: int = 50

class SearchChromeHistoryRequest(BaseModel):
    keywords: List[str]
    days: int = 30
    max_results: int = 50

class OCRPDFRequest(BaseModel):
    file_content: bytes
    file_name: str
    language: str = "ja"

class OCRImageRequest(BaseModel):
    image_content: bytes
    image_name: str
    language: str = "ja"

class ListGoogleDriveRequest(BaseModel):
    folder_id: str = "root"

class RecentHistoryRequest(BaseModel):
    hours: int = 24
    max_results: int = 100

# エンドポイント実装
@app.get("/")
async def root():
    return {"message": "Extend Your Memory MCP Server", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/tools/search_google_drive")
async def search_google_drive(request: SearchGoogleDriveRequest):
    """Google Driveからキーワードに基づいてファイルを検索"""
    try:
        logger.info(f"Google Drive search: keywords={request.keywords}")
        
        documents = await google_drive_tool.search_files(
            keywords=request.keywords,
            file_types=request.file_types,
            folder_id=request.folder_id,
            max_results=request.max_results
        )
        
        logger.info(f"Found {len(documents)} documents in Google Drive")
        return documents
        
    except Exception as e:
        logger.error(f"Error in search_google_drive: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/search_chrome_history")
async def search_chrome_history(request: SearchChromeHistoryRequest):
    """Chrome履歴からキーワードに基づいて検索"""
    try:
        logger.info(f"Chrome history search: keywords={request.keywords}")
        
        history_items = await chrome_history_tool.search_history(
            keywords=request.keywords,
            days=request.days,
            max_results=request.max_results
        )
        
        logger.info(f"Found {len(history_items)} items in Chrome history")
        return history_items
        
    except Exception as e:
        logger.error(f"Error in search_chrome_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/ocr_pdf_to_markdown")
async def ocr_pdf_to_markdown(request: OCRPDFRequest):
    """PDFファイルをMistral OCRでMarkdown変換"""
    try:
        logger.info(f"OCR processing: {request.file_name}")
        
        markdown_result = await mistral_ocr_tool.process_pdf_to_markdown(
            file_content=request.file_content,
            file_name=request.file_name,
            language=request.language
        )
        
        logger.info(f"OCR completed for {request.file_name}")
        return {"markdown": markdown_result}
        
    except Exception as e:
        logger.error(f"Error in ocr_pdf_to_markdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/ocr_image_to_markdown")
async def ocr_image_to_markdown(request: OCRImageRequest):
    """画像ファイルをMistral OCRでMarkdown変換"""
    try:
        logger.info(f"Image OCR processing: {request.image_name}")
        
        markdown_result = await mistral_ocr_tool.process_image_to_markdown(
            image_content=request.image_content,
            image_name=request.image_name,
            language=request.language
        )
        
        logger.info(f"Image OCR completed for {request.image_name}")
        return {"markdown": markdown_result}
        
    except Exception as e:
        logger.error(f"Error in ocr_image_to_markdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/list_google_drive_files")
async def list_google_drive_files(request: ListGoogleDriveRequest):
    """Google Driveの指定フォルダ内ファイル一覧を取得"""
    try:
        logger.info(f"Listing Google Drive files in folder: {request.folder_id}")
        
        files = await google_drive_tool.list_files_in_folder(request.folder_id)
        
        logger.info(f"Found {len(files)} files in folder {request.folder_id}")
        return files
        
    except Exception as e:
        logger.error(f"Error in list_google_drive_files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/get_recent_chrome_history")
async def get_recent_chrome_history(request: RecentHistoryRequest):
    """最近のChrome履歴を取得"""
    try:
        logger.info(f"Getting recent Chrome history: {request.hours} hours")
        
        recent_history = await chrome_history_tool.get_recent_history(
            hours=request.hours,
            max_results=request.max_results
        )
        
        logger.info(f"Found {len(recent_history)} recent history items")
        return recent_history
        
    except Exception as e:
        logger.error(f"Error in get_recent_chrome_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools/check_tools_status")
async def check_tools_status():
    """各ツールの状態をチェック"""
    try:
        status = {
            "google_drive": {
                "service_initialized": google_drive_tool.service is not None,
                "credentials_found": google_drive_tool.credentials is not None
            },
            "chrome_history": chrome_history_tool.get_status(),
            "mistral_ocr": await mistral_ocr_tool.check_api_status(),
            "mcp_server": {
                "status": "running",
                "implementation": "FastAPI",
                "endpoints": len([route for route in app.routes if hasattr(route, 'methods')])
            }
        }
        
        logger.info("Tools status checked")
        return status
        
    except Exception as e:
        logger.error(f"Error checking tools status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Extend Your Memory MCP Server (FastAPI)...")
    logger.info("Available endpoints:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            logger.info(f"  {methods} {route.path}")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8501)
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        logger.error(f"MCP Server error: {e}")
        raise