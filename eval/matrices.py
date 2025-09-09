import numpy as np
from typing import List, Dict
from sklearn.metrics import ndcg_score

def precision_at_k(relevant_items: List[bool], k: int) -> float:
    """
    Calculate Precision@k
    """
    if len(relevant_items) < k:
        k = len(relevant_items)
    top_k = relevant_items[:k]
    return sum(top_k) / k

def average_precision(relevant_items: List[bool]) -> float:
    """
    Calculate Average Precision
    """
    precisions = []
    relevant_count = 0
    
    for i, is_relevant in enumerate(relevant_items):
        if is_relevant:
            relevant_count += 1
            precisions.append(relevant_count / (i + 1))
    
    if not precisions:
        return 0.0
    
    return sum(precisions) / len(precisions)

def mean_average_precision(all_relevant_items: List[List[bool]]) -> float:
    """
    Calculate Mean Average Precision (MAP)
    """
    aps = [average_precision(relevant_items) for relevant_items in all_relevant_items]
    return sum(aps) / len(aps) if aps else 0.0

def normalized_dcg(relevance_scores: List[float], k: int = None) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain (nDCG)
    """
    if k is None:
        k = len(relevance_scores)
    
    # Ensure we have at least k elements
    scores = relevance_scores[:k]
    ideal_scores = sorted(relevance_scores, reverse=True)[:k]
    
    # Calculate DCG
    dcg = sum(score / np.log2(i + 2) for i, score in enumerate(scores))
    
    # Calculate ideal DCG
    ideal_dcg = sum(score / np.log2(i + 2) for i, score in enumerate(ideal_scores))
    
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0

class EvaluationMetrics:
    def __init__(self):
        self.all_relevant_items = []
        self.all_relevance_scores = []
    
    def add_query_results(self, ranked_results: List[bool], relevance_scores: List[float]):
        """
        Add results from one query for evaluation
        """
        self.all_relevant_items.append(ranked_results)
        self.all_relevance_scores.append(relevance_scores)
    
    def calculate_all_metrics(self, k: int = 5) -> Dict[str, float]:
        """
        Calculate all evaluation metrics
        """
        metrics = {}
        
        # Precision@k
        p_at_k = [precision_at_k(relevant_items, k) 
                 for relevant_items in self.all_relevant_items]
        metrics[f"P@{k}"] = sum(p_at_k) / len(p_at_k) if p_at_k else 0.0
        
        # MAP
        metrics["MAP"] = mean_average_precision(self.all_relevant_items)
        
        # nDCG
        ndcg_scores = [normalized_dcg(scores, k) 
                      for scores in self.all_relevance_scores]
        metrics[f"nDCG@{k}"] = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
        
        return metrics