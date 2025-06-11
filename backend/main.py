#!/usr/bin/env python3
"""
Extend Your Memory Backend API
FastAPI server with RAG pipeline and MCP integration
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# RAG Pipeline のインポート
from rag_pipeline import RAGPipeline
from config_manager import excluded_folders_config

load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Extend Your Memory API",
    description="AI-powered search and report generation from Google Drive and browser history",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    excluded_folder_ids: Optional[List[str]] = None

class ExcludedFolderRequest(BaseModel):
    folder_id: str
    name: Optional[str] = ""
    description: Optional[str] = ""
    enabled: bool = True

class ConfigSettingsRequest(BaseModel):
    settings: Dict[str, Any]

class SearchProgress(BaseModel):
    step: int
    stage: str
    message: str
    details: Optional[Dict[str, Any]] = None

class SearchResult(BaseModel):
    report: str
    sources: List[Dict[str, Any]]
    keywords_used: List[str]
    rag_queries: List[str]
    total_documents: int
    relevant_documents: int

# RAGパイプラインインスタンス
rag_pipeline = RAGPipeline()

@app.get("/")
async def root():
    return {"message": "Extend Your Memory API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.websocket("/ws/search")
async def websocket_search(websocket: WebSocket):
    """リアルタイム検索進捗のWebSocket接続"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            query = request.get("query", "")
            excluded_folder_ids = request.get("excluded_folder_ids")
            
            if not query:
                await websocket.send_text(json.dumps({
                    "error": "Query is required"
                }))
                continue
            
            # 設定ファイルから除外フォルダを自動読み込み（リクエストで指定がない場合）
            if excluded_folder_ids is None and excluded_folders_config.is_auto_exclude_enabled():
                excluded_folder_ids = excluded_folders_config.get_excluded_folder_ids()
                logger.info(f"Auto-loaded {len(excluded_folder_ids)} excluded folders from config")
            
            # 検索プロセスの実行
            result = await process_search_with_progress(query, websocket, excluded_folder_ids)
            
            # 最終結果の送信
            await websocket.send_text(json.dumps({
                "event": "search_complete",
                "data": result.dict()
            }))
            
    except Exception as e:
        await websocket.send_text(json.dumps({
            "event": "error",
            "message": str(e)
        }))

async def process_search_with_progress(query: str, websocket: WebSocket, excluded_folder_ids: Optional[List[str]] = None) -> SearchResult:
    """進捗をWebSocketで送信しながら検索を実行"""
    
    try:
        # ステップ1: キーワード生成
        await websocket.send_text(json.dumps({
            "event": "search_progress",
            "data": SearchProgress(
                step=1,
                stage="keyword_generation",
                message="検索キーワードを生成中...",
                details={"query": query}
            ).dict()
        }))
        
        keywords = await rag_pipeline.generate_keywords(query)
        logger.info(f"Generated keywords: {keywords}")
        
        # ステップ2-3: MCP検索
        await websocket.send_text(json.dumps({
            "event": "search_progress",
            "data": SearchProgress(
                step=2,
                stage="mcp_search",
                message="MCPサーバーでソースを検索中...",
                details={
                    "keywords": keywords,
                    "searching": ["google_drive", "chrome_history"]
                }
            ).dict()
        }))
        
        documents = await rag_pipeline.search_with_mcp(keywords, excluded_folder_ids)
        logger.info(f"Retrieved {len(documents)} documents from MCP")
        
        # 検索結果が0件の場合はエラーを返す
        if not documents:
            await websocket.send_text(json.dumps({
                "event": "error",
                "message": "検索結果が0件でした。キーワードを変更して再度検索してください。"
            }))
            raise HTTPException(status_code=404, detail="検索結果が0件です")
        
        # ステップ4: ベクトル化
        await websocket.send_text(json.dumps({
            "event": "search_progress",
            "data": SearchProgress(
                step=4,
                stage="vectorization",
                message="取得したドキュメントをベクトル化中...",
                details={
                    "total_documents": len(documents),
                    "processed": len(documents),
                    "sources": {
                        "google_drive": len([d for d in documents if d.metadata.get("source", "").startswith("google")]),
                        "chrome_history": len([d for d in documents if d.metadata.get("source", "").startswith("chrome")])
                    }
                }
            ).dict()
        }))
        
        vector_store = await rag_pipeline.process_and_store_documents(documents)
        logger.info("Documents processed and stored in vector database")
        
        # ベクトルストアを保存
        if vector_store:
            await rag_pipeline.save_vector_store()
        
        # ステップ5-6: RAG検索
        rag_queries = await rag_pipeline.generate_rag_queries(query)
        
        await websocket.send_text(json.dumps({
            "event": "search_progress",
            "data": SearchProgress(
                step=5,
                stage="rag_search",
                message="セマンティック検索を実行中...",
                details={"rag_queries": rag_queries}
            ).dict()
        }))
        
        relevant_docs = await rag_pipeline.semantic_search(rag_queries)
        logger.info(f"Semantic search returned {len(relevant_docs)} relevant documents")
        
        # ステップ7: レポート生成
        await websocket.send_text(json.dumps({
            "event": "search_progress",
            "data": SearchProgress(
                step=7,
                stage="report_generation",
                message="レポートを生成中...",
                details={
                    "relevant_sources": len(relevant_docs),
                    "citations_count": len(relevant_docs)
                }
            ).dict()
        }))
        
        report = await rag_pipeline.generate_report(query, relevant_docs)
        logger.info("Report generated successfully")
        
        return SearchResult(
            report=report,
            sources=[doc.metadata for doc in documents],
            keywords_used=keywords,
            rag_queries=rag_queries,
            total_documents=len(documents),
            relevant_documents=len(relevant_docs)
        )
        
    except Exception as e:
        logger.error(f"Error in search process: {e}")
        await websocket.send_text(json.dumps({
            "event": "error",
            "message": f"検索中にエラーが発生しました: {str(e)}"
        }))
        raise

