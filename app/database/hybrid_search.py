from __future__ import annotations
from typing import List, Dict, Any, Optional

from .vector_searcher import search_similar_documents, keyword_search_documents


def _rerank(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Enhanced reranking with semantic awareness"""
    query_terms = set(query.lower().split())
    
    def score_fn(item: Dict[str, Any]) -> float:
        base_score = item.get("score", 0.0)
        semantic_boost = item.get("semantic_boost", 0.0)
        meta = item.get("metadata", {})
        
        # Traditional boosting
        tags = meta.get("tags", "")
        tag_overlap = len([t for t in tags.split(',') if t.strip().lower() in query_terms])
        cat_match = 1 if meta.get("category") and meta["category"].lower() in query.lower() else 0
        loc_match = 1 if meta.get("location") and meta["location"].lower() in query.lower() else 0
        
        # Synthetic document type bonus (prefer diverse types)
        synthetic_bonus = 0.0
        if meta.get("synthetic_type") == "review" and "후기" in query.lower():
            synthetic_bonus = 0.05
        elif meta.get("synthetic_type") == "recommendation" and any(word in query.lower() for word in ["추천", "좋은", "어떤"]):
            synthetic_bonus = 0.05
        
        total_score = (base_score + 
                      semantic_boost + 
                      0.1 * tag_overlap + 
                      0.2 * cat_match + 
                      0.1 * loc_match + 
                      synthetic_bonus)
        
        return total_score
    
    return sorted(results, key=score_fn, reverse=True)


def hybrid_group_search(query: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Enhanced hybrid search combining dense, sparse, and semantic boosting"""
    # Get results from all search methods
    info_dense = search_similar_documents(query, top_k=top_k, collection="group-info", where=where, user_id=user_id)
    syn_dense = search_similar_documents(query, top_k=top_k, collection="group-synthetic", where=where, user_id=user_id)

    info_sparse = keyword_search_documents(query, top_k=top_k, collection="group-info", where=where, user_id=user_id)
    syn_sparse = keyword_search_documents(query, top_k=top_k, collection="group-synthetic", where=where, user_id=user_id)

    # Combine results with enhanced deduplication logic
    combined: Dict[str, Dict[str, Any]] = {}
    for item in info_dense + info_sparse + syn_dense + syn_sparse:
        gid = item.get("metadata", {}).get("groupId")
        if not gid:
            continue

        prev = combined.get(gid)
        if not prev:
            combined[gid] = item
            continue

        prev_origin = prev.get("origin")
        curr_origin = item.get("origin")
        prev_score = prev.get("score", 0)
        curr_score = item.get("score", 0)
        
        # Enhanced selection logic considering semantic boost
        prev_total_score = prev_score + prev.get("semantic_boost", 0)
        curr_total_score = curr_score + item.get("semantic_boost", 0)

        # Prefer real documents, but allow synthetic if significantly better semantically
        if prev_origin == "real" and curr_origin == "synthetic":
            if curr_total_score > prev_total_score + 0.1:  # Threshold for synthetic override
                combined[gid] = item
            continue

        if prev_origin == "synthetic" and curr_origin == "real":
            combined[gid] = item
            continue

        # For same origin, pick higher total score
        if curr_total_score > prev_total_score:
            combined[gid] = item

    reranked = _rerank(list(combined.values()), query)
    return reranked[:top_k]
