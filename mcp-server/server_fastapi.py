#!/usr/bin/env python3
"""
Extend Your Memory MCP Server (FastAPI Implementation)
Provides tools for Google Drive, Chrome History, and Mistral OCR integration
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ツールクラスのインポート
from google_drive_tool import GoogleDriveTool
from chrome_history_tool_remote import RemoteChromeHistoryTool
from mistral_ocr_tool import MistralOCRTool
from web_fetch_tool import WebFetchTool

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

# CORS設定 - Chrome Extension からのアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "http://localhost:*",
        "https://localhost:*",
        "http://localhost:3000", 
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ツールインスタンス
google_drive_tool = GoogleDriveTool()
chrome_history_tool = RemoteChromeHistoryTool()
mistral_ocr_tool = MistralOCRTool()
web_fetch_tool = WebFetchTool()

# Pydantic モデル
class SearchGoogleDriveRequest(BaseModel):
    keywords: List[str]
    file_types: Optional[List[str]] = None
    folder_id: Optional[str] = "root"
    max_results: int = 50
    excluded_folder_ids: Optional[List[str]] = None

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

# Chrome Extension 用の追加モデル
class HistoryDataRequest(BaseModel):
    """Chrome Extension からの履歴データ受信用モデル"""
    history_items: List[Dict[str, Any]]
    client_id: Optional[str] = None
    timestamp: Optional[float] = None

# Web Fetch 用のモデル
class WebFetchRequest(BaseModel):
    """Web フェッチリクエスト用モデル"""
    urls: List[str]
    max_concurrent: Optional[int] = 5
    use_chromium: Optional[bool] = False  # JavaScript有効化オプション

class WebSearchRequest(BaseModel):
    """Web 検索リクエスト用モデル"""
    keywords: List[str]
    max_results: Optional[int] = 10

# エンドポイント実装
@app.get("/")
async def root():
    return {"message": "Extend Your Memory MCP Server", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Chrome Extension API endpoints
@app.post("/api/chrome/history")
async def receive_chrome_history(request: HistoryDataRequest):
    """Chrome Extension からの履歴データを受信"""
    try:
        logger.info(f"Received history data: {len(request.history_items)} items")
        
        result = await chrome_history_tool.receive_history_data(request.history_items)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error receiving Chrome history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chrome/history/search")
async def search_chrome_history_endpoint(
    keywords: str = "",
    days: int = 30,
    max_results: int = 50
):
    """Chrome履歴検索エンドポイント (GET version for Chrome Extension)"""
    try:
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
        
        logger.info(f"Chrome history search: keywords={keyword_list}, days={days}")
        
        history_items = await chrome_history_tool.search_history(
            keywords=keyword_list,
            days=days,
            max_results=max_results
        )
        
        return JSONResponse(content={
            "success": True,
            "data": history_items,
            "total": len(history_items)
        })
        
    except Exception as e:
        logger.error(f"Error in Chrome history search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chrome/history/recent")
async def get_recent_chrome_history_endpoint(
    hours: int = 24,
    max_results: int = 100
):
    """最近のChrome履歴取得エンドポイント (GET version for Chrome Extension)"""
    try:
        logger.info(f"Getting recent Chrome history: {hours} hours, max {max_results}")
        
        recent_history = await chrome_history_tool.get_recent_history(
            hours=hours,
            max_results=max_results
        )
        
        return JSONResponse(content={
            "success": True,
            "data": recent_history,
            "total": len(recent_history)
        })
        
    except Exception as e:
        logger.error(f"Error getting recent Chrome history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chrome/register")
async def register_chrome_extension(request: Request):
    """Chrome Extension の登録エンドポイント"""
    try:
        client_info = await request.json()
        extension_id = client_info.get("extension_id")
        version = client_info.get("version", "unknown")
        
        logger.info(f"Chrome Extension registered: {extension_id} (v{version})")
        
        # Initialize the Chrome history tool with extension
        await chrome_history_tool.initialize()
        
        return JSONResponse(content={
            "success": True,
            "message": "Extension registered successfully",
            "server_capabilities": {
                "history_search": True,
                "google_drive_search": True,
                "ocr_processing": True
            }
        })
        
    except Exception as e:
        logger.error(f"Error registering Chrome extension: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/search_google_drive")
async def search_google_drive(request: SearchGoogleDriveRequest):
    """Google Driveからキーワードに基づいてファイルを検索"""
    try:
        logger.info(f"Google Drive search: keywords={request.keywords}")
        
        documents = await google_drive_tool.search_files(
            keywords=request.keywords,
            file_types=request.file_types,
            folder_id=request.folder_id,
            max_results=request.max_results,
            excluded_folder_ids=request.excluded_folder_ids
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

@app.post("/tools/web_fetch")
async def web_fetch_multiple(request: WebFetchRequest):
    """複数URLのWebページフェッチ (LangChain WebBaseLoader使用)"""
    try:
        logger.info(f"Fetching {len(request.urls)} URLs (chromium: {request.use_chromium})")
        
        results = await web_fetch_tool.fetch_multiple_urls(
            urls=request.urls,
            max_concurrent=request.max_concurrent,
            use_chromium=request.use_chromium
        )
        
        return {
            "success": True,
            "data": results,
            "total": len(results),
            "loader_type": "AsyncChromiumLoader" if request.use_chromium else "WebBaseLoader"
        }
        
    except Exception as e:
        logger.error(f"Error in web_fetch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools/web_fetch_single")
async def web_fetch_single(url: str, use_chromium: bool = False):
    """単一URLのWebページフェッチ (LangChain WebBaseLoader使用)"""
    try:
        logger.info(f"Fetching single URL: {url} (chromium: {use_chromium})")
        
        result = await web_fetch_tool.fetch_url(url, use_chromium=use_chromium)
        
        if result:
            return result
        else:
            raise HTTPException(status_code=404, detail="Failed to fetch URL")
        
    except Exception as e:
        logger.error(f"Error in web_fetch_single: {e}")
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

# Google OAuth2 endpoints
@app.get("/auth/google/login")
async def google_oauth_login():
    """Google OAuth2認証を開始"""
    try:
        auth_url = google_drive_tool.get_authorization_url()
        
        if auth_url:
            return {"auth_url": auth_url}
        else:
            raise HTTPException(
                status_code=500, 
                detail="OAuth2 flow not configured. Check GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET"
            )
    except Exception as e:
        logger.error(f"Error starting Google OAuth2 flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/google/callback")
async def google_oauth_callback(code: str):
    """Google OAuth2コールバックを処理"""
    try:
        success = google_drive_tool.handle_oauth_callback(code)
        
        if success:
            return {
                "success": True,
                "message": "Google Drive authentication successful",
                "redirect_url": "/"  # フロントエンドのルートにリダイレクト
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to authenticate with Google")
            
    except Exception as e:
        logger.error(f"Error in Google OAuth2 callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/google/revoke")
async def google_oauth_revoke():
    """Google OAuth2認証を取り消し"""
    try:
        # トークンファイルを削除
        token_file = './credentials/google_oauth_token.json'
        if os.path.exists(token_file):
            os.remove(token_file)
        
        # ツールを再初期化
        google_drive_tool._initialize_service()
        
        return {"success": True, "message": "Google Drive authentication revoked"}
        
    except Exception as e:
        logger.error(f"Error revoking Google OAuth2: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools/check_tools_status")
async def check_tools_status():
    """各ツールの状態をチェック"""
    try:
        status = {
            "google_drive": google_drive_tool.get_status(),
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