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
        self._clear_vector_store_cache()  # 起動時にキャッシュをクリア
        self._initialize_models()
    
    def _clear_vector_store_cache(self):
        """ベクターストアキャッシュファイルを削除"""
        import shutil
        cache_path = "./vector_store_cache"
        try:
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path)
                logger.info("Cleared vector store cache directory to prevent data contamination")
        except Exception as e:
            logger.warning(f"Failed to clear vector store cache: {e}")
    
    def _initialize_models(self):
        """LLMと埋め込みモデルを初期化"""
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        if not google_api_key:
            logger.warning("GOOGLE_API_KEY not found. RAG pipeline functionality will be limited.")
            return
        
        try:
            logger.info("Initializing RAG pipeline models...")
            
            # Gemini 2.5 Flash LLMの初期化
            logger.info("Initializing Gemini LLM...")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=google_api_key,
                temperature=1.0,
                max_tokens=8192
            )
            logger.info("Gemini LLM initialized successfully")
            
            # Google Embeddings の初期化
            logger.info("Initializing Google Embeddings...")
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=google_api_key
            )
            logger.info("Google Embeddings initialized successfully")
            
            # LLM Query Generator の初期化
            logger.info("Initializing LLM Query Generator...")
            self.query_generator = LLMQueryGenerator(self.llm)
            logger.info("LLM Query Generator initialized successfully")
            
            logger.info("RAG pipeline models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG models: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            logger.warning("RAG pipeline functionality will be limited without proper API configuration")
            # Ensure query_generator is None for proper error handling
            self.query_generator = None
    
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
        
        # Google検索結果や低品質ソースをフィルタリング
        filtered_documents = self._filter_low_quality_sources(documents)
        logger.info(f"Filtered {len(documents)} → {len(filtered_documents)} documents (removed low-quality sources)")
        
        if not filtered_documents:
            logger.warning("No documents remaining after quality filtering")
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
            splits = await self._split_documents_optimized(filtered_documents, chunk_config)
            
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
            
            # ベクトル化とストア（常に新規作成で過去の検索結果をクリア）
            logger.info("Creating NEW vector store (clearing previous search data to prevent contamination)")
            self.vector_store = await asyncio.to_thread(
                FAISS.from_documents,
                documents=splits,
                embedding=self.embeddings
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
    
    
    async def semantic_search(self, queries: List[str], original_query: Optional[str] = None, similarity_threshold: float = 0.3) -> List[Document]:
        """セマンティック検索を実行（類似度スコアフィルタリング付き）"""
        
        if not self.retriever:
            logger.warning("Retriever not available")
            return []
        
        try:
            relevant_docs_with_scores = []
            
            for query in queries:
                try:
                    # similarity_search_with_score を使用してスコア付きで検索
                    docs_with_scores = await asyncio.to_thread(
                        self.vector_store.similarity_search_with_score,
                        query,
                        k=self.retriever.search_kwargs.get("k", 6)
                    )
                    
                    # スコアと共にドキュメントを保存
                    for doc, score in docs_with_scores:
                        # FAISSでは距離が小さいほど類似度が高い（0に近いほど類似）
                        # 類似度スコアに変換: similarity = 1 / (1 + distance)
                        similarity_score = 1.0 / (1.0 + score)
                        
                        # 類似度閾値でフィルタリング
                        if similarity_score >= similarity_threshold:
                            relevant_docs_with_scores.append({
                                'document': doc,
                                'similarity_score': similarity_score,
                                'distance': score,
                                'query': query
                            })
                            
                except Exception as e:
                    logger.error(f"Error in semantic search for query '{query}': {e}")
                    continue
            
            # 類似度スコアでソート（高い順）
            relevant_docs_with_scores.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # 重複除去（コンテンツベース）とスコア情報の保持
            unique_docs = []
            seen_content = set()
            
            for item in relevant_docs_with_scores:
                doc = item['document']
                content_hash = hash(doc.page_content[:100])  # 最初の100文字でハッシュ
                
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    
                    # メタデータに類似度情報を追加
                    doc.metadata['similarity_score'] = item['similarity_score']
                    doc.metadata['distance'] = item['distance']
                    doc.metadata['matched_query'] = item['query']
                    
                    unique_docs.append(doc)
            
            # 最終的な関連性チェック（元クエリとの関連性）
            from config_manager import excluded_folders_config
            max_docs_for_check = excluded_folders_config.get_max_documents_for_relevance_check()
            
            if original_query and len(unique_docs) > 10:
                filtered_docs = await self._final_relevance_check(original_query, unique_docs[:max_docs_for_check])
                logger.info(f"Final relevance check: {len(filtered_docs)}/{len(unique_docs)} documents passed")
                unique_docs = filtered_docs
            
            # スコア統計をログ出力
            if unique_docs:
                scores = [doc.metadata.get('similarity_score', 0) for doc in unique_docs]
                avg_score = sum(scores) / len(scores)
                min_score = min(scores)
                max_score = max(scores)
                
                logger.info(f"Semantic search returned {len(unique_docs)} documents with similarity filtering")
                logger.info(f"  Similarity scores - Min: {min_score:.3f}, Max: {max_score:.3f}, Avg: {avg_score:.3f}")
                logger.info(f"  Similarity threshold: {similarity_threshold}")
                
                # 低品質文書の警告
                low_quality_count = len([s for s in scores if s < 0.5])
                if low_quality_count > 0:
                    logger.warning(f"  {low_quality_count} documents have low similarity scores (<0.5)")
            else:
                logger.warning("No documents passed similarity threshold")
            
            return unique_docs[:20]  # 最大20ドキュメント
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            # フォールバック: 元の方法を使用
            return await self._fallback_semantic_search(queries)
    
    async def _fallback_semantic_search(self, queries: List[str]) -> List[Document]:
        """フォールバック用のセマンティック検索（スコアなし）"""
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
                    logger.error(f"Error in fallback search for query '{query}': {e}")
                    continue
            
            # 重複除去のみ
            unique_docs = []
            seen_content = set()
            
            for doc in relevant_docs:
                content_hash = hash(doc.page_content[:100])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_docs.append(doc)
            
            logger.info(f"Fallback search returned {len(unique_docs)} documents")
            return unique_docs[:20]
            
        except Exception as e:
            logger.error(f"Error in fallback semantic search: {e}")
            return []
    
    async def _final_relevance_check(self, original_query: str, documents: List[Document]) -> List[Document]:
        """元クエリとの最終関連性チェック"""
        
        if not self.llm:
            logger.warning("LLM not available for relevance check")
            return documents[:10]  # LLMが使えない場合は上位10件を返す
        
        try:
            # ドキュメント概要を作成
            doc_summaries = []
            for i, doc in enumerate(documents):
                content_preview = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                doc_summaries.append(f"[{i}] {doc.metadata.get('title', 'Untitled')}: {content_preview}")
            
            # LLMに関連性判定を依頼
            relevance_prompt = f"""
ユーザークエリ: "{original_query}"

以下のドキュメントの中から、ユーザークエリに関連性が高いものを選択してください。
関連性が低い、または無関係なドキュメントは除外してください。

ドキュメント一覧:
{chr(10).join(doc_summaries)}

関連性が高いドキュメントの番号を、関連性の高い順にカンマ区切りで返してください。
例: 0,3,7,2

番号のみを返してください。説明は不要です。
"""
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(relevance_prompt)
            )
            
            # レスポンスから番号を抽出
            selected_indices = []
            try:
                numbers = response.content.strip().split(',')
                for num_str in numbers:
                    try:
                        idx = int(num_str.strip())
                        if 0 <= idx < len(documents):
                            selected_indices.append(idx)
                    except ValueError:
                        continue
            except Exception as e:
                logger.warning(f"Failed to parse relevance check response: {e}")
                return documents[:10]  # パース失敗時は上位10件
            
            # 選択されたドキュメントを返す
            if selected_indices:
                filtered_docs = [documents[i] for i in selected_indices]
                logger.info(f"Relevance check: selected {len(filtered_docs)} from {len(documents)} documents")
                return filtered_docs
            else:
                logger.warning("No documents selected by relevance check, returning top 5")
                return documents[:5]
                
        except Exception as e:
            logger.error(f"Error in final relevance check: {e}")
            return documents[:10]
    
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
                
                以下の情報源を基に、構造化されたレポートをマークダウン形式で作成してください．数式はKatexで対応しています．
                参考にした文献はURLのリンク埋め込みを行ってください．ただし，レポートの見やすさのため，埋め込みを行う文字列は文献のタイトルではなく'[1]'などのように番号で示してください．
                なお， **ユーザの質問に関連がない** と判断した情報は無視してください．：
                
                {context}
                
                レポートには以下を含めてください：
                1. **要約（Executive Summary）** - 重要なポイントを簡潔に
                2. **詳細な分析** - 情報源から得られた具体的な内容
                3. **重要なポイント** - 箇条書きで主要な発見事項
                4. **結論** - 質問に対する総合的な回答
                マークダウン形式で、読みやすく構造化して出力してください。
                各情報には適切な引用を含めてください。参考文献は不要です．""",
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
    
    def _filter_low_quality_sources(self, documents: List[Document]) -> List[Document]:
        """低品質なソース（Google検索結果など）をフィルタリング"""
        
        filtered_docs = []
        removed_count = {'search_results': 0, 'low_content': 0, 'blocked_domains': 0}
        
        for doc in documents:
            try:
                url = doc.metadata.get('url', '')
                title = doc.metadata.get('title', '').lower()
                content = doc.page_content.lower()
                source = doc.metadata.get('source', '')
                
                # Google検索結果ページを除外
                if self._is_search_result_page(url, title, content):
                    removed_count['search_results'] += 1
                    logger.debug(f"Filtered search result: {title[:50]}...")
                    continue
                
                # 低品質コンテンツを除外
                if self._is_low_quality_content(content, title):
                    removed_count['low_content'] += 1
                    logger.debug(f"Filtered low quality content: {title[:50]}...")
                    continue
                
                # ブロックドメインを除外
                if self._is_blocked_domain(url):
                    removed_count['blocked_domains'] += 1
                    logger.debug(f"Filtered blocked domain: {url}")
                    continue
                
                # 品質基準を通過したドキュメントを保持
                filtered_docs.append(doc)
                
            except Exception as e:
                logger.warning(f"Error filtering document: {e}")
                # エラーの場合は保守的にドキュメントを保持
                filtered_docs.append(doc)
        
        # フィルタリング統計をログ出力
        total_removed = sum(removed_count.values())
        if total_removed > 0:
            logger.info(f"Document filtering removed {total_removed} documents:")
            logger.info(f"  Search results: {removed_count['search_results']}")
            logger.info(f"  Low quality content: {removed_count['low_content']}")
            logger.info(f"  Blocked domains: {removed_count['blocked_domains']}")
        
        return filtered_docs
    
    def _is_search_result_page(self, url: str, title: str, content: str) -> bool:
        """検索結果ページかどうかを判定"""
        
        # URL パターンで検索結果ページを検出
        search_url_patterns = [
            'google.com/search',
            'google.com/search?',
            'google.co.jp/search',
            'bing.com/search',
            'yahoo.com/search',
            'youtube.com',
            'duckduckgo.com/',
            'baidu.com/s',
            'yandex.com/search'
        ]
        
        for pattern in search_url_patterns:
            if pattern in url.lower():
                return True
        
        # タイトルで検索結果ページを検出
        search_title_patterns = [
            '- google 検索',
            '- google search',
            '- bing search',
            '- yahoo search',
            'search results',
            '検索結果'
        ]
        
        for pattern in search_title_patterns:
            if pattern in title:
                return True
        
        # コンテンツで検索結果ページを検出
        search_content_indicators = [
            'did you mean',
            'search instead for',
            'showing results for',
            'about x results',
            'もしかして',
            '検索結果',
            'results for'
        ]
        
        for indicator in search_content_indicators:
            if indicator in content and len(content) < 1000:  # 短いコンテンツで検索指標がある場合
                return True
        
        return False
    
    def _is_low_quality_content(self, content: str, title: str) -> bool:
        """低品質コンテンツかどうかを判定"""
        
        # 極端に短いコンテンツ
        if len(content.strip()) < 100:
            return True
        
        # エラーページやアクセス拒否ページ
        error_indicators = [
            '404 not found',
            '403 forbidden',
            'access denied',
            'page not found',
            'server error',
            'アクセスが拒否されました',
            'ページが見つかりません',
            'エラーが発生しました'
        ]
        
        for indicator in error_indicators:
            if indicator in content:
                return True
        
        # ナビゲーションメニューのみのページ
        nav_only_indicators = [
            'home about contact',
            'ホーム について お問い合わせ',
            'menu navigation'
        ]
        
        content_words = len(content.split())
        if content_words < 50:  # 極端に短い場合のみチェック
            for indicator in nav_only_indicators:
                if indicator in content:
                    return True
        
        # 重複の多いコンテンツ（同じ文章の繰り返し）
        sentences = content.split('.')
        if len(sentences) > 5:
            unique_sentences = set(s.strip().lower() for s in sentences if s.strip())
            if len(unique_sentences) / len(sentences) < 0.5:  # 50%以上が重複
                return True
        
        return False
    
    def _is_blocked_domain(self, url: str) -> bool:
        """ブロックすべきドメインかどうかを判定"""
        
        blocked_domains = [
            'twitter.com',
            'facebook.com',
            'instagram.com',
            'tiktok.com',
            'linkedin.com',
            'pinterest.com',
            'reddit.com',  # コメントセクションが多く情報価値が低い場合が多い
            'youtube.com/watch',  # 動画ページ（動画自体は取得できない）
            'localhost',
            '127.0.0.1'
        ]
        
        for domain in blocked_domains:
            if domain in url.lower():
                return True
        
        return False
    
    def _is_fetchable_url(self, url: str) -> bool:
        """Check if URL is suitable for web fetching"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Only HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Use the same filtering logic as _filter_low_quality_sources
            if self._is_blocked_domain(url):
                return False
            
            # Skip file downloads
            skip_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.tar', '.gz']
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                return False
            
            return True
            
        except Exception:
            return False
    
