"""
Unit tests for Layer 3: Strategic Pruning
Run with:  python -m pytest layer3/test_layer3.py -v
"""

import math
import pytest
from unittest.mock import MagicMock, patch

from layer3.scoring import (
    score_event_anchor,
    score_recency,
    score_frequency,
    prune_score,
    decide,
)


# ──────────────────────────────────────────────────────────────
# score_event_anchor
# ──────────────────────────────────────────────────────────────

class TestEventAnchorScoring:

    def test_job_promotion_returns_1(self):
        assert score_event_anchor("User got promoted to principal") == 1.0

    def test_relocation_returns_1(self):
        assert score_event_anchor("User relocated to Portland") == 1.0

    def test_mundane_returns_0_2(self):
        assert score_event_anchor("User ate pizza on January 15") == 0.2

    def test_empty_string_returns_0_2(self):
        assert score_event_anchor("") == 0.2

    def test_none_returns_0_2(self):
        assert score_event_anchor(None) == 0.2

    def test_case_insensitive(self):
        assert score_event_anchor("USER MARRIED IN 2023") == 1.0

    def test_partial_match(self):
        # "birthday" is a keyword
        assert score_event_anchor("celebrated birthday party") == 1.0


# ──────────────────────────────────────────────────────────────
# score_recency
# ──────────────────────────────────────────────────────────────

class TestRecencyScoring:

    def test_today_scores_1(self):
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).isoformat()
        score = score_recency(today)
        assert abs(score - 1.0) < 0.01

    def test_half_life_scores_half(self):
        from datetime import datetime, timezone, timedelta
        ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        score = score_recency(ts, half_life_days=30)
        assert abs(score - 0.5) < 0.05

    def test_very_old_scores_near_zero(self):
        score = score_recency("2020-01-01", half_life_days=30)
        assert score < 0.01

    def test_none_returns_zero(self):
        assert score_recency(None) == 0.0

    def test_invalid_string_returns_zero(self):
        assert score_recency("not-a-date") == 0.0


# ──────────────────────────────────────────────────────────────
# score_frequency
# ──────────────────────────────────────────────────────────────

class TestFrequencyScoring:

    def test_max_access_returns_1(self):
        assert score_frequency(10, 10) == 1.0

    def test_zero_access_returns_0(self):
        assert score_frequency(0, 10) == 0.0

    def test_zero_max_returns_0(self):
        assert score_frequency(5, 0) == 0.0

    def test_half_access(self):
        assert score_frequency(5, 10) == 0.5

    def test_over_max_capped_at_1(self):
        assert score_frequency(15, 10) == 1.0


# ──────────────────────────────────────────────────────────────
# prune_score
# ──────────────────────────────────────────────────────────────

class TestPruneScore:

    def test_spec_example_principal_node(self):
        # From project proposal: Node A — Principal, score ≈ 0.90
        score = prune_score(
            centrality=0.85,
            event_anchor=1.0,
            recency=0.90,
            frequency=0.80,
        )
        expected = 0.40*0.85 + 0.30*1.0 + 0.20*0.90 + 0.10*0.80
        assert abs(score - expected) < 1e-6
        assert score > 0.60  # Should RETAIN

    def test_spec_example_pizza_node(self):
        # From project proposal: Node B — pizza, score ≈ 0.10
        score = prune_score(
            centrality=0.05,
            event_anchor=0.2,
            recency=0.001,
            frequency=0.0,
        )
        expected = 0.40*0.05 + 0.30*0.2 + 0.20*0.001 + 0.10*0.0
        assert abs(score - expected) < 1e-4
        assert score < 0.30  # Should ARCHIVE

    def test_spec_example_portland_node(self):
        # From project proposal: Node C — Portland, score ≈ 0.84
        score = prune_score(
            centrality=0.75,
            event_anchor=1.0,
            recency=0.85,
            frequency=0.70,
        )
        expected = 0.40*0.75 + 0.30*1.0 + 0.20*0.85 + 0.10*0.70
        assert abs(score - expected) < 1e-6
        assert score > 0.60  # Should RETAIN

    def test_all_zeros_returns_zero(self):
        assert prune_score(0, 0, 0, 0) == 0.0

    def test_all_ones_returns_one(self):
        assert abs(prune_score(1, 1, 1, 1) - 1.0) < 1e-6


# ──────────────────────────────────────────────────────────────
# decide
# ──────────────────────────────────────────────────────────────

class TestDecide:

    def test_high_score_retains(self):
        assert decide(0.90) == "RETAIN"

    def test_boundary_score_retains(self):
        assert decide(0.45) == "RETAIN"

    def test_low_score_archives(self):
        assert decide(0.10) == "ARCHIVE"

    def test_exactly_at_archive_threshold_retains(self):
        # score == 0.30 is boundary zone → RETAIN
        assert decide(0.30) == "RETAIN"

    def test_just_below_archive_threshold(self):
        assert decide(0.29) == "ARCHIVE"
