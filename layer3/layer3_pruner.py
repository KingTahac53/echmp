"""
ECHMP Layer 3: Strategic Pruning with PageRank-Based Event Grounding

Scores every ACTIVE/GeneralizationNode across four dimensions:
  - Centrality   (PageRank on Neo4j graph)          weight=0.40
  - EventAnchor  (LoCoMo life-event alignment)       weight=0.30
  - Recency      (exponential decay, 30-day half)    weight=0.20
  - Frequency    (retrieval count normalised)        weight=0.10

Pruning thresholds (from project spec):
  score >= 0.60  →  RETAIN
  0.30 <= score < 0.60  →  RETAIN  (boundary zone)
  score < 0.30  →  ARCHIVE
"""

import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Life-event keywords (from LoCoMo Event Graph categories)
# ---------------------------------------------------------------------------
LIFE_EVENT_KEYWORDS: List[str] = [
    # Employment
    "job", "work", "hired", "fired", "promoted", "promotion",
    "resigned", "retire", "career", "salary", "unemployed",
    "employer", "employee", "position", "role", "occupation",
    # Relocation
    "moved", "move", "relocated", "relocation", "living",
    "location", "city", "country", "address", "apartment",
    # Education
    "graduated", "graduation", "university", "college", "school",
    "degree", "diploma", "phd", "masters", "enrolled",
    # Relationships
    "married", "marriage", "divorce", "engaged", "engagement",
    "partner", "spouse", "wedding", "relationship",
    # Family
    "born", "birth", "baby", "child", "parent", "mother",
    "father", "sibling", "family",
    # Health
    "diagnosed", "surgery", "hospital", "illness", "recovered",
    "treatment", "health",
    # Financial
    "bought", "purchased", "sold", "investment", "loan",
    "mortgage", "business", "startup",
    # Travel / Significant dates
    "anniversary", "birthday", "holiday", "vacation",
]


