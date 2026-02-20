"""Hybrid search using Reciprocal Rank Fusion (RRF) to merge FTS + vector results."""

from __future__ import annotations

from mainframe.memory.base import SearchResult


def reciprocal_rank_fusion(
    *result_lists: list[SearchResult],
    k: int = 60,
    max_results: int = 10,
) -> list[SearchResult]:
    """Merge multiple ranked result lists using RRF.

    RRF score = sum(1 / (k + rank)) across all lists where the document appears.
    k=60 is the standard constant from the original RRF paper.
    """
    # Key by content to deduplicate
    scores: dict[str, float] = {}
    best_result: dict[str, SearchResult] = {}

    for results in result_lists:
        for rank, result in enumerate(results):
            rrf_score = 1.0 / (k + rank + 1)
            key = result.content
            scores[key] = scores.get(key, 0.0) + rrf_score
            # Keep the result with the highest original score
            if key not in best_result or result.score > best_result[key].score:
                best_result[key] = result

    # Sort by fused score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    fused: list[SearchResult] = []
    for content, fused_score in ranked[:max_results]:
        result = best_result[content]
        fused.append(SearchResult(
            content=result.content,
            score=fused_score,
            source=result.source,
            metadata=result.metadata,
        ))

    return fused
