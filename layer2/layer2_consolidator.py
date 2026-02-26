"""
ECHMP Layer 2: Schema-Aligned Memory Consolidation
Fully aligned with Layer 1 Neo4j schema.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
import requests
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Layer2Consolidator:

    def __init__(
        self,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        ollama_url="http://localhost:11434",
        similarity_threshold=0.85,
    ):
        self.driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )
        self.ollama_url = ollama_url
        self.similarity_threshold = similarity_threshold

        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        logger.info("Embedding model loaded.")

    # ============================================================
    # FETCH ACTIVE FACTS (SCHEMA ALIGNED)
    # ============================================================

    def _fetch_active_facts(self) -> Dict[str, List[Dict]]:
        """
        Fetch ACTIVE facts grouped by relation.
        """

        query = """
        MATCH (s:Entity)-[:HAS_FACT]->(f:Fact {status:'ACTIVE'})-[:TARGET]->(o:Entity)
        RETURN f.fact_id AS fact_id,
               s.name AS subject,
               f.relation AS relation,
               o.name AS object,
               f.timestamp AS timestamp
        """

        relation_groups = {}

        with self.driver.session() as session:
            results = session.run(query)

            for record in results:
                relation = record["relation"]

                fact_text = (
                    f"{record['subject']} {relation} {record['object']}"
                )

                fact = {
                    "fact_id": record["fact_id"],
                    "relation": relation,
                    "text": fact_text,
                }

                if relation not in relation_groups:
                    relation_groups[relation] = []

                relation_groups[relation].append(fact)

        return relation_groups

    # ============================================================
    # EMBEDDING + CLUSTERING PER RELATION
    # ============================================================

    def _cluster_relation(self, facts: List[Dict]) -> List[List[Dict]]:

        if len(facts) < 2:
            return []

        texts = [f["text"] for f in facts]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        similarity_matrix = cosine_similarity(embeddings)
        distance_matrix = 1 - similarity_matrix

        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - self.similarity_threshold,
            metric="precomputed",
            linkage="complete",
        )

        labels = clustering.fit_predict(distance_matrix)

        clusters = {}
        for idx, label in enumerate(labels):
            clusters.setdefault(label, []).append(facts[idx])

        return [c for c in clusters.values() if len(c) > 1]

    # ============================================================
    # LLM SUMMARIZATION
    # ============================================================

    def _summarize_cluster(self, cluster):

        lines = "\n".join([f"- {f['text']}" for f in cluster])

        prompt = f"""
    Summarize the following related facts into one concise general statement:

    {lines}
    """

        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": "llama3.1:8b",
                "messages": [
                    {"role": "system", "content": "You are a concise summarization assistant."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            },
            timeout=60
        )

        response.raise_for_status()

        result = response.json()
        return result["message"]["content"].strip()

    # ============================================================
    # GRAPH UPDATE
    # ============================================================

    def _create_generalization(self, summary: str, cluster: List[Dict]):

        gen_id = str(uuid.uuid4())

        with self.driver.session() as session:

            session.run(
                """
                CREATE (g:GeneralizationNode {
                    node_id:$node_id,
                    summary_text:$summary_text,
                    created_at:datetime()
                })
                """,
                node_id=gen_id,
                summary_text=summary,
            )

            for fact in cluster:
                session.run(
                    """
                    MATCH (f:Fact {fact_id:$fact_id})
                    MATCH (g:GeneralizationNode {node_id:$node_id})
                    SET f.status = 'CONSOLIDATED'
                    MERGE (f)-[:CONSOLIDATES_TO]->(g)
                    """,
                    fact_id=fact["fact_id"],
                    node_id=gen_id,
                )

    # ============================================================
    # MAIN PIPELINE
    # ============================================================

    def run_consolidation(self):

        logger.info("Starting Layer 2 consolidation...")

        relation_groups = self._fetch_active_facts()

        total_clusters = 0

        for relation, facts in relation_groups.items():

            logger.info(f"Processing relation: {relation} ({len(facts)} facts)")

            clusters = self._cluster_relation(facts)

            for cluster in clusters:
                summary = self._summarize_cluster(cluster)
                self._create_generalization(summary, cluster)
                total_clusters += 1

        logger.info(f"Layer 2 completed. Created {total_clusters} generalizations.")
        return {"generalizations_created": total_clusters}

    def close(self):
        self.driver.close()


if __name__ == "__main__":
    consolidator = Layer2Consolidator()
    try:
        stats = consolidator.run_consolidation()
        print(stats)
    finally:
        consolidator.close()
