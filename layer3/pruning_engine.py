"""
ECHMP Layer 3
Strategic Memory Pruning
Uses Neo4j graph centrality + recency scoring
"""

import logging
from datetime import datetime
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Layer3Pruner:

    def __init__(
        self,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password"
    ):
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

    # ------------------------------------------------
    # Compute PageRank centrality
    # ------------------------------------------------

    def compute_centrality(self):

        logger.info("Computing graph centrality...")

        query = """
        MATCH (s:Entity)-[:HAS_FACT]->(f:Fact)-[:TARGET]->(o:Entity)
        RETURN f.fact_id AS fact_id,
            COUNT { (s)--() } + COUNT { (o)--() } AS centrality
        """

        centrality = {}

        with self.driver.session() as session:
            results = session.run(query)

            for r in results:
                centrality[r["fact_id"]] = r["centrality"]

        # normalize
        max_c = max(centrality.values()) if centrality else 1

        for k in centrality:
            centrality[k] = centrality[k] / max_c

        return centrality
    # ------------------------------------------------
    # Fetch ACTIVE facts
    # ------------------------------------------------

    def fetch_active_facts(self):

        query = """
        MATCH (s:Entity)-[:HAS_FACT]->(f:Fact {status:'ACTIVE'})-[:TARGET]->(o:Entity)
        RETURN
            f.fact_id AS fact_id,
            f.relation AS relation,
            f.timestamp AS timestamp,
            f.version AS version
        """

        facts = []

        with self.driver.session() as session:
            results = session.run(query)

            for r in results:
                facts.append(dict(r))

        return facts

    # ------------------------------------------------
    # Recency score
    # ------------------------------------------------

    def recency_score(self, timestamp):

        try:
            ts = datetime.fromisoformat(str(timestamp))
        except:
            return 0.5

        age = (datetime.utcnow() - ts).days

        if age < 30:
            return 1.0
        elif age < 180:
            return 0.7
        elif age < 365:
            return 0.4
        else:
            return 0.2

    # ------------------------------------------------
    # Relation importance
    # ------------------------------------------------

    def relation_score(self, relation):

        weights = {
            "Occupation": 1.0,
            "Location": 1.0,
            "FamilyStatus": 0.9,
            "RelationshipStatus": 0.9,
            "LifeEvent": 0.8,
            "Education": 0.7,
            "LifeGoal": 0.6,
            "Activity": 0.5,
        }

        return weights.get(relation, 0.4)

    # ------------------------------------------------
    # Archive fact
    # ------------------------------------------------

    def archive_fact(self, fact_id):

        query = """
        MATCH (f:Fact {fact_id:$fact_id})
        SET f.status='ARCHIVED'
        """

        with self.driver.session() as session:
            session.run(query, fact_id=fact_id)

    # ------------------------------------------------
    # Main pruning pipeline
    # ------------------------------------------------

    def run_pruning(self):

        logger.info("Running Layer 3 pruning")

        facts = self.fetch_active_facts()

        centrality_map = self.compute_centrality()

        archived = 0

        for fact in facts:

            centrality = centrality_map.get(fact["fact_id"], 0.1)
            recency = self.recency_score(fact["timestamp"])
            relation = self.relation_score(fact["relation"])

            score = (
                0.4 * centrality +
                0.35 * recency +
                0.25 * relation
            )

            if score < 0.60:
                self.archive_fact(fact["fact_id"])
                archived += 1

        logger.info(f"Archived {archived} facts")

        return {
            "total": len(facts),
            "archived": archived,
            "remaining": len(facts) - archived
        }
    
    def close(self):
        self.driver.close()

if __name__ == "__main__":

    pruner = Layer3Pruner()

    try:
        stats = pruner.run_pruning()
        print("\nLayer 3 Pruning Results")
        print("------------------------")
        print(stats)

    finally:
        pruner.close()