@app.post("/search", response_model=SearchResult)
async def search_endpoint(request: QueryRequest):
    """RESTful検索エンドポイント（WebSocketを使わない場合）"""
    try:
        logger.info(f"Search request: {request.query}")
        
        # 設定ファイルから除外フォルダを自動読み込み（リクエストで指定がない場合）
        excluded_folder_ids = request.excluded_folder_ids
        if excluded_folder_ids is None and excluded_folders_config.is_auto_exclude_enabled():
            excluded_folder_ids = excluded_folders_config.get_excluded_folder_ids()
            logger.info(f"Auto-loaded {len(excluded_folder_ids)} excluded folders from config")
        
        # 簡略化された検索プロセス
        keywords = await rag_pipeline.generate_keywords(request.query)
        logger.info(f"Generated keywords: {keywords}")
        
        documents = await rag_pipeline.search_with_mcp(keywords, excluded_folder_ids)
        logger.info(f"Retrieved {len(documents)} documents from MCP")
        
        # 検索結果が0件の場合はエラーを返す
        if not documents:
            logger.error("No documents found from MCP search")
            raise HTTPException(status_code=404, detail="検索結果が0件でした。キーワードを変更して再度検索してください。")
        
        vector_store = await rag_pipeline.process_and_store_documents(documents)
        logger.info("Documents processed and stored")
        
        if vector_store:
            await rag_pipeline.save_vector_store()
        
        rag_queries = await rag_pipeline.generate_rag_queries(request.query)
        logger.info(f"Generated RAG queries: {rag_queries}")
        
        relevant_docs = await rag_pipeline.semantic_search(rag_queries)
        logger.info(f"Semantic search returned {len(relevant_docs)} relevant documents")
        
        report = await rag_pipeline.generate_report(request.query, relevant_docs)
        logger.info("Report generated")
        
        return SearchResult(
            report=report,
            sources=[doc.metadata for doc in documents],
            keywords_used=keywords,
            rag_queries=rag_queries,
            total_documents=len(documents),
            relevant_documents=len(relevant_docs)
        )
        
    except Exception as e:
        logger.error(f"Search endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 除外フォルダ設定管理エンドポイント

@app.get("/config/excluded-folders")
async def get_excluded_folders():
    """除外フォルダ設定を取得"""
    try:
        return {
            "excluded_folders": excluded_folders_config.get_excluded_folders(),
            "settings": excluded_folders_config.get_settings(),
            "total_enabled": len(excluded_folders_config.get_excluded_folder_ids())
        }
    except Exception as e:
        logger.error(f"Error getting excluded folders config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/excluded-folders")
async def add_excluded_folder(request: ExcludedFolderRequest):
    """除外フォルダを追加"""
    try:
        success = excluded_folders_config.add_excluded_folder(
            folder_id=request.folder_id,
            name=request.name,
            description=request.description,
            enabled=request.enabled
        )
        
        if success:
            return {
                "success": True,
                "message": f"Added excluded folder: {request.folder_id}",
                "total_excluded": len(excluded_folders_config.get_excluded_folder_ids())
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to add excluded folder")
            
    except Exception as e:
        logger.error(f"Error adding excluded folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/config/excluded-folders/{folder_id}")
async def remove_excluded_folder(folder_id: str):
    """除外フォルダを削除"""
    try:
        success = excluded_folders_config.remove_excluded_folder(folder_id)
        
        if success:
            return {
                "success": True,
                "message": f"Removed excluded folder: {folder_id}",
                "total_excluded": len(excluded_folders_config.get_excluded_folder_ids())
            }
        else:
            raise HTTPException(status_code=404, detail="Excluded folder not found")
            
    except Exception as e:
        logger.error(f"Error removing excluded folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/config/excluded-folders/{folder_id}/toggle")
async def toggle_excluded_folder(folder_id: str):
    """除外フォルダの有効/無効を切り替え"""
    try:
        enabled = excluded_folders_config.toggle_excluded_folder(folder_id)
        
        if enabled is not None:
            return {
                "success": True,
                "folder_id": folder_id,
                "enabled": enabled,
                "message": f"Folder {'enabled' if enabled else 'disabled'}",
                "total_excluded": len(excluded_folders_config.get_excluded_folder_ids())
            }
        else:
            raise HTTPException(status_code=404, detail="Excluded folder not found")
            
    except Exception as e:
        logger.error(f"Error toggling excluded folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/config/settings")
async def update_config_settings(request: ConfigSettingsRequest):
    """設定を更新"""
    try:
        success = excluded_folders_config.update_settings(request.settings)
        
        if success:
            return {
                "success": True,
                "message": "Settings updated successfully",
                "settings": excluded_folders_config.get_settings()
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update settings")
            
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/excluded-folders/reload")
async def reload_excluded_folders_config():
    """設定ファイルを再読み込み"""
    try:
        success = excluded_folders_config.load_config()
        
        if success:
            return {
                "success": True,
                "message": "Configuration reloaded successfully",
                "total_excluded": len(excluded_folders_config.get_excluded_folder_ids())
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reload configuration")
            
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)