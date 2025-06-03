#!/usr/bin/env python3
"""
Extend Your Memory Backend API
FastAPI server with RAG pipeline and MCP integration
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# RAG Pipeline のインポート
from rag_pipeline import RAGPipeline

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
            
            if not query:
                await websocket.send_text(json.dumps({
                    "error": "Query is required"
                }))
                continue
            
            # 検索プロセスの実行
            result = await process_search_with_progress(query, websocket)
            
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

async def process_search_with_progress(query: str, websocket: WebSocket) -> SearchResult:
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
        
        documents = await rag_pipeline.search_with_mcp(keywords)
        logger.info(f"Retrieved {len(documents)} documents from MCP")
        
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
        doc_summary = "\n".join([doc.page_content[:100] for doc in documents[:3]])
        rag_queries = await rag_pipeline.generate_rag_queries(query, doc_summary)
        
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
        
        # 簡略化された検索プロセス
        keywords = await rag_pipeline.generate_keywords(request.query)
        logger.info(f"Generated keywords: {keywords}")
        
        documents = await rag_pipeline.search_with_mcp(keywords)
        logger.info(f"Retrieved {len(documents)} documents from MCP")
        
        vector_store = await rag_pipeline.process_and_store_documents(documents)
        logger.info("Documents processed and stored")
        
        if vector_store:
            await rag_pipeline.save_vector_store()
        
        doc_summary = "\n".join([doc.page_content[:100] for doc in documents[:3]])
        rag_queries = await rag_pipeline.generate_rag_queries(request.query, doc_summary)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)