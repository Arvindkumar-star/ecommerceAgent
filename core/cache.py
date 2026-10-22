"""
Multi-Tenant Semantic and Exact Cache Layer.
Ensures zero cross-company or cross-customer cache leakage.
Invalidates company cache entries on document updates or deletions.
"""

import hashlib
import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np

from core.knowledge_base import embedding_service


@dataclass
class CacheEntry:
    company_id: str
    customer_id: Optional[str]
    query: str
    response: str
    sources: List[Dict[str, Any]]
    embedding: np.ndarray
    timestamp: datetime.datetime
    hits: int = 0
    cost_saved: float = 0.0


class MultiTenantSemanticCache:
    """
    Two-tiered cache (Exact Hash + Semantic Cosine Similarity).
    Partitioned strictly by company_id and customer_id to prevent any cross-tenant leakage.
    """

    def __init__(self, similarity_threshold: float = 0.95, ttl_hours: int = 24):
        self.exact_cache: Dict[str, CacheEntry] = {}
        # semantic_cache partitioned by company_id
        self.semantic_cache: Dict[str, List[CacheEntry]] = {}
        self.similarity_threshold = similarity_threshold
        self.ttl = datetime.timedelta(hours=ttl_hours)

        self.stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "misses": 0,
            "total_cost_saved": 0.0
        }

    def _hash_key(self, company_id: str, customer_id: Optional[str], query: str) -> str:
        cust_scope = customer_id.strip().lower() if customer_id else "public"
        norm_query = query.lower().strip()
        h = hashlib.sha256(f"{company_id}:{cust_scope}:{norm_query}".encode()).hexdigest()
        return f"{company_id}:{cust_scope}:{h}"

    def _is_expired(self, entry: CacheEntry) -> bool:
        return datetime.datetime.now() - entry.timestamp > self.ttl

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get(
        self,
        company_id: str,
        query: str,
        customer_id: Optional[str] = None,
        estimated_cost: float = 0.02
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response strictly within the company and customer scope.
        """
        exact_key = self._hash_key(company_id, customer_id, query)

        # 1. Exact match check
        if exact_key in self.exact_cache:
            entry = self.exact_cache[exact_key]
            if not self._is_expired(entry):
                entry.hits += 1
                entry.cost_saved += estimated_cost
                self.stats["exact_hits"] += 1
                self.stats["total_cost_saved"] += estimated_cost
                return {
                    "response": entry.response,
                    "sources": entry.sources,
                    "cache_type": "exact",
                    "hits": entry.hits
                }
            else:
                del self.exact_cache[exact_key]

        # 2. Semantic vector check within the company
        company_entries = self.semantic_cache.get(company_id, [])
        if not company_entries:
            self.stats["misses"] += 1
            return None

        try:
            query_emb = embedding_service.embed_text(query)
        except Exception:
            self.stats["misses"] += 1
            return None

        best_entry: Optional[CacheEntry] = None
        best_sim = 0.0

        active_entries = []
        for entry in company_entries:
            if self._is_expired(entry):
                continue
            active_entries.append(entry)

            # Strict customer scope check: customer-specific cache cannot be served to different customer
            if entry.customer_id != customer_id:
                continue

            sim = self._cosine_similarity(query_emb, entry.embedding)
            if sim > best_sim:
                best_sim = sim
                best_entry = entry

        self.semantic_cache[company_id] = active_entries

        if best_entry and best_sim >= self.similarity_threshold:
            best_entry.hits += 1
            best_entry.cost_saved += estimated_cost
            self.stats["semantic_hits"] += 1
            self.stats["total_cost_saved"] += estimated_cost
            return {
                "response": best_entry.response,
                "sources": best_entry.sources,
                "cache_type": "semantic",
                "similarity": round(best_sim, 4),
                "hits": best_entry.hits
            }

        self.stats["misses"] += 1
        return None

    def set(
        self,
        company_id: str,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
        customer_id: Optional[str] = None
    ):
        """
        Stores response in cache. Bounded to company_id and customer_id.
        """
        try:
            emb = embedding_service.embed_text(query)
        except Exception:
            emb = np.zeros(10, dtype=np.float32)

        entry = CacheEntry(
            company_id=company_id,
            customer_id=customer_id,
            query=query,
            response=response,
            sources=sources,
            embedding=emb,
            timestamp=datetime.datetime.now()
        )

        exact_key = self._hash_key(company_id, customer_id, query)
        self.exact_cache[exact_key] = entry

        if company_id not in self.semantic_cache:
            self.semantic_cache[company_id] = []
        self.semantic_cache[company_id].append(entry)

    def invalidate_company(self, company_id: str):
        """
        Invalidates all cache entries for a company when documents are uploaded or deleted.
        """
        keys_to_del = [k for k in self.exact_cache if k.startswith(f"{company_id}:")]
        for k in keys_to_del:
            del self.exact_cache[k]

        if company_id in self.semantic_cache:
            del self.semantic_cache[company_id]


# Global cache singleton
semantic_cache = MultiTenantSemanticCache()
