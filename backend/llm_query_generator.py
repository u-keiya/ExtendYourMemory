"""
LLM-Only Query Generator for Extend Your Memory
All keyword and query generation is handled by LLM with sophisticated prompts
"""

import json
import asyncio
from typing import List, Dict, Any
import logging
from langchain.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class LLMQueryGenerator:
    def __init__(self, llm):
        self.llm = llm
        
    async def generate_diverse_keywords(self, user_query: str) -> Dict[str, Any]:
        """LLMを使用して多様なキーワードを生成"""
        
        if not self.llm:
            logger.error("LLM not available for keyword generation")
            return {"all_keywords": []}
        
        try:
            keyword_prompt = PromptTemplate(
                template="""あなたは高度な検索キーワード生成AIです。ファイル検索のために多様なキーワードを5～10個生成してください。各キーワードは2～3つのワードから構成し，空白区切りをしてください．これによりAND検索が可能になり，文書の絞り込みが行えます．

                # ユーザーの質問
                "{question}"

                厳密にJSON形式のみ出力：
                {{
                    "all_keywords": ["リスト"]
                }}""",
                input_variables=["question"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(keyword_prompt.format(question=user_query))
            )
            
            # JSONレスポンスを解析
            try:
                # マークダウンコードブロックを除去
                content = response.content.strip()
                if content.startswith("```json"):
                    content = content[7:]  # ```json を除去
                if content.startswith("```"):
                    content = content[3:]   # ``` を除去
                if content.endswith("```"):
                    content = content[:-3]  # 末尾の ``` を除去
                content = content.strip()
                
                result = json.loads(content)
                logger.info(f"LLM generated keywords: {len(result.get('all_keywords', []))}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM keyword JSON response: {e}")
                logger.error(f"Raw response: {response.content[:500]}")
                raise RuntimeError("キーワード生成に失敗しました。もう一度お試しください。")
                
        except Exception as e:
            logger.error(f"Error in LLM keyword generation: {e}")
            raise RuntimeError("キーワード生成中にエラーが発生しました。もう一度お試しください。")
    
    async def generate_rag_queries(self, original_query: str) -> List[str]:
        """LLMを使用してRAG検索クエリを生成"""
        
        if not self.llm:
            logger.error("LLM not available for RAG query generation")
            return []
        
        try:
            rag_prompt = PromptTemplate(
                template="""あなたは創造的なRAG探索の専門家です。ユーザーの質問を多角的に分析し、包括的な検索クエリを5～10個生成してください。

                # ユーザーの質問
                "{original_question}"

                厳密にJSON形式で出力：
                {{
                    "all_queries": ["リスト"]
                }}""",
                input_variables=["original_question"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(rag_prompt.format(
                    original_question=original_query
                ))
            )
            
            try:
                # マークダウンコードブロックを除去
                content = response.content.strip()
                if content.startswith("```json"):
                    content = content[7:]  # ```json を除去
                if content.startswith("```"):
                    content = content[3:]   # ``` を除去
                if content.endswith("```"):
                    content = content[:-3]  # 末尾の ``` を除去
                content = content.strip()
                
                result = json.loads(content)
                all_queries = result.get("all_queries", [])
                logger.info(f"LLM generated {len(all_queries)} RAG queries")
                return all_queries[:15]  # 最大15個
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM RAG query JSON response: {e}")
                logger.error(f"Raw response: {response.content[:500]}")
                raise RuntimeError("RAGクエリ生成に失敗しました。もう一度お試しください。")
                
        except Exception as e:
            logger.error(f"Error in LLM RAG query generation: {e}")
            raise RuntimeError("RAGクエリ生成中にエラーが発生しました。もう一度お試しください。")
    
