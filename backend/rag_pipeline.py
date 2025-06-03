"""
RAG Pipeline Implementation with LangChain, FAISS, and Google Gemini
"""

import os
import json
import asyncio
import pickle
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.docstore.document import Document
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import httpx

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vector_store = None
        self.retriever = None
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8501")
        self._initialize_models()
    
    def _initialize_models(self):
        """LLMと埋め込みモデルを初期化"""
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        if not google_api_key:
            logger.warning("GOOGLE_API_KEY not found. RAG pipeline will use mock responses.")
            return
        
        try:
            # Gemini 2.5 Flash LLMの初期化
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-preview-05-20",
                google_api_key=google_api_key,
                temperature=0.3,
                max_tokens=8192
            )
            
            # Google Embeddings の初期化
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=google_api_key
            )
            
            logger.info("RAG pipeline models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG models: {e}")
            logger.info("RAG pipeline will use mock responses")
    
    async def generate_keywords(self, user_query: str) -> List[str]:
        """ユーザークエリから検索キーワードを生成"""
        
        if not self.llm:
            return await self._mock_generate_keywords(user_query)
        
        try:
            keyword_prompt = PromptTemplate(
                template="""ユーザーからの質問: {question}

この質問に関連する情報を検索するため、以下の観点から検索キーワードを生成してください：
1. 質問の核心的なトピック
2. 関連する技術用語（日本語・英語両方）
3. 類似概念や同義語
4. 時期やバージョンに関する情報

JSON形式で5-10個のキーワードを出力してください。
出力形式: {{"keywords": ["キーワード1", "keyword2", ...]}}

JSON以外は出力しないでください。""",
                input_variables=["question"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(keyword_prompt.format(question=user_query))
            )
            
            # JSONレスポンスを解析
            try:
                result = json.loads(response.content)
                keywords = result.get("keywords", [])
                logger.info(f"Generated keywords: {keywords}")
                return keywords[:10]  # 最大10個まで
            except json.JSONDecodeError:
                logger.error("Failed to parse keywords JSON response")
                return await self._mock_generate_keywords(user_query)
                
        except Exception as e:
            logger.error(f"Error generating keywords: {e}")
            return await self._mock_generate_keywords(user_query)
    
    async def search_with_mcp(self, keywords: List[str]) -> List[Document]:
        """MCPサーバーを使用してドキュメントを検索"""
        
        documents = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Google Drive検索
                try:
                    gdrive_response = await client.post(
                        f"{self.mcp_server_url}/tools/search_google_drive",
                        json={
                            "keywords": keywords,
                            "file_types": ["document", "sheet", "pdf"],
                            "max_results": 20
                        }
                    )
                    if gdrive_response.status_code == 200:
                        gdrive_results = gdrive_response.json()
                        for item in gdrive_results:
                            documents.append(Document(
                                page_content=item.get("content", ""),
                                metadata=item.get("metadata", {})
                            ))
                except Exception as e:
                    logger.error(f"Google Drive search failed: {e}")
                
                # Chrome履歴検索
                try:
                    chrome_response = await client.post(
                        f"{self.mcp_server_url}/tools/search_chrome_history",
                        json={
                            "keywords": keywords,
                            "days": 30,
                            "max_results": 20
                        }
                    )
                    if chrome_response.status_code == 200:
                        chrome_results = chrome_response.json()
                        for item in chrome_results:
                            documents.append(Document(
                                page_content=item.get("content", ""),
                                metadata=item.get("metadata", {})
                            ))
                except Exception as e:
                    logger.error(f"Chrome history search failed: {e}")
        
        except Exception as e:
            logger.error(f"MCP search failed: {e}")
            # フォールバック: モックドキュメント
            documents = await self._mock_search_results(keywords)
        
        logger.info(f"Retrieved {len(documents)} documents from MCP search")
        return documents
    
    async def process_and_store_documents(self, documents: List[Document]) -> Optional[FAISS]:
        """ドキュメントを処理してFAISSベクトルストアに保存"""
        
        if not self.embeddings:
            logger.warning("Embeddings not available, skipping vector store creation")
            return None
        
        if not documents:
            logger.warning("No documents to process")
            return None
        
        try:
            # ドキュメントを分割
            splits = await self._split_documents(documents)
            
            if not splits:
                logger.warning("No document splits created")
                return None
            
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
            
            # リトリーバーを更新
            self.retriever = self.vector_store.as_retriever(
                search_type="mmr",  # Maximal Marginal Relevance
                search_kwargs={
                    "k": 6,
                    "fetch_k": 20,
                    "lambda_mult": 0.5
                }
            )
            
            logger.info(f"Processed {len(splits)} document chunks into FAISS vector store")
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
    
    async def generate_rag_queries(self, original_query: str, doc_summary: str) -> List[str]:
        """RAG検索用のクエリを生成"""
        
        if not self.llm:
            return await self._mock_rag_queries(original_query)
        
        try:
            rag_query_prompt = PromptTemplate(
                template="""元の質問: {original_question}
取得したドキュメントの要約: {doc_summary}

上記の情報を基に、より詳細な情報を取得するためのセマンティック検索クエリを生成してください。
以下の観点を含めてください：
1. 質問の本質的な意図
2. ドキュメントから得られた新しい視点
3. 関連する概念の深堀り

5-10個の検索クエリをJSON形式で出力してください。
出力形式: {{"queries": ["クエリ1", "クエリ2", ...]}}

JSON以外は出力しないでください。""",
                input_variables=["original_question", "doc_summary"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(rag_query_prompt.format(
                    original_question=original_query,
                    doc_summary=doc_summary
                ))
            )
            
            try:
                result = json.loads(response.content)
                queries = result.get("queries", [])
                logger.info(f"Generated RAG queries: {queries}")
                return queries[:10]
            except json.JSONDecodeError:
                logger.error("Failed to parse RAG queries JSON response")
                return await self._mock_rag_queries(original_query)
                
        except Exception as e:
            logger.error(f"Error generating RAG queries: {e}")
            return await self._mock_rag_queries(original_query)
    
    async def semantic_search(self, queries: List[str]) -> List[Document]:
        """セマンティック検索を実行"""
        
        if not self.retriever:
            logger.warning("Retriever not available")
            return await self._mock_semantic_search_results(queries)
        
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
            return unique_docs[:10]  # 最大10ドキュメント
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return await self._mock_semantic_search_results(queries)
    
    async def generate_report(self, query: str, context_docs: List[Document]) -> str:
        """構造化レポートを生成"""
        
        if not self.llm:
            return await self._mock_report(query, context_docs)
        
        try:
            # コンテキストの準備
            context = "\n\n---\n\n".join([
                f"**出典**: {doc.metadata}\n**内容**: {doc.page_content}"
                for doc in context_docs[:10]
            ])
            
            report_prompt = PromptTemplate(
                template="""質問: {question}

以下の情報源を基に、構造化されたレポートを作成してください：

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
            return await self._mock_report(query, context_docs)
    
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
    
    # モック実装メソッド
    async def _mock_generate_keywords(self, query: str) -> List[str]:
        """モックキーワード生成"""
        words = query.split()
        keywords = words[:3] + ["AI", "技術", "開発", "情報"]
        return keywords[:8]
    
    async def _mock_search_results(self, keywords: List[str]) -> List[Document]:
        """モック検索結果"""
        mock_docs = []
        for i, keyword in enumerate(keywords[:3]):
            mock_docs.append(Document(
                page_content=f"Mock document content about {keyword}. This would contain real information from Google Drive or Chrome history.",
                metadata={"source": "mock", "title": f"Mock Doc {i+1}", "keyword": keyword}
            ))
        return mock_docs
    
    async def _mock_rag_queries(self, query: str) -> List[str]:
        """モックRAGクエリ"""
        return [
            f"{query} 詳細",
            f"{query} 技術仕様",
            f"{query} 事例",
            f"{query} 最新動向"
        ]
    
    async def _mock_semantic_search_results(self, queries: List[str]) -> List[Document]:
        """モックセマンティック検索結果"""
        mock_docs = []
        for i, query in enumerate(queries[:3]):
            mock_docs.append(Document(
                page_content=f"Relevant content for query: {query}",
                metadata={"source": "mock_search", "relevance_score": 0.8 - i*0.1}
            ))
        return mock_docs
    
    async def _mock_report(self, query: str, docs: List[Document]) -> str:
        """モックレポート"""
        return f"""# レポート: {query}

## 要約
{query}に関する情報を検索・分析した結果をまとめました。

## 詳細分析
検索された{len(docs)}件の情報源から以下の内容が確認されました：

{chr(10).join([f"- {doc.metadata.get('title', 'ソース')}: {doc.page_content[:100]}..." for doc in docs[:3]])}

## 重要ポイント
- モック実装による基本構造の確認
- MCP統合による外部データ取得
- FAISS による高速ベクトル検索

## 結論
{query}について、複数の情報源から総合的な情報を取得できました。

## 引用情報
{chr(10).join([f"{i+1}. {doc.metadata}" for i, doc in enumerate(docs[:5])])}

---
*このレポートはExtend Your Memoryシステムにより自動生成されました*
"""