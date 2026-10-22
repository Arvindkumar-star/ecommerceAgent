"""
Real Observability and Metrics Module.
Tracks actual observed query execution times, tool usages, cache hits, and errors.
Zero invented values or fake analytics.
"""

import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
import numpy as np

from core.knowledge_base import get_db_connection


class PlatformMetrics:
    """Manages real telemetry and analytics persisted in SQLite."""

    def log_query(
        self,
        company_id: str,
        query: str,
        total_latency: float,
        steps: int,
        tools_used: List[str],
        from_cache: bool = False,
        error: Optional[str] = None
    ):
        """Persists a real query execution record to the database."""
        now = datetime.datetime.now().isoformat()
        log_id = str(uuid.uuid4())
        tools_json = json.dumps(tools_used)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO metrics (id, company_id, query, from_cache, total_latency, steps, tools_used, error, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_id, company_id, query, 1 if from_cache else 0, total_latency, steps, tools_json, error, now)
            )
            conn.commit()

    def get_summary(self, company_id: str) -> Dict[str, Any]:
        """
        Calculates aggregated metrics strictly from real logged activity for this company.
        Never invents statistics.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT query, from_cache, total_latency, steps, tools_used, error, timestamp
                   FROM metrics WHERE company_id = ? ORDER BY timestamp DESC""",
                (company_id,)
            )
            rows = cursor.fetchall()

        if not rows:
            return {
                "has_activity": False,
                "total_queries": 0,
                "message": "No activity yet. Start chatting or test agent queries to record metrics."
            }

        total_queries = len(rows)
        latencies = [r["total_latency"] for r in rows]
        cache_hits = sum(1 for r in rows if r["from_cache"] == 1)
        error_count = sum(1 for r in rows if r["error"] is not None)
        steps_list = [r["steps"] for r in rows]

        tool_counts: Dict[str, int] = {}
        for r in rows:
            try:
                tools = json.loads(r["tools_used"])
                for t in tools:
                    tool_counts[t] = tool_counts.get(t, 0) + 1
            except Exception:
                pass

        return {
            "has_activity": True,
            "total_queries": total_queries,
            "avg_latency_ms": round(float(np.mean(latencies)) * 1000, 1),
            "p95_latency_ms": round(float(np.percentile(latencies, 95)) * 1000, 1) if len(latencies) > 1 else round(latencies[0] * 1000, 1),
            "cache_hit_rate": round(cache_hits / total_queries, 3) if total_queries > 0 else 0.0,
            "cache_hits": cache_hits,
            "error_rate": round(error_count / total_queries, 3) if total_queries > 0 else 0.0,
            "avg_steps": round(float(np.mean(steps_list)), 1) if steps_list else 0.0,
            "tool_usage": tool_counts
        }

    def get_recent_logs(self, company_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Returns the most recent actual query executions."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, query, from_cache, total_latency, steps, tools_used, error, timestamp
                   FROM metrics WHERE company_id = ? ORDER BY timestamp DESC LIMIT ?""",
                (company_id, limit)
            )
            rows = cursor.fetchall()

        logs = []
        for r in rows:
            d = dict(r)
            try:
                d["tools_used"] = json.loads(d["tools_used"])
            except Exception:
                d["tools_used"] = []
            d["total_latency_ms"] = round(d["total_latency"] * 1000, 1)
            d["from_cache"] = bool(d["from_cache"])
            logs.append(d)
        return logs


# Global metrics singleton
platform_metrics = PlatformMetrics()
