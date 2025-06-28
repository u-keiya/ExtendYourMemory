"""
Adaptive FAISS Optimizer for Dynamic Search Parameter Adjustment
Implements query-complexity based optimization for vector search
"""

import logging
import time
from enum import Enum
from typing import Dict, Any, Optional, List
from langchain.docstore.document import Document

logger = logging.getLogger(__name__)

class QueryComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

class AdaptiveFAISSOptimizer:
    def __init__(self):
        self.search_history = []
        self.performance_metrics = {}
        
    
    def get_adaptive_search_params(self, query_analysis: Dict[str, Any], doc_count: int) -> Dict[str, Any]:
        """クエリ分析に基づく動的検索パラメータ調整"""
        
        try:
            intent = query_analysis.get('intent', '情報検索')
            complexity = query_analysis.get('complexity', '中程度')
            search_strategy = query_analysis.get('search_strategy', '包括検索')
            
            # ベースパラメータ
            base_params = {
                "search_type": "mmr",
                "k": 6,
                "fetch_k": 20,
                "lambda_mult": 0.5
            }
            
            # 検索意図による調整
            if intent == "事実確認":
                # 事実確認: 精度重視
                base_params.update({
                    "k": 3,
                    "fetch_k": 10,
                    "lambda_mult": 0.8  # 関連性重視
                })
            elif intent == "探索的検索":
                # 探索的検索: 多様性重視
                base_params.update({
                    "k": 10,
                    "fetch_k": 50,
                    "lambda_mult": 0.2  # 多様性重視
                })
            elif intent == "比較分析":
                # 比較分析: バランス重視
                base_params.update({
                    "k": 8,
                    "fetch_k": 30,
                    "lambda_mult": 0.4
                })
            
            # 複雑度による調整
            if complexity == "複雑":
                # 複雑なクエリ: より多くの候補を検討
                base_params["fetch_k"] = min(base_params["fetch_k"] * 2, 100)
                base_params["k"] = min(base_params["k"] + 2, 15)
            elif complexity == "単純":
                # 単純なクエリ: 効率重視
                base_params["fetch_k"] = max(base_params["fetch_k"] // 2, 5)
                base_params["k"] = max(base_params["k"] - 1, 3)
            
            # 検索戦略による調整
            if search_strategy == "精密検索":
                base_params["lambda_mult"] = min(base_params["lambda_mult"] + 0.2, 0.9)
            elif search_strategy == "探索検索":
                base_params["lambda_mult"] = max(base_params["lambda_mult"] - 0.2, 0.1)
            
            # ドキュメント数による調整
            if doc_count < 50:
                # 少数ドキュメント: より厳密に
                base_params["k"] = min(base_params["k"], doc_count // 2 + 1)
                base_params["fetch_k"] = min(base_params["fetch_k"], doc_count)
            
            logger.info(f"Adaptive FAISS params: {base_params}")
            logger.info(f"  Based on: {intent}/{complexity}/{search_strategy}, docs={doc_count}")
            
            return base_params
            
        except Exception as e:
            logger.error(f"Error generating adaptive search params: {e}")
            return {
                "search_type": "mmr",
                "k": 6,
                "fetch_k": 20,
                "lambda_mult": 0.5
            }
    
    def optimize_chunk_strategy(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """クエリ分析に基づくドキュメント分割戦略の最適化"""
        
        try:
            intent = analysis.get('intent', '情報検索')
            complexity = analysis.get('complexity', '中程度')
            domain = analysis.get('domain', '一般')
            
            # ベース設定
            chunk_config = {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "separators": ["\n\n", "\n", "。", ".", " ", ""]
            }
            
            # 検索意図による調整
            if intent == "事実確認":
                # 事実確認: 小さなチャンクで精密に
                chunk_config.update({
                    "chunk_size": 500,
                    "chunk_overlap": 100
                })
            elif intent == "探索的検索":
                # 探索的検索: 大きなチャンクで文脈を保持
                chunk_config.update({
                    "chunk_size": 1500,
                    "chunk_overlap": 300
                })
            
            # 複雑度による調整
            if complexity == "複雑":
                # 複雑なクエリ: オーバーラップを増やして文脈を保持
                chunk_config["chunk_overlap"] = min(chunk_config["chunk_overlap"] * 1.5, chunk_config["chunk_size"] // 2)
            
            # ドメインによる調整
            if domain == "技術":
                # 技術文書: コードブロックやセクションを考慮
                chunk_config["separators"] = ["```", "\n\n", "\n", "。", ".", " ", ""]
            elif domain == "学術":
                # 学術文書: パラグラフ単位を重視
                chunk_config["separators"] = ["\n\n", "\n", "。", "．", ".", " ", ""]
            
            logger.info(f"Optimized chunk strategy: {chunk_config}")
            return chunk_config
            
        except Exception as e:
            logger.error(f"Error optimizing chunk strategy: {e}")
            return {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "separators": ["\n\n", "\n", "。", ".", " ", ""]
            }
    
    
    
    
    
    
    
    