class Layer3Pruner:

    # -----------------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------------

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        # Scoring weights (must sum to 1.0)
        w_centrality: float = 0.40,
        w_event_anchor: float = 0.30,
        w_recency: float = 0.20,
        w_frequency: float = 0.10,
        # Pruning thresholds
        retain_threshold: float = 0.60,
        archive_threshold: float = 0.30,
        # Recency decay half-life in days
        recency_half_life_days: float = 30.0,
        # PageRank iterations for in-DB estimation
        pagerank_iterations: int = 20,
        pagerank_damping: float = 0.85,
    ):
        self.driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )

        assert abs(w_centrality + w_event_anchor + w_recency + w_frequency - 1.0) < 1e-6, \
            "Scoring weights must sum to 1.0"

        self.w_centrality = w_centrality
        self.w_event_anchor = w_event_anchor
        self.w_recency = w_recency
        self.w_frequency = w_frequency

        self.retain_threshold = retain_threshold
        self.archive_threshold = archive_threshold
        self.recency_half_life_days = recency_half_life_days
        self.pagerank_iterations = pagerank_iterations
        self.pagerank_damping = pagerank_damping

        logger.info(
            "Layer3Pruner initialised — weights: "
            f"centrality={w_centrality}, event={w_event_anchor}, "
            f"recency={w_recency}, frequency={w_frequency}"
        )

    # -----------------------------------------------------------------------
    # Step 1 – Fetch candidate nodes
    # -----------------------------------------------------------------------

    def _fetch_candidates(self) -> List[Dict]:
        """
        Fetch all ACTIVE Fact nodes and GeneralizationNodes.
        Returns list of dicts with: node_id, label, text, timestamp, access_count.
        """
        query = """
        // ACTIVE facts
        MATCH (s:Entity)-[:HAS_FACT]->(f:Fact {status:'ACTIVE'})-[:TARGET]->(o:Entity)
        RETURN
            f.fact_id                 AS node_id,
            'Fact'                    AS label,
            s.name + ' ' + f.relation + ' ' + o.name AS text,
            f.timestamp               AS timestamp,
            coalesce(f.access_count, 0)  AS access_count

        UNION ALL

        // GeneralizationNodes from Layer 2
        MATCH (g:GeneralizationNode)
        RETURN
            g.node_id                 AS node_id,
            'GeneralizationNode'      AS label,
            g.summary_text            AS text,
            toString(g.created_at)    AS timestamp,
            coalesce(g.access_count, 0)  AS access_count
        """

        candidates = []
        with self.driver.session() as session:
            for rec in session.run(query):
                candidates.append(dict(rec))

        logger.info(f"Fetched {len(candidates)} candidate nodes for pruning.")
        return candidates

    # -----------------------------------------------------------------------
    # Step 2 – PageRank-based centrality
    # -----------------------------------------------------------------------

    def _compute_pagerank(self) -> Dict[str, float]:
        """
        Compute a lightweight PageRank over the Neo4j fact graph using
        the Graph Data Science library if available, otherwise falling
        back to an in-Python power-iteration over the adjacency fetched
        from Neo4j.
        """
        # Try GDS first (fast, in-DB)
        try:
            return self._compute_pagerank_gds()
        except Exception as e:
            logger.warning(f"GDS PageRank failed ({e}), falling back to Python.")
            return self._compute_pagerank_python()

    def _compute_pagerank_gds(self) -> Dict[str, float]:
        """Use Neo4j GDS library for PageRank."""
        with self.driver.session() as session:
            # Project in-memory graph
            session.run("""
                CALL gds.graph.project(
                    'echmp_graph',
                    ['Fact', 'GeneralizationNode', 'Entity'],
                    {
                        HAS_FACT: {orientation: 'NATURAL'},
                        TARGET:   {orientation: 'NATURAL'},
                        CONSOLIDATES_TO: {orientation: 'NATURAL'}
                    }
                )
            """)

            results = session.run("""
                CALL gds.pageRank.stream('echmp_graph', {
                    maxIterations: $iters,
                    dampingFactor: $damp
                })
                YIELD nodeId, score
                RETURN gds.util.asNode(nodeId).fact_id AS fact_id,
                       gds.util.asNode(nodeId).node_id AS node_id,
                       score
            """, iters=self.pagerank_iterations, damp=self.pagerank_damping)

            raw = {}
            for rec in results:
                key = rec["fact_id"] or rec["node_id"]
                if key:
                    raw[key] = rec["score"]

            # Drop projected graph
            session.run("CALL gds.graph.drop('echmp_graph')")

        return self._normalise_scores(raw)

    def _compute_pagerank_python(self) -> Dict[str, float]:
        """
        Fallback: fetch adjacency list and run power-iteration PageRank
        purely in Python.
        """
        edge_query = """
        MATCH (a)-[r]->(b)
        WHERE (a:Fact OR a:GeneralizationNode) AND (b:Fact OR b:GeneralizationNode OR b:Entity)
        RETURN
            coalesce(a.fact_id, a.node_id) AS src,
            coalesce(b.fact_id, b.node_id) AS dst
        """

        node_query = """
        MATCH (n)
        WHERE n:Fact OR n:GeneralizationNode
        RETURN coalesce(n.fact_id, n.node_id) AS nid
        """

        nodes = set()
        edges: List[Tuple[str, str]] = []

        with self.driver.session() as session:
            for rec in session.run(node_query):
                nodes.add(rec["nid"])
            for rec in session.run(edge_query):
                if rec["src"] and rec["dst"]:
                    edges.append((rec["src"], rec["dst"]))

        if not nodes:
            return {}

        node_list = list(nodes)
        idx = {n: i for i, n in enumerate(node_list)}
        N = len(node_list)

        # Out-degree
        out_deg = [0] * N
        adj: List[List[int]] = [[] for _ in range(N)]
        for src, dst in edges:
            if src in idx and dst in idx:
                s, d = idx[src], idx[dst]
                adj[s].append(d)
                out_deg[s] += 1

        pr = [1.0 / N] * N
        d = self.pagerank_damping

        for _ in range(self.pagerank_iterations):
            new_pr = [(1 - d) / N] * N
            for s in range(N):
                if out_deg[s] > 0:
                    contrib = d * pr[s] / out_deg[s]
                    for t in adj[s]:
                        new_pr[t] += contrib
                else:
                    # Dangling node — spread evenly
                    for t in range(N):
                        new_pr[t] += d * pr[s] / N
            pr = new_pr

        raw = {node_list[i]: pr[i] for i in range(N)}
        return self._normalise_scores(raw)

    @staticmethod
    def _normalise_scores(scores: Dict[str, float]) -> Dict[str, float]:
        if not scores:
            return {}
        min_v = min(scores.values())
        max_v = max(scores.values())
        if max_v == min_v:
            return {k: 0.5 for k in scores}
        return {k: (v - min_v) / (max_v - min_v) for k, v in scores.items()}

    # -----------------------------------------------------------------------
    # Step 3 – Individual scoring functions
    # -----------------------------------------------------------------------

    def _score_event_anchor(self, text: str) -> float:
        """
        1.0 if text contains a LoCoMo life-event keyword, else 0.2.
        Mirrors the spec exactly.
        """
        if not text:
            return 0.2
        lower = text.lower()
        for kw in LIFE_EVENT_KEYWORDS:
            if kw in lower:
                return 1.0
        return 0.2

    def _score_recency(self, timestamp_str: Optional[str]) -> float:
        """
        Exponential decay: exp(-days_old / half_life * ln2)
        so that a node at exactly half_life days old scores 0.5.
        """
        if not timestamp_str:
            return 0.0

        try:
            # Handle multiple timestamp formats from Neo4j / ISO 8601
            ts_clean = timestamp_str.replace("Z", "+00:00")
            # Strip Neo4j datetime format if needed
            if "T" in ts_clean:
                node_dt = datetime.fromisoformat(ts_clean)
            else:
                # e.g. "2024-01-15"
                node_dt = datetime.fromisoformat(ts_clean).replace(
                    tzinfo=timezone.utc
                )

            if node_dt.tzinfo is None:
                node_dt = node_dt.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            days_old = max((now - node_dt).days, 0)
            decay = math.exp(-days_old * math.log(2) / self.recency_half_life_days)
            return float(decay)

        except Exception:
            return 0.0

    @staticmethod
    def _score_frequency(
        access_count: int, max_access: int
    ) -> float:
        """
        Normalised retrieval frequency, capped at 1.0.
        """
        if max_access == 0:
            return 0.0
        return min(access_count / max_access, 1.0)

    # -----------------------------------------------------------------------
    # Step 4 – Combined pruning score
    # -----------------------------------------------------------------------

    def _prune_score(
        self,
        centrality: float,
        event_anchor: float,
        recency: float,
        frequency: float,
    ) -> float:
        """
        PruneScore = 0.40*C + 0.30*E + 0.20*R + 0.10*F
        (weights per project specification)
        """
        return (
            self.w_centrality * centrality
            + self.w_event_anchor * event_anchor
            + self.w_recency * recency
            + self.w_frequency * frequency
        )

    def _decide(self, score: float) -> str:
        if score >= self.retain_threshold:
            return "RETAIN"
        if score >= self.archive_threshold:
            return "RETAIN"   # boundary zone — keep
        return "ARCHIVE"

    # -----------------------------------------------------------------------
    # Step 5 – Apply decisions to Neo4j
    # -----------------------------------------------------------------------

    def _archive_nodes(
        self, decisions: List[Dict]
    ) -> Tuple[int, int]:
        """
        For ARCHIVE decisions:
          - Fact nodes       → status = 'ARCHIVED'
          - GeneralizationNodes → status = 'ARCHIVED'
        Returns (retained_count, archived_count).
        """
        retained = 0
        archived = 0

        with self.driver.session() as session:
            for node in decisions:
                if node["decision"] == "RETAIN":
                    # Persist the prune_score for observability
                    if node["label"] == "Fact":
                        session.run(
                            """
                            MATCH (f:Fact {fact_id: $nid})
                            SET f.prune_score = $score
                            """,
                            nid=node["node_id"],
                            score=round(node["prune_score"], 4),
                        )
                    else:
                        session.run(
                            """
                            MATCH (g:GeneralizationNode {node_id: $nid})
                            SET g.prune_score = $score
                            """,
                            nid=node["node_id"],
                            score=round(node["prune_score"], 4),
                        )
                    retained += 1

                else:  # ARCHIVE
                    if node["label"] == "Fact":
                        session.run(
                            """
                            MATCH (f:Fact {fact_id: $nid})
                            SET f.status = 'ARCHIVED',
                                f.archived_at = datetime(),
                                f.prune_score = $score
                            """,
                            nid=node["node_id"],
                            score=round(node["prune_score"], 4),
                        )
                    else:
                        session.run(
                            """
                            MATCH (g:GeneralizationNode {node_id: $nid})
                            SET g.status = 'ARCHIVED',
                                g.archived_at = datetime(),
                                g.prune_score = $score
                            """,
                            nid=node["node_id"],
                            score=round(node["prune_score"], 4),
                        )
                    archived += 1

        return retained, archived

    # -----------------------------------------------------------------------
    # Main pipeline
    # -----------------------------------------------------------------------

    def run_pruning(self) -> Dict:
        """
        Full Layer 3 pipeline:
          1. Fetch candidates
          2. Compute PageRank centrality
          3. Score each node
          4. Apply RETAIN / ARCHIVE decisions
          5. Return statistics
        """
        logger.info("=" * 60)
        logger.info("Layer 3 Strategic Pruning — started")
        logger.info("=" * 60)

        # ── 1. Fetch ────────────────────────────────────────────────
        candidates = self._fetch_candidates()
        if not candidates:
            logger.warning("No candidate nodes found. Skipping pruning.")
            return {"status": "skipped", "reason": "no_candidates"}

        # ── 2. PageRank ─────────────────────────────────────────────
        logger.info("Computing PageRank centrality...")
        pagerank_scores = self._compute_pagerank()

        # ── 3. Frequency normalisation ──────────────────────────────
        max_access = max(
            (c["access_count"] for c in candidates), default=0
        )

        # ── 4. Score each node ──────────────────────────────────────
        decisions: List[Dict] = []

        for node in candidates:
            nid = node["node_id"]
            text = node.get("text") or ""
            ts = node.get("timestamp")
            access = int(node.get("access_count") or 0)

            centrality = pagerank_scores.get(nid, 0.0)
            event_anchor = self._score_event_anchor(text)
            recency = self._score_recency(ts)
            frequency = self._score_frequency(access, max_access)

            prune_score = self._prune_score(
                centrality, event_anchor, recency, frequency
            )
            decision = self._decide(prune_score)

            decisions.append({
                "node_id": nid,
                "label": node["label"],
                "text": text[:80],
                "centrality": round(centrality, 4),
                "event_anchor": event_anchor,
                "recency": round(recency, 4),
                "frequency": round(frequency, 4),
                "prune_score": round(prune_score, 4),
                "decision": decision,
            })

            logger.debug(
                f"{decision:7s}  score={prune_score:.3f}  "
                f"[C={centrality:.2f} E={event_anchor:.1f} "
                f"R={recency:.2f} F={frequency:.2f}]  "
                f"{text[:60]}"
            )

        # ── 5. Apply decisions ──────────────────────────────────────
        retained, archived = self._archive_nodes(decisions)

        compression = (
            round(archived / len(candidates) * 100, 1)
            if candidates else 0
        )

        stats = {
            "total_candidates": len(candidates),
            "retained": retained,
            "archived": archived,
            "compression_pct": compression,
        }

        logger.info(
            f"Layer 3 complete — "
            f"total={len(candidates)}, "
            f"retained={retained}, "
            f"archived={archived}, "
            f"compression={compression}%"
        )
        logger.info("=" * 60)
        return stats

    def close(self):
        self.driver.close()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    pruner = Layer3Pruner(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
    )
    try:
        stats = pruner.run_pruning()
        print("\n── Layer 3 Pruning Results ──")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    finally:
        pruner.close()
