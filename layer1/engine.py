# layer1/engine.py
import requests
import re
import json
from datetime import datetime
from neo4j import GraphDatabase


class Layer1Engine:
    def __init__(
        self,
        ollama_url: str,
        ollama_model: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    # ---------- LLM Extraction ----------
    def extract_triplets(self, utterance) -> list[dict]:
        prompt = f"""
    You are an information extraction system.

    TASK:
    Extract ALL factual triplets from the text.

    OUTPUT RULES:
    - Output ONLY valid JSON
    - No explanations, no markdown
    - Always return a JSON ARRAY
    - If only one fact exists, return an array with one element

    JSON FORMAT:
    [
    {{
        "subject": "User",
        "relation": "WorksAs | Location | Other",
        "object": "string",
        "timestamp": "YYYY-MM or empty"
    }}
    ]

    TEXT:
    {utterance}
    """

        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0,
        }

        r = requests.post(f"{self.ollama_url}/api/generate", json=payload)
        r.raise_for_status()

        raw = r.json().get("response", "")

        # Match JSON array
        match = re.search(r"\[[\s\S]*\]", raw)
        if not match:
            raise ValueError(f"LLM output not JSON array:\n{raw}")

        data = json.loads(match.group())

        if not isinstance(data, list):
            raise ValueError("Expected list of triplets")

        return data

    # ---------- Normalization ----------
    def normalize_triplet(self, triplet: dict) -> dict:
        obj_raw = triplet.get("object", "").strip().lower()

        ROLE_KEYWORDS = [
            "teacher",
            "principal",
            "engineer",
            "manager",
            "student",
            "developer",
            "professor",
            "doctor",
        ]

        if obj_raw in ROLE_KEYWORDS:
            relation = "WorksAs"
        else:
            relation_raw = triplet.get("relation", "").strip().lower()
            relation_map = {
                "works as": "WorksAs",
                "worksas": "WorksAs",
                "is a": "WorksAs",
                "job": "WorksAs",
                "role": "WorksAs",
                "lives in": "Location",
                "moved to": "Location",
                "located in": "Location",
                "location": "Location",
            }
            relation = relation_map.get(relation_raw, "Other")

        timestamp = triplet.get("timestamp", "").strip()

        return {
            "subject": "User",  # ✅ FIXED
            "relation": relation,
            "object": triplet.get("object", "").strip(),
            "timestamp": timestamp,
        }

    # ---------- Timestamp Handling ----------
    def parse_timestamp(self, ts: str) -> datetime:
        if not ts or ts.lower() == "none":
            now = datetime.utcnow()
            return datetime(now.year, now.month, 1)

        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            try:
                return datetime.fromisoformat(ts + "-01")
            except ValueError:
                now = datetime.utcnow()
                return datetime(now.year, now.month, 1)

    # ---------- Neo4j Ops ----------

    def _find_existing_fact(self, tx, subject, relation):
        query = f"""
        MATCH (s:Entity {{name:$subject}})-[r:{relation} {{status:"ACTIVE"}}]->()
        RETURN r LIMIT 1
        """
        res = tx.run(query, subject=subject).single()
        return res["r"] if res else None

    def _archive_fact(self, tx, rel_id):
        tx.run(
            "MATCH ()-[r]->() WHERE id(r)=$id SET r.status='ARCHIVED'",
            id=rel_id,
        )

    def _create_fact(self, tx, subject, relation, obj, timestamp):
        assert relation.isidentifier(), f"Invalid relationship type: {relation}"
        query = f"""
        MERGE (s:Entity {{name: $subject}})
        MERGE (o:Entity {{name: $object}})
        CREATE (s)-[r:{relation} {{
            timestamp: $timestamp,
            status: "ACTIVE"
        }}]->(o)
        RETURN id(r) AS id
        """
        res = tx.run(
            query,
            subject=subject,
            object=obj,
            timestamp=timestamp,
        ).single()
        return res["id"]

    # ---------- Public API ----------
    def ingest_utterance(self, utterance: str):
        triplets = self.extract_triplets(utterance)

        for triplet in triplets:
            norm = self.normalize_triplet(triplet)
            ts_new = self.parse_timestamp(norm["timestamp"])

            with self.driver.session() as session:
                existing = session.execute_read(
                    self._find_existing_fact,
                    norm["subject"],
                    norm["relation"],
                )

                if existing:
                    ts_existing = self.parse_timestamp(existing["timestamp"])
                    if ts_new > ts_existing:
                        session.execute_write(self._archive_fact, existing.id)
                    else:
                        continue  # reject older fact

                session.execute_write(
                    self._create_fact,
                    norm["subject"],
                    norm["relation"],
                    norm["object"],
                    norm["timestamp"],
                )
