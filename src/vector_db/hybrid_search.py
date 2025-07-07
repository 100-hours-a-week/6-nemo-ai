from __future__ import annotations
from typing import List, Dict, Any, Optional

from .vector_searcher import search_similar_documents


def _rerank(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    query_terms = set(query.lower().split())
    def score_fn(item: Dict[str, Any]) -> float:
        base = item.get("score", 0.0)
        meta = item.get("metadata", {})
        tags = meta.get("tags", "")
        overlap = len([t for t in tags.split(',') if t.strip().lower() in query_terms])
        cat_match = 1 if meta.get("category") and meta["category"].lower() in query.lower() else 0
        loc_match = 1 if meta.get("location") and meta["location"].lower() in query.lower() else 0
        return base + 0.1 * overlap + 0.2 * cat_match + 0.1 * loc_match
    return sorted(results, key=score_fn, reverse=True)


def hybrid_group_search(query: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    info_results = search_similar_documents(query, top_k=top_k, collection="group-info", where=where, user_id=user_id)
    syn_results = search_similar_documents(query, top_k=top_k, collection="group-synthetic", where=where, user_id=user_id)

    combined: Dict[str, Dict[str, Any]] = {}
    for item in info_results + syn_results:
        gid = item.get("metadata", {}).get("groupId")
        if not gid:
            continue
        prev = combined.get(gid)
        if not prev or item["score"] > prev["score"]:
            combined[gid] = item

    reranked = _rerank(list(combined.values()), query)
    return reranked[:top_k]
