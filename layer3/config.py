"""
Layer 3 Configuration
=====================
All tunable parameters for the strategic pruning engine.
Values align with the ECHMP project specification (Team 4).
"""

# ---------------------------------------------------------------------------
# Neo4j connection
# ---------------------------------------------------------------------------
NEO4J_URI      = "bolt://localhost:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "password"

# ---------------------------------------------------------------------------
# Scoring weights  (must sum to 1.0)
# ---------------------------------------------------------------------------
W_CENTRALITY   = 0.40   # PageRank importance in knowledge graph
W_EVENT_ANCHOR = 0.30   # Alignment with LoCoMo life events
W_RECENCY      = 0.20   # Exponential decay from timestamp
W_FREQUENCY    = 0.10   # Retrieval frequency normalised

# ---------------------------------------------------------------------------
# Pruning thresholds
# ---------------------------------------------------------------------------
RETAIN_THRESHOLD  = 0.60   # Definitely retain
ARCHIVE_THRESHOLD = 0.30   # Below this → archive
# 0.30 <= score < 0.60 → boundary zone → RETAIN (conservative)

# ---------------------------------------------------------------------------
# Recency decay
# ---------------------------------------------------------------------------
RECENCY_HALF_LIFE_DAYS = 30.0   # Facts lose half their recency score every 30 days

# ---------------------------------------------------------------------------
# PageRank
# ---------------------------------------------------------------------------
PAGERANK_ITERATIONS = 20
PAGERANK_DAMPING    = 0.85
