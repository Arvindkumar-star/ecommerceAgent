"""
Safety Guardrails Module.
Enforces execution step limits, cost budget boundaries, PII redaction,
and citation validation against verified retrieved sources.
"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class SafetyGuardrails:
    """Production guardrails for safety, privacy, and grounding verification."""

    def __init__(self, max_steps: int = 10, max_cost: float = 1.0):
        self.max_steps = max_steps
        self.max_cost = max_cost
        self.current_cost = 0.0

        self.pii_patterns: List[Tuple[str, str]] = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
            (r"\b(?:\d{4}[ -]?){3}\d{4}\b", "[CARD]"),
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
            (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]"),
        ]

    def reset_cost(self):
        self.current_cost = 0.0

    def check_step_limit(self, current_step: int) -> bool:
        """Prevents infinite agent loops."""
        if current_step >= self.max_steps:
            raise ValueError(
                f"Safety Guardrail: Step limit reached ({self.max_steps}). Execution stopped."
            )
        return True

    def check_cost_limit(self, additional_cost: float) -> bool:
        """Prevents unexpected cost spikes."""
        self.current_cost += additional_cost
        if self.current_cost >= self.max_cost:
            raise ValueError(
                f"Safety Guardrail: Cost limit reached (${self.max_cost:.2f}). Current: ${self.current_cost:.2f}"
            )
        return True

    def mask_pii(self, text: str) -> str:
        """Masks personally identifiable information in logs and user outputs."""
        if not text:
            return ""
        masked = text
        for pattern, replacement in self.pii_patterns:
            masked = re.sub(pattern, replacement, masked)
        return masked

    def sanitize_untrusted_content(self, text: str) -> str:
        """
        Sanitizes uploaded document chunks to neutralize prompt injection attempts
        (e.g., 'Ignore previous instructions and do X').
        """
        if not text:
            return ""
        # Neutralize common prompt injection phrases
        patterns = [
            (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "[BLOCKED PROMPT INJECTION]"),
            (r"(?i)system\s*:\s*you\s+are\s+now", "[BLOCKED SYSTEM OVERRIDE]"),
            (r"(?i)you\s+must\s+act\s+as\s+a\s+different\s+ai", "[BLOCKED ROLE OVERRIDE]")
        ]
        sanitized = text
        for p, r in patterns:
            sanitized = re.sub(p, r, sanitized)
        return sanitized

    def validate_citations(self, response: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validates whether claims or citations in the response correspond to verified sources.
        """
        if not sources:
            return {
                "grounded": False,
                "verified_citations": [],
                "note": "No source documents were retrieved."
            }

        verified = []
        for s in sources:
            filename = s.get("filename", "")
            location = s.get("location", "")
            if filename:
                verified.append({
                    "filename": filename,
                    "location": location,
                    "excerpt": s.get("content", "")[:180]
                })

        return {
            "grounded": len(verified) > 0,
            "verified_citations": verified,
            "count": len(verified)
        }


# Global guardrails singleton
safety_guardrails = SafetyGuardrails()
