"""
Advanced LLM Query Generator with AGR (Analyze-Generate-Refine) Framework
Implements state-of-the-art query expansion and refinement techniques
"""

import json
import time
import asyncio
from typing import List, Dict, Any, Optional
import logging
from langchain.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class LLMQueryGenerator:
    def __init__(self, llm):
        self.llm = llm
        self.search_history = []  # For learning successful patterns
        
    async def analyze_query_intent(self, user_query: str) -> Dict[str, Any]:
        """AGR Step 1: ユーザークエリの意図と複雑度を分析"""
        
        if not self.llm:
            logger.error("LLM not available for query analysis")
            return {"intent": "unknown", "complexity": "medium", "sources": ["google_drive"]}
        
        try:
            analysis_prompt = PromptTemplate(
                template="""あなたは検索クエリ分析の専門家です。以下のユーザークエリを詳細に分析してください。

                # ユーザークエリ
                "{query}"

                以下の観点で分析し、JSON形式で出力してください：

                厳密にJSON形式のみ出力：
                {{
                    "intent": "情報検索|問題解決|比較分析|事実確認|探索的検索",
                    "complexity": "単純|中程度|複雑",
                    "time_constraint": "最新|期間指定|時系列|なし",
                    "required_sources": ["google_drive", "chrome_history", "web_content"],
                    "search_scope": "狭い|中程度|広い",
                    "domain": "技術|ビジネス|学術|一般|専門分野",
                    "key_concepts": ["概念1", "概念2"],
                    "search_strategy": "精密検索|探索検索|包括検索"
                }}""",
                input_variables=["query"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(analysis_prompt.format(query=user_query))
            )
            
            content = self._parse_json_response(response.content)
            analysis = json.loads(content)
            
            logger.info(f"Query analysis: {analysis.get('intent')} / {analysis.get('complexity')} / {analysis.get('search_strategy')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in query analysis: {e}")
            # デフォルト分析結果を返す
            return {
                "intent": "情報検索",
                "complexity": "中程度",
                "time_constraint": "なし",
                "required_sources": ["google_drive", "chrome_history"],
                "search_scope": "中程度",
                "domain": "一般",
                "key_concepts": [user_query],
                "search_strategy": "包括検索"
            }

    async def generate_hierarchical_keywords(self, user_query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """AGR Step 2: 分析結果に基づく階層的キーワード生成"""
        
        if not self.llm:
            logger.error("LLM not available for keyword generation")
            return {"primary_keywords": [], "secondary_keywords": [], "context_keywords": [], "negative_keywords": []}
        
        try:
            # 検索戦略に基づくプロンプト調整
            strategy = analysis.get('search_strategy', '包括検索')
            complexity = analysis.get('complexity', '中程度')
            domain = analysis.get('domain', '一般')
            
            keyword_prompt = PromptTemplate(
                template="""あなたは高度な検索キーワード戦略の専門家です。以下の分析結果に基づいて、階層的なキーワード戦略を生成してください。

                # 元のクエリ
                "{query}"

                # 分析結果
                検索意図: {intent}
                複雑度: {complexity}
                ドメイン: {domain}
                検索戦略: {strategy}
                主要概念: {concepts}

                以下の階層でキーワードを生成してください：
                1. 必須キーワード (primary_keywords): AND検索で使用、最も重要な2-4個
                2. 関連キーワード (secondary_keywords): OR検索で使用、関連概念や同義語5-8個
                3. 文脈キーワード (context_keywords): 文脈理解を助ける補完キーワード3-5個
                4. 除外キーワード (negative_keywords): 無関係な結果を除外する1-3個

                各キーワードは検索効率を考慮し、フレーズは2-3語以内に抑えてください。

                厳密にJSON形式のみ出力：
                {{
                    "primary_keywords": ["必須キーワード1", "必須キーワード2"],
                    "secondary_keywords": ["関連キーワード1", "関連キーワード2"],
                    "context_keywords": ["文脈キーワード1", "文脈キーワード2"],
                    "negative_keywords": ["除外キーワード1"],
                    "search_confidence": 0.8,
                    "strategy_used": "戦略名"
                }}""",
                input_variables=["query", "intent", "complexity", "domain", "strategy", "concepts"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(keyword_prompt.format(
                    query=user_query,
                    intent=analysis.get('intent', '情報検索'),
                    complexity=complexity,
                    domain=domain,
                    strategy=strategy,
                    concepts=', '.join(analysis.get('key_concepts', [user_query]))
                ))
            )
            
            content = self._parse_json_response(response.content)
            result = json.loads(content)
            
            # キーワード統計をログ出力
            total_keywords = (len(result.get('primary_keywords', [])) + 
                            len(result.get('secondary_keywords', [])) + 
                            len(result.get('context_keywords', [])))
            
            logger.info(f"Generated hierarchical keywords: {total_keywords} total")
            logger.info(f"  Primary: {len(result.get('primary_keywords', []))}, Secondary: {len(result.get('secondary_keywords', []))}")
            logger.info(f"  Context: {len(result.get('context_keywords', []))}, Negative: {len(result.get('negative_keywords', []))}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in hierarchical keyword generation: {e}")
            # フォールバック: シンプルなキーワード生成
            return await self._fallback_keyword_generation(user_query)

    async def generate_diverse_keywords(self, user_query: str) -> Dict[str, Any]:
        """AGRフレームワークを使用した高度なキーワード生成"""
        
        try:
            # Step 1: クエリ分析
            analysis = await self.analyze_query_intent(user_query)
            
            # Step 2: 階層的キーワード生成
            hierarchical_keywords = await self.generate_hierarchical_keywords(user_query, analysis)
            
            # Step 3: 改善のための結果統合
            all_keywords = []
            all_keywords.extend(hierarchical_keywords.get('primary_keywords', []))
            all_keywords.extend(hierarchical_keywords.get('secondary_keywords', []))
            all_keywords.extend(hierarchical_keywords.get('context_keywords', []))
            
            # 重複除去
            unique_keywords = []
            seen = set()
            for keyword in all_keywords:
                if keyword.lower() not in seen:
                    unique_keywords.append(keyword)
                    seen.add(keyword.lower())
            
            result = {
                'all_keywords': unique_keywords[:20],  # 最大20個に制限
                'hierarchical': hierarchical_keywords,
                'analysis': analysis
            }
            
            logger.info(f"AGR framework generated {len(unique_keywords)} unique keywords")
            return result
            
        except Exception as e:
            logger.error(f"Error in AGR keyword generation: {e}")
            # フォールバック: 従来の方法
            return await self._fallback_keyword_generation(user_query)
    
    async def generate_multi_perspective_queries(self, original_query: str, initial_results: Optional[List] = None) -> List[str]:
        """AGR Step 3: 多角的なRAG検索クエリを生成（初回結果による改善を含む）"""
        
        if not self.llm:
            logger.error("LLM not available for RAG query generation")
            return []
        
        try:
            # 初回検索結果がある場合は改善プロンプトを使用
            if initial_results and len(initial_results) > 0:
                return await self._refine_queries_with_results(original_query, initial_results)
            
            rag_prompt = PromptTemplate(
                template="""あなたはRAG検索の専門家です。以下のユーザークエリに対して、多角的で効果的な検索クエリを生成してください。

                # 元のクエリ
                "{original_question}"

                以下の戦略を組み合わせて、多様で効果的な検索クエリを生成してください：
                1. クエリ分解: 複雑なクエリを構成要素に分割
                2. 観点変更: 異なる視点から同じ情報を探索
                3. 具体化: 抽象的な概念を具体例で検索
                4. 一般化: 具体的な質問をより広い概念で検索
                5. 時系列: 時間軸を考慮した検索
                6. 因果関係: 原因と結果の両面から検索

                厳密にJSON形式で出力：
                {{
                    "decomposed_queries": ["分解クエリ1", "分解クエリ2"],
                    "perspective_queries": ["視点変更クエリ1", "視点変更クエリ2"],
                    "specific_queries": ["具体化クエリ1", "具体化クエリ2"],
                    "general_queries": ["一般化クエリ1", "一般化クエリ2"],
                    "temporal_queries": ["時系列クエリ1"],
                    "causal_queries": ["因果関係クエリ1"],
                    "all_queries": ["統合された全クエリリスト"]
                }}""",
                input_variables=["original_question"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(rag_prompt.format(
                    original_question=original_query
                ))
            )
            
            content = self._parse_json_response(response.content)
            result = json.loads(content)
            all_queries = result.get("all_queries", [])
            
            # クエリ多様性のログ
            logger.info(f"Generated multi-perspective queries: {len(all_queries)} total")
            for strategy, queries in result.items():
                if strategy != "all_queries" and isinstance(queries, list):
                    logger.info(f"  {strategy}: {len(queries)} queries")
            
            return all_queries[:15]  # 最大15個
            
        except Exception as e:
            logger.error(f"Error in multi-perspective query generation: {e}")
            # フォールバック
            return await self._fallback_rag_queries(original_query)

    async def generate_rag_queries(self, original_query: str) -> List[str]:
        """後方互換性のためのラッパー関数"""
        return await self.generate_multi_perspective_queries(original_query)
    
    async def _refine_queries_with_results(self, original_query: str, initial_results: List) -> List[str]:
        """初回検索結果を基にクエリを改善 (AGR Refine段階)"""
        
        try:
            # 初回結果の品質分析
            result_analysis = self._analyze_initial_results(initial_results)
            
            refine_prompt = PromptTemplate(
                template="""あなたは検索改善の専門家です。初回検索結果を分析し、より効果的なクエリを生成してください。

                # 元のクエリ
                "{original_query}"

                # 初回検索結果の分析
                結果数: {result_count}
                関連性: {relevance_score}
                カバレッジ: {coverage_analysis}
                不足している要素: {missing_elements}

                初回結果の課題を踏まえ、以下の改善策を適用したクエリを生成してください：
                1. 不足要素を補完するクエリ
                2. より具体的な検索クエリ
                3. 異なる角度からのアプローチ
                4. 関連性を高めるためのクエリ

                厳密にJSON形式で出力：
                {{
                    "refined_queries": ["改善クエリ1", "改善クエリ2"],
                    "complementary_queries": ["補完クエリ1", "補完クエリ2"],
                    "specific_queries": ["具体化クエリ1", "具体化クエリ2"],
                    "alternative_queries": ["代替クエリ1", "代替クエリ2"],
                    "all_queries": ["全改善クエリリスト"]
                }}""",
                input_variables=["original_query", "result_count", "relevance_score", "coverage_analysis", "missing_elements"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(refine_prompt.format(
                    original_query=original_query,
                    result_count=len(initial_results),
                    relevance_score=result_analysis.get('relevance_score', 'unknown'),
                    coverage_analysis=result_analysis.get('coverage', 'limited'),
                    missing_elements=', '.join(result_analysis.get('missing_elements', []))
                ))
            )
            
            content = self._parse_json_response(response.content)
            result = json.loads(content)
            refined_queries = result.get("all_queries", [])
            
            logger.info(f"Refined {len(refined_queries)} queries based on initial results")
            return refined_queries[:10]  # 改善クエリは10個まで
            
        except Exception as e:
            logger.error(f"Error in query refinement: {e}")
            return await self._fallback_rag_queries(original_query)

    def _analyze_initial_results(self, results: List) -> Dict[str, Any]:
        """初回検索結果の品質分析"""
        try:
            if not results:
                return {
                    'relevance_score': 'poor',
                    'coverage': 'none',
                    'missing_elements': ['no results found']
                }
            
            # 簡単な分析ロジック
            result_count = len(results)
            
            if result_count < 3:
                relevance = 'poor'
                coverage = 'limited'
                missing = ['insufficient results', 'need broader search']
            elif result_count < 10:
                relevance = 'moderate'
                coverage = 'partial'
                missing = ['need more specific terms']
            else:
                relevance = 'good'
                coverage = 'comprehensive'
                missing = ['consider refinement for precision']
            
            return {
                'relevance_score': relevance,
                'coverage': coverage,
                'missing_elements': missing
            }
            
        except Exception as e:
            logger.error(f"Error analyzing initial results: {e}")
            return {
                'relevance_score': 'unknown',
                'coverage': 'unknown',
                'missing_elements': ['analysis failed']
            }

    def _parse_json_response(self, content: str) -> str:
        """JSONレスポンスのパース処理を統一"""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    async def _fallback_keyword_generation(self, user_query: str) -> Dict[str, Any]:
        """フォールバック用のシンプルなキーワード生成"""
        try:
            simple_prompt = PromptTemplate(
                template="""以下のクエリから重要なキーワードを5個生成してください："{query}"
                
                JSON形式で出力：
                {{
                    "all_keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"]
                }}""",
                input_variables=["query"]
            )
            
            response = await asyncio.to_thread(
                lambda: self.llm.invoke(simple_prompt.format(query=user_query))
            )
            
            content = self._parse_json_response(response.content)
            result = json.loads(content)
            
            return {
                'all_keywords': result.get('all_keywords', [user_query]),
                'hierarchical': {
                    'primary_keywords': result.get('all_keywords', [user_query])[:2],
                    'secondary_keywords': result.get('all_keywords', [user_query])[2:],
                    'context_keywords': [],
                    'negative_keywords': []
                },
                'analysis': {'intent': '情報検索', 'complexity': '中程度'}
            }
            
        except Exception as e:
            logger.error(f"Fallback keyword generation failed: {e}")
            return {
                'all_keywords': [user_query],
                'hierarchical': {
                    'primary_keywords': [user_query],
                    'secondary_keywords': [],
                    'context_keywords': [],
                    'negative_keywords': []
                },
                'analysis': {'intent': '情報検索', 'complexity': '中程度'}
            }

    async def _fallback_rag_queries(self, original_query: str) -> List[str]:
        """フォールバック用のシンプルなRAGクエリ生成"""
        try:
            # 単純な変形クエリを生成
            variations = [
                original_query,
                f"What is {original_query}?",
                f"How to {original_query}?",
                f"{original_query} について",
                f"{original_query} 方法"
            ]
            
            logger.info(f"Using fallback RAG queries: {len(variations)}")
            return variations[:5]
            
        except Exception as e:
            logger.error(f"Fallback RAG queries failed: {e}")
            return [original_query]

    def record_search_success(self, query: str, keywords: Dict[str, Any], result_quality: float):
        """成功した検索パターンを記録 (将来の学習機能用)"""
        try:
            success_record = {
                'query': query,
                'keywords': keywords,
                'quality': result_quality,
                'timestamp': time.time()
            }
            
            self.search_history.append(success_record)
            
            # 履歴サイズ制限
            if len(self.search_history) > 100:
                self.search_history = self.search_history[-50:]
            
            logger.info(f"Recorded search success pattern for query: {query[:50]}...")
            
        except Exception as e:
            logger.error(f"Error recording search success: {e}")

    def get_search_insights(self) -> Dict[str, Any]:
        """検索パターンの分析結果を取得"""
        try:
            if not self.search_history:
                return {'total_searches': 0, 'insights': 'No data available'}
            
            total_searches = len(self.search_history)
            avg_quality = sum(record['quality'] for record in self.search_history) / total_searches
            
            return {
                'total_searches': total_searches,
                'average_quality': avg_quality,
                'insights': f'Recorded {total_searches} searches with average quality {avg_quality:.2f}'
            }
            
        except Exception as e:
            logger.error(f"Error getting search insights: {e}")
            return {'total_searches': 0, 'insights': 'Analysis failed'}