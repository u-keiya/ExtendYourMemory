"""
Adaptive FAISS Optimizer for Dynamic Search Parameter Adjustment
Implements query-complexity based optimization for vector search
"""

import logging
from typing import Dict, Any, Optional, List
from langchain.docstore.document import Document

logger = logging.getLogger(__name__)

class AdaptiveFAISSOptimizer:
    def __init__(self):
        self.search_history = []
        self.performance_metrics = {}
        
    def select_optimal_index_type(self, doc_count: int, query_complexity: str) -> str:
        """ドキュメント数とクエリ複雑度に基づく最適インデックス選択"""
        
        try:
            if doc_count < 1000:
                # 小規模: 正確性重視
                return "IndexFlatL2"
            elif doc_count < 10000:
                # 中規模: バランス型
                if query_complexity in ["単純", "中程度"]:
                    return "IndexIVFFlat"
                else:
                    return "IndexFlatL2"  # 複雑なクエリには正確性を優先
            elif doc_count < 100000:
                # 大規模: 効率重視
                if query_complexity == "単純":
                    return "IndexIVFPQ"
                else:
                    return "IndexIVFFlat"
            else:
                # 超大規模: 速度最優先
                return "IndexIVFPQ"
                
        except Exception as e:
            logger.error(f"Error selecting index type: {e}")
            return "IndexIVFFlat"  # デフォルト
    
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
    
    def analyze_search_quality(self, query: str, results: List[Document], user_feedback: Optional[float] = None) -> Dict[str, Any]:
        """検索品質の分析と学習"""
        
        try:
            quality_metrics = {
                "result_count": len(results),
                "diversity_score": self._calculate_diversity(results),
                "length_distribution": self._analyze_length_distribution(results),
                "source_distribution": self._analyze_source_distribution(results),
                "user_feedback": user_feedback
            }
            
            # 品質スコアの計算
            quality_score = self._calculate_quality_score(quality_metrics)
            quality_metrics["overall_quality"] = quality_score
            
            # 履歴に記録
            self.search_history.append({
                "query": query,
                "metrics": quality_metrics,
                "timestamp": self._get_timestamp()
            })
            
            # 履歴サイズ制限
            if len(self.search_history) > 100:
                self.search_history = self.search_history[-50:]
            
            logger.info(f"Search quality analysis: score={quality_score:.2f}, diversity={quality_metrics['diversity_score']:.2f}")
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error analyzing search quality: {e}")
            return {"overall_quality": 0.5}
    
    def get_optimization_recommendations(self, recent_searches: int = 10) -> Dict[str, Any]:
        """最近の検索結果に基づく最適化推奨事項"""
        
        try:
            if len(self.search_history) < 3:
                return {"recommendations": ["Insufficient data for recommendations"]}
            
            recent_history = self.search_history[-recent_searches:]
            
            # 平均品質分析
            avg_quality = sum(search["metrics"]["overall_quality"] for search in recent_history) / len(recent_history)
            
            recommendations = []
            
            # 品質に基づく推奨
            if avg_quality < 0.4:
                recommendations.append("Consider increasing fetch_k parameter for broader search")
                recommendations.append("Try using more specific primary keywords")
            elif avg_quality > 0.8:
                recommendations.append("Current settings perform well, consider optimizing for speed")
            
            # 多様性分析
            avg_diversity = sum(search["metrics"]["diversity_score"] for search in recent_history) / len(recent_history)
            if avg_diversity < 0.3:
                recommendations.append("Increase lambda_mult to improve result diversity")
            
            # 結果数分析
            avg_result_count = sum(search["metrics"]["result_count"] for search in recent_history) / len(recent_history)
            if avg_result_count < 3:
                recommendations.append("Consider broadening search terms or increasing max_results")
            elif avg_result_count > 20:
                recommendations.append("Consider more specific search terms to reduce noise")
            
            return {
                "avg_quality": avg_quality,
                "avg_diversity": avg_diversity,
                "avg_result_count": avg_result_count,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
            return {"recommendations": ["Analysis failed"]}
    
    def _calculate_diversity(self, results: List[Document]) -> float:
        """結果の多様性スコアを計算"""
        try:
            if len(results) <= 1:
                return 0.0
            
            # ソースの多様性
            sources = set()
            for doc in results:
                source = doc.metadata.get('source', 'unknown')
                sources.add(source)
            
            source_diversity = len(sources) / len(results)
            
            # 長さの多様性
            lengths = [len(doc.page_content) for doc in results]
            if len(set(lengths)) > 1:
                length_diversity = len(set(lengths)) / len(results)
            else:
                length_diversity = 0.0
            
            return (source_diversity + length_diversity) / 2
            
        except Exception as e:
            logger.error(f"Error calculating diversity: {e}")
            return 0.0
    
    def _analyze_length_distribution(self, results: List[Document]) -> Dict[str, float]:
        """結果の長さ分布を分析"""
        try:
            if not results:
                return {"avg_length": 0, "min_length": 0, "max_length": 0}
            
            lengths = [len(doc.page_content) for doc in results]
            return {
                "avg_length": sum(lengths) / len(lengths),
                "min_length": min(lengths),
                "max_length": max(lengths)
            }
        except Exception as e:
            logger.error(f"Error analyzing length distribution: {e}")
            return {"avg_length": 0, "min_length": 0, "max_length": 0}
    
    def _analyze_source_distribution(self, results: List[Document]) -> Dict[str, int]:
        """結果のソース分布を分析"""
        try:
            source_count = {}
            for doc in results:
                source = doc.metadata.get('source', 'unknown')
                source_count[source] = source_count.get(source, 0) + 1
            return source_count
        except Exception as e:
            logger.error(f"Error analyzing source distribution: {e}")
            return {}
    
    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """総合品質スコアを計算"""
        try:
            score = 0.0
            weights = 0.0
            
            # 結果数スコア (3-10が理想)
            result_count = metrics["result_count"]
            if 3 <= result_count <= 10:
                score += 0.4 * 1.0
            elif result_count > 0:
                score += 0.4 * (1.0 - abs(result_count - 6.5) / 10)
            weights += 0.4
            
            # 多様性スコア
            diversity = metrics.get("diversity_score", 0)
            score += 0.3 * diversity
            weights += 0.3
            
            # ユーザーフィードバック
            if metrics.get("user_feedback") is not None:
                score += 0.3 * metrics["user_feedback"]
                weights += 0.3
            
            return score / weights if weights > 0 else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0.5
    
    def _get_timestamp(self) -> float:
        """現在のタイムスタンプを取得"""
        import time
        return time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """オプティマイザーの状態を取得"""
        return {
            "total_searches": len(self.search_history),
            "optimization_active": True,
            "adaptive_parameters": True,
            "quality_tracking": True,
            "recent_avg_quality": (
                sum(s["metrics"]["overall_quality"] for s in self.search_history[-10:]) / min(len(self.search_history), 10)
                if self.search_history else 0.0
            )
        }