"""
Layer 3 Scoring Utilities
=========================
Standalone, unit-testable scoring functions used by Layer3Pruner.
"""

import math
from datetime import datetime, timezone
from typing import Optional

from layer3.config import RECENCY_HALF_LIFE_DAYS

# Life-event keyword list (mirrors layer3_pruner.py for standalone use)
LIFE_EVENT_KEYWORDS = [
    "job", "work", "hired", "fired", "promoted", "promotion",
    "resigned", "retire", "career", "salary", "unemployed",
    "moved", "move", "relocated", "relocation", "living",
    "location", "city", "country", "address",
    "graduated", "graduation", "university", "college", "school",
    "degree", "diploma", "phd", "masters", "enrolled",
    "married", "marriage", "divorce", "engaged", "engagement",
    "partner", "spouse", "wedding",
    "born", "birth", "baby", "child", "parent",
    "mother", "father", "sibling", "family",
    "diagnosed", "surgery", "hospital", "illness", "recovered",
    "bought", "purchased", "sold", "investment", "loan",
    "mortgage", "business", "startup",
    "anniversary", "birthday", "holiday", "vacation",
]


def score_event_anchor(text: str) -> float:
    """
    Returns 1.0 if any life-event keyword is in the text, else 0.2.
    """
    lower = (text or "").lower()
    for kw in LIFE_EVENT_KEYWORDS:
        if kw in lower:
            return 1.0
    return 0.2


def score_recency(
    timestamp_str: Optional[str],
    half_life_days: float = RECENCY_HALF_LIFE_DAYS,
) -> float:
    """
    Exponential decay:
        score = exp( -days_old * ln2 / half_life_days )

    A node exactly `half_life_days` old scores 0.5.
    A node with no timestamp scores 0.0.
    """
    if not timestamp_str:
        return 0.0
    try:
        ts = timestamp_str.replace("Z", "+00:00")
        if "T" in ts:
            node_dt = datetime.fromisoformat(ts)
        else:
            node_dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        if node_dt.tzinfo is None:
            node_dt = node_dt.replace(tzinfo=timezone.utc)
        days_old = max((datetime.now(timezone.utc) - node_dt).days, 0)
        return float(math.exp(-days_old * math.log(2) / half_life_days))
    except Exception:
        return 0.0


def score_frequency(access_count: int, max_access: int) -> float:
    """
    Normalised retrieval frequency, capped at 1.0.
    """
    if max_access == 0:
        return 0.0
    return min(access_count / max_access, 1.0)


def prune_score(
    centrality: float,
    event_anchor: float,
    recency: float,
    frequency: float,
    w_centrality: float = 0.40,
    w_event_anchor: float = 0.30,
    w_recency: float = 0.20,
    w_frequency: float = 0.10,
) -> float:
    """
    PruneScore = 0.40*C + 0.30*E + 0.20*R + 0.10*F
    """
    return (
        w_centrality * centrality
        + w_event_anchor * event_anchor
        + w_recency * recency
        + w_frequency * frequency
    )


def decide(score: float, retain_threshold: float = 0.60, archive_threshold: float = 0.30) -> str:
    """
    Returns 'RETAIN' or 'ARCHIVE' based on thresholds.
    Boundary zone (0.30 <= score < 0.60) → RETAIN (conservative).
    """
    return "ARCHIVE" if score < archive_threshold else "RETAIN"
