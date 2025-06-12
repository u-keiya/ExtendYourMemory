"""
RAG Pipeline Implementation with LangChain, FAISS, and Google Gemini
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import logging

from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
import httpx
from llm_query_generator import LLMQueryGenerator
from adaptive_faiss_optimizer import AdaptiveFAISSOptimizer

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vector_store = None
        self.retriever = None
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8501")
        self.query_generator = None
        self.faiss_optimizer = AdaptiveFAISSOptimizer()  # 新しい最適化コンポーネント
        self._initialize_models()
    
    def _initialize_models(self):
        """LLMと埋め込みモデルを初期化"""
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        if not google_api_key:
            logger.warning("GOOGLE_API_KEY not found. RAG pipeline functionality will be limited.")
            return
        
        try:
            # Gemini 2.5 Flash LLMの初期化
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-preview-05-20",
                google_api_key=google_api_key,
                temperature=1.0,
                max_tokens=8192
            )
            
            # Google Embeddings の初期化
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=google_api_key
            )
            
            # LLM Query Generator の初期化
            self.query_generator = LLMQueryGenerator(self.llm)
            
            logger.info("RAG pipeline models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG models: {e}")
            logger.warning("RAG pipeline functionality will be limited without proper API configuration")
    
    async def generate_keywords(self, user_query: str) -> List[str]:
        """ユーザークエリから検索キーワードを生成（後方互換性のため）"""
        
        keyword_data = await self.generate_hierarchical_keywords(user_query)
        return keyword_data.get('all_keywords', [])

    async def generate_hierarchical_keywords(self, user_query: str) -> Dict[str, Any]:
        """AGRフレームワークを使用した階層的キーワード生成"""
        
        if not self.query_generator:
            logger.error("Query generator not initialized")
            raise RuntimeError("LLM Query Generator not available - cannot generate keywords")
        
        try:
            # LLM Query Generator を使用（AGRフレームワーク）
            keyword_data = await self.query_generator.generate_diverse_keywords(user_query)
            
            # 全てのキーワードを取得
            all_keywords = keyword_data.get('all_keywords', [])
            hierarchical = keyword_data.get('hierarchical', {})
            analysis = keyword_data.get('analysis', {})
            
            # 重複除去
            unique_keywords = []
            seen = set()
            
            for keyword in all_keywords:
                if keyword.lower() not in seen:
                    unique_keywords.append(keyword)
                    seen.add(keyword.lower())
            
            logger.info(f"AGR keyword generation produced {len(unique_keywords)} keywords")
            logger.info(f"Query analysis: {analysis.get('intent', 'unknown')} / {analysis.get('complexity', 'medium')}")
            
            # 階層情報のログ
            primary_count = len(hierarchical.get('primary_keywords', []))
            secondary_count = len(hierarchical.get('secondary_keywords', []))
            context_count = len(hierarchical.get('context_keywords', []))
            negative_count = len(hierarchical.get('negative_keywords', []))
            
            logger.info(f"Hierarchical breakdown: Primary={primary_count}, Secondary={secondary_count}, Context={context_count}, Negative={negative_count}")
            
            return {
                'all_keywords': unique_keywords[:20],  # 最大20個
                'hierarchical': hierarchical,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error in AGR keyword generation: {e}")
            raise RuntimeError(f"Failed to generate keywords with LLM: {e}")
    
    
    async def search_with_mcp(self, keywords: List[str], excluded_folder_ids: Optional[List[str]] = None, hierarchical_keywords: Optional[Dict[str, Any]] = None) -> List[Document]:
        """MCPサーバーを使用してドキュメントを検索"""
        
        documents = []
        
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                # Google Drive検索 - 階層的キーワード対応
                try:
                    if hierarchical_keywords:
                        # 階層的キーワードを使用した最適化検索
                        actual_hierarchical = hierarchical_keywords.get('hierarchical', {})
                        # MCPサーバーが期待する形式に合わせて、余分なフィールドを除去
                        clean_hierarchical = {
                            key: value for key, value in actual_hierarchical.items()
                            if key in ['primary_keywords', 'secondary_keywords', 'context_keywords', 'negative_keywords']
                        }
                        gdrive_request = {
                            "hierarchical_keywords": clean_hierarchical,
                            "file_types": ["document", "sheet", "pdf", "markdown"],
                            "max_results": 100
                        }
                        logger.info(f"Using hierarchical keywords for Google Drive search")
                        logger.info(f"Sending clean hierarchical_keywords: {clean_hierarchical}")
                    else:
                        # 従来のキーワード検索
                        gdrive_request = {
                            "keywords": keywords,
                            "file_types": ["document", "sheet", "pdf", "markdown"],
                            "max_results": 100
                        }
                        logger.info(f"Using simple keywords for Google Drive search: {keywords[:3]}...")
                    
                    # 除外フォルダがある場合は追加
                    if excluded_folder_ids:
                        gdrive_request["excluded_folder_ids"] = excluded_folder_ids
                        logger.info(f"Google Drive search excluding folders: {excluded_folder_ids}")
                    
                    gdrive_response = await client.post(
                        f"{self.mcp_server_url}/tools/search_google_drive",
                        json=gdrive_request
                    )
                    logger.info(f"Google Drive response status: {gdrive_response.status_code}")
                    if gdrive_response.status_code == 200:
                        gdrive_results = gdrive_response.json()
                        logger.info(f"Google Drive returned {len(gdrive_results)} results")
                        for item in gdrive_results:
                            documents.append(Document(
                                page_content=item.get("content", ""),
                                metadata=item.get("metadata", {})
                            ))
                    else:
                        logger.error(f"Google Drive search HTTP error: {gdrive_response.status_code} - {gdrive_response.text}")
                except Exception as e:
                    logger.error(f"Google Drive search failed: {e}")
                
                # Chrome履歴検索
                try:
                    chrome_response = await client.post(
                        f"{self.mcp_server_url}/tools/search_chrome_history",
                        json={
                            "keywords": keywords,
                            "days": 90,
                            "max_results": 100
                        }
                    )
                    logger.info(f"Chrome history response status: {chrome_response.status_code}")
                    if chrome_response.status_code == 200:
                        chrome_results = chrome_response.json()
                        logger.info(f"Chrome history returned {len(chrome_results)} results")
                        urls_to_fetch = []
                        
                        for item in chrome_results:
                            # Add Chrome history as document
                            documents.append(Document(
                                page_content=item.get("content", ""),
                                metadata=item.get("metadata", {})
                            ))
                            
                            # Collect URLs for web fetching
                            url = item.get("url")
                            if url and self._is_fetchable_url(url):
                                urls_to_fetch.append(url)
                        # Fetch web content from URLs
                        if urls_to_fetch:
                            try:
                                logger.info(f"Fetching {len(urls_to_fetch)} URLs from Chrome history")
                                web_response = await client.post(
                                    f"{self.mcp_server_url}/tools/web_fetch",
                                    json={
                                        "urls": urls_to_fetch[:50],  # Limit to 20 URLs
                                        "max_concurrent": 3
                                    }
                                )
                                logger.info(f"Web fetch response status: {web_response.status_code}")
                                if web_response.status_code == 200:
                                    web_results = web_response.json()
                                    web_data = web_results.get("data", []) if isinstance(web_results, dict) else web_results
                                    logger.info(f"Web fetch returned {len(web_data)} results")
                                    for web_item in web_data:
                                        documents.append(Document(
                                            page_content=web_item.get("content", ""),
                                            metadata={
                                                **web_item.get("metadata", {}),
                                                "source": "web_fetch",
                                                "fetched_from_history": True
                                            }
                                        ))
                                else:
                                    logger.error(f"Web fetch HTTP error: {web_response.status_code} - {web_response.text}")
                            except Exception as e:
                                logger.warning(f"Web fetch failed: {e}")
                    else:
                        logger.error(f"Chrome history search HTTP error: {chrome_response.status_code} - {chrome_response.text}")
                                
                except Exception as e:
                    logger.error(f"Chrome history search failed: {e}")
        
        except Exception as e:
            logger.error(f"MCP search failed: {e}")
            # 実際のデータが取得できない場合は空のリストを返す
            documents = []
        
        logger.info(f"Retrieved {len(documents)} documents from MCP search")
        return documents
    
    async def process_and_store_documents(self, documents: List[Document], query_analysis: Optional[Dict[str, Any]] = None) -> Optional[FAISS]:
        """ドキュメントを処理してFAISSベクトルストアに保存"""
        
        if not self.embeddings:
            logger.warning("Embeddings not available, skipping vector store creation")
            return None
        
        if not documents:
            logger.warning("No documents to process")
            return None
        
        try:
            # 適応的チャンク戦略の取得
            if query_analysis:
                chunk_config = self.faiss_optimizer.optimize_chunk_strategy(query_analysis)
            else:
                chunk_config = {
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                    "separators": ["\n\n", "\n", "。", ".", " ", ""]
                }
            
            # ドキュメントを最適化された戦略で分割
            splits = await self._split_documents_optimized(documents, chunk_config)
            
            if not splits:
                logger.warning("No document splits created")
                return None
            
            # 適応的検索パラメータの取得
            if query_analysis:
                search_params = self.faiss_optimizer.get_adaptive_search_params(query_analysis, len(splits))
            else:
                search_params = {
                    "search_type": "mmr",
                    "k": 6,
                    "fetch_k": 20,
                    "lambda_mult": 0.5
                }
            
            # ベクトル化とストア
            if self.vector_store is None:
                self.vector_store = await asyncio.to_thread(
                    FAISS.from_documents,
                    documents=splits,
                    embedding=self.embeddings
                )
            else:
                await asyncio.to_thread(
                    self.vector_store.add_documents,
                    splits
                )
            
            # 適応的パラメータでリトリーバーを更新
            self.retriever = self.vector_store.as_retriever(
                search_type=search_params.get("search_type", "mmr"),
                search_kwargs={
                    "k": search_params.get("k", 6),
                    "fetch_k": search_params.get("fetch_k", 20),
                    "lambda_mult": search_params.get("lambda_mult", 0.5)
                }
            )
            
            logger.info(f"Processed {len(splits)} document chunks into FAISS vector store")
            logger.info(f"Using adaptive search params: k={search_params.get('k')}, fetch_k={search_params.get('fetch_k')}, lambda_mult={search_params.get('lambda_mult')}")
            return self.vector_store
            
        except Exception as e:
            logger.error(f"Error processing documents: {e}")
            return None
    
    async def _split_documents(self, documents: List[Document]) -> List[Document]:
        """ドキュメントを適切なチャンクに分割"""
        
        all_splits = []
        
        for doc in documents:
            try:
                content = doc.page_content
                metadata = doc.metadata
                
                # Markdownドキュメントの場合
                if (metadata.get("ocr_processed") or 
                    ".md" in metadata.get("title", "") or
                    content.startswith("#")):
                    
                    # Markdownヘッダーで分割
                    headers_to_split_on = [
                        ("#", "Header 1"),
                        ("##", "Header 2"),
                        ("###", "Header 3")
                    ]
                    
                    markdown_splitter = MarkdownHeaderTextSplitter(
                        headers_to_split_on=headers_to_split_on,
                        strip_headers=False
                    )
                    
                    md_splits = markdown_splitter.split_text(content)
                    
                    # さらに文字数で分割
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000,
                        chunk_overlap=200
                    )
                    
                    for split in md_splits:
                        split.metadata.update(metadata)
                        chunks = text_splitter.split_documents([split])
                        all_splits.extend(chunks)
                else:
                    # 通常のテキストドキュメント
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000,
                        chunk_overlap=200,
                        separators=["\n\n", "\n", "。", ".", " ", ""]
                    )
                    
                    chunks = text_splitter.split_documents([doc])
                    all_splits.extend(chunks)
                    
            except Exception as e:
                logger.error(f"Error splitting document: {e}")
                continue
        
        return all_splits
    
    async def _split_documents_optimized(self, documents: List[Document], chunk_config: Dict[str, Any]) -> List[Document]:
        """最適化されたパラメータでドキュメントを分割"""
        
        all_splits = []
        
        chunk_size = chunk_config.get("chunk_size", 1000)
        chunk_overlap = chunk_config.get("chunk_overlap", 200)
        separators = chunk_config.get("separators", ["\n\n", "\n", "。", ".", " ", ""])
        
        for doc in documents:
            try:
                content = doc.page_content
                metadata = doc.metadata
                
                # Markdownドキュメントの場合
                if (metadata.get("ocr_processed") or 
                    ".md" in metadata.get("title", "") or
                    content.startswith("#")):
                    
                    # Markdownヘッダーで分割
                    headers_to_split_on = [
                        ("#", "Header 1"),
                        ("##", "Header 2"),
                        ("###", "Header 3")
                    ]
                    
                    markdown_splitter = MarkdownHeaderTextSplitter(
                        headers_to_split_on=headers_to_split_on,
                        strip_headers=False
                    )
                    
                    md_splits = markdown_splitter.split_text(content)
                    
                    # さらに最適化されたパラメータで分割
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        separators=separators
                    )
                    
                    for split in md_splits:
                        split.metadata.update(metadata)
                        chunks = text_splitter.split_documents([split])
                        all_splits.extend(chunks)
                else:
                    # 通常のテキストドキュメント（最適化されたパラメータ）
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        separators=separators
                    )
                    
                    chunks = text_splitter.split_documents([doc])
                    all_splits.extend(chunks)
                    
            except Exception as e:
                logger.error(f"Error splitting document with optimized config: {e}")
                continue
        
        logger.info(f"Optimized splitting: {len(all_splits)} chunks with size={chunk_size}, overlap={chunk_overlap}")
        return all_splits
    
    async def generate_rag_queries(self, original_query: str) -> List[str]:
        """RAG検索用のクエリを生成（完全LLMベース）"""
        
        if not self.query_generator:
            logger.error("Query generator not initialized")
            raise RuntimeError("LLM Query Generator not available - cannot generate RAG queries")
        
        try:
            # LLM Query Generator を使用
            rag_queries = await self.query_generator.generate_rag_queries(original_query)
            
            logger.info(f"LLM generated {len(rag_queries)} unique RAG queries")
            return rag_queries[:15]  # 最大15個
            
        except Exception as e:
            logger.error(f"Error in LLM RAG query generation: {e}")
            raise RuntimeError(f"Failed to generate RAG queries with LLM: {e}")
    
    
    async def semantic_search(self, queries: List[str]) -> List[Document]:
        """セマンティック検索を実行"""
        
        if not self.retriever:
            logger.warning("Retriever not available")
            return []
        
        try:
            relevant_docs = []
            
            for query in queries:
                try:
                    docs = await asyncio.to_thread(
                        self.retriever.invoke,
                        query
                    )
                    relevant_docs.extend(docs)
                except Exception as e:
                    logger.error(f"Error in semantic search for query '{query}': {e}")
                    continue
            
            # 重複除去（コンテンツベース）
            unique_docs = []
            seen_content = set()
            
            for doc in relevant_docs:
                content_hash = hash(doc.page_content[:100])  # 最初の100文字でハッシュ
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_docs.append(doc)
            
            logger.info(f"Semantic search returned {len(unique_docs)} unique documents")
            return unique_docs[:20]  # 最大20ドキュメント
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    async def generate_report(self, query: str, context_docs: List[Document]) -> str:
        """構造化レポートを生成"""
        
        if not self.llm:
            raise RuntimeError("LLM not available - cannot generate report")
        
        try:
            # コンテキストの準備
            context = "\n\n---\n\n".join([
                f"**出典**: {doc.metadata}\n**内容**: {doc.page_content}"
                for doc in context_docs
            ])
            
            report_prompt = PromptTemplate(
                template="""質問: {question}
                
                以下の情報源を基に、構造化されたレポートを作成してください．なお， **ユーザの質問に関連がない** と判断した情報は無視してください．：
                
                {context}
                
                レポートには以下を含めてください：
                1. **要約（Executive Summary）** - 重要なポイントを簡潔に
                2. **詳細な分析** - 情報源から得られた具体的な内容
                3. **重要なポイント** - 箇条書きで主要な発見事項
                4. **結論** - 質問に対する総合的な回答
                5. **引用情報** - 各情報には必ず出典を明記
                マークダウン形式で、読みやすく構造化して出力してください。
                各情報には適切な引用を含めてください。""",
                input_variables=["question", "context"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(report_prompt.format(
                    question=query,
                    context=context
                ))
            )
            
            logger.info("Report generated successfully")
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise RuntimeError(f"Failed to generate report with LLM: {e}")
    
    async def save_vector_store(self, path: str = "./vector_store_cache"):
        """ベクトルストアをローカルに保存"""
        if self.vector_store:
            try:
                await asyncio.to_thread(
                    self.vector_store.save_local,
                    path
                )
                logger.info(f"Vector store saved to {path}")
            except Exception as e:
                logger.error(f"Error saving vector store: {e}")
    
    async def load_vector_store(self, path: str = "./vector_store_cache"):
        """保存されたベクトルストアをロード"""
        if not self.embeddings:
            logger.warning("Embeddings not available, cannot load vector store")
            return
        
        try:
            if os.path.exists(path):
                self.vector_store = await asyncio.to_thread(
                    FAISS.load_local,
                    path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                self.retriever = self.vector_store.as_retriever(
                    search_type="mmr",
                    search_kwargs={"k": 6, "fetch_k": 20, "lambda_mult": 0.5}
                )
                logger.info(f"Vector store loaded from {path}")
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
    
    def _is_fetchable_url(self, url: str) -> bool:
        """Check if URL is suitable for web fetching"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Only HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Skip common non-content URLs
            skip_patterns = [
                'google.com/search',
                'bing.com/search',
                'youtube.com/watch',
                'twitter.com',
                'facebook.com',
                'instagram.com',
                'localhost',
                '127.0.0.1'
            ]
            
            for pattern in skip_patterns:
                if pattern in url.lower():
                    return False
            
            # Skip file downloads
            skip_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.tar', '.gz']
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                return False
            
            return True
            
        except Exception:
            return False
    
