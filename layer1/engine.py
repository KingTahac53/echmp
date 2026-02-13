# layer1/engine.py

import requests
import re
import json
import uuid
from datetime import datetime
from neo4j import GraphDatabase
from neo4j.time import DateTime as Neo4jDateTime


VALID_RELATIONS = {"WorksAs", "Location", "Other"}


class Layer1Engine:
    def __init__(
        self,
        ollama_url: str,
        ollama_model: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        use_llm: bool = False,  # 🔥 SWITCH
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.use_llm = use_llm

    # ============================================================
    # EXTRACTION LAYER
    # ============================================================

    def extract_triplets(self, utterance) -> list[dict]:
        if self.use_llm:
            return self._extract_with_llm(utterance)
        else:
            return self._extract_deterministic(utterance)

    # ---------------- DETERMINISTIC (STABLE) ----------------
    print("DETERMINISTIC EXTRACTION ACTIVE")

    def _extract_deterministic(self, utterance) -> list[dict]:
        utterance_lower = utterance.lower()
        triplets = []
        print("UTTERANCE:", utterance_lower)

        if "teacher" in utterance_lower:
            triplets.append(
                {
                    "subject": "User",
                    "relation": "WorksAs",
                    "object": "teacher",
                    "timestamp": "",
                }
            )

        if "principal" in utterance_lower:
            triplets.append(
                {
                    "subject": "User",
                    "relation": "WorksAs",
                    "object": "principal",
                    "timestamp": "",
                }
            )

        if "seattle" in utterance_lower:
            triplets.append(
                {
                    "subject": "User",
                    "relation": "Location",
                    "object": "Seattle",
                    "timestamp": "",
                }
            )

        if "portland" in utterance_lower:
            triplets.append(
                {
                    "subject": "User",
                    "relation": "Location",
                    "object": "Portland",
                    "timestamp": "",
                }
            )
        print("DETERMINISTIC TRIPLETS:", triplets)
        return triplets

    # ---------------- OPTIONAL LLM MODE ----------------

    def _extract_with_llm(self, utterance) -> list[dict]:
        prompt = f"""
Extract factual triplets as JSON array.
Each item must contain:
subject = "User"
relation = WorksAs | Location | Other
object = string
timestamp = YYYY-MM or ""

Return ONLY JSON array.
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

        match = re.search(r"\[[\s\S]*\]", raw)
        if not match:
            return []

        try:
            data = json.loads(match.group())
        except:
            return []

        cleaned = []
        for item in data:
            relation = item.get("relation", "Other")
            if relation not in VALID_RELATIONS:
                relation = "Other"

            cleaned.append(
                {
                    "subject": "User",
                    "relation": relation,
                    "object": str(item.get("object", "")).strip(),
                    "timestamp": str(item.get("timestamp", "")).strip(),
                }
            )

        return cleaned

    # ============================================================
    # TIMESTAMP
    # ============================================================

    def extract_month_from_text(self, utterance: str) -> str:
        match = re.search(r"Month\s*(\d+)", utterance, re.IGNORECASE)
        if match:
            month = int(match.group(1))
            return f"2023-{month:02d}"
        return ""

    def parse_timestamp(self, ts) -> datetime:
        if not ts:
            now = datetime.utcnow()
            return datetime(now.year, now.month, 1)

        # If already Python datetime
        if isinstance(ts, datetime):
            return ts

        # If Neo4j datetime object
        if isinstance(ts, Neo4jDateTime):
            return datetime(ts.year, ts.month, ts.day)

        # If string YYYY-MM
        if isinstance(ts, str):
            try:
                if len(ts) == 7:
                    ts = ts + "-01"
                return datetime.fromisoformat(ts)
            except:
                pass

        # Fallback
        now = datetime.utcnow()
        return datetime(now.year, now.month, 1)

    # ============================================================
    # NEO4J OPERATIONS
    # ============================================================

    def _find_active_fact(self, tx, subject, relation):
        query = """
        MATCH (s:Entity {name:$subject})-[:HAS_FACT]->(f:Fact {relation:$relation, status:"ACTIVE"})
        RETURN f
        LIMIT 1
        """
        result = tx.run(query, subject=subject, relation=relation).single()
        return result["f"] if result else None

    def _supersede_fact(self, tx, fact_id):
        tx.run(
            """
            MATCH (f:Fact)
            WHERE id(f) = $id
            SET f.status = "SUPERSEDED"
            """,
            id=fact_id,
        )

    def _create_fact(self, tx, subject, relation, obj, timestamp, version):
        fact_id = str(uuid.uuid4())

        query = """
        MERGE (s:Entity {name:$subject})
        MERGE (o:Entity {name:$object})

        CREATE (f:Fact {
            fact_id: $fact_id,
            relation: $relation,
            timestamp: $timestamp,
            status: "ACTIVE",
            version: $version,
            confidence: 0.95,
            created_at: datetime()
        })

        MERGE (s)-[:HAS_FACT]->(f)
        MERGE (f)-[:TARGET]->(o)
        """

        tx.run(
            query,
            subject=subject,
            object=obj,
            relation=relation,
            timestamp=timestamp,
            fact_id=fact_id,
            version=version,
        )

    # ============================================================
    # PUBLIC INGEST
    # ============================================================

    def ingest_utterance(self, utterance: str):
        triplets = self.extract_triplets(utterance)

        for triplet in triplets:
            relation = triplet["relation"]
            if relation not in VALID_RELATIONS:
                continue

            # Timestamp override for demo
            manual_ts = self.extract_month_from_text(utterance)
            print("MANUAL_TS:", manual_ts)
            timestamp = manual_ts if manual_ts else triplet.get("timestamp", "")

            ts_new = self.parse_timestamp(timestamp)

            with self.driver.session() as session:
                existing = session.execute_read(
                    self._find_active_fact,
                    "User",
                    relation,
                )

                version = 1

                if existing:
                    ts_existing = self.parse_timestamp(existing["timestamp"])
                    version = existing["version"] + 1
                    print("DEBUG ts_existing:", ts_existing)
                    print("DEBUG ts_new:", ts_new)
                    print("COMPARE:", ts_new > ts_existing)

                    if ts_new > ts_existing:
                        session.execute_write(self._supersede_fact, existing.id)
                    else:
                        continue
                print("Processing:", relation, "timestamp:", timestamp)
                session.execute_write(
                    self._create_fact,
                    "User",
                    relation,
                    triplet["object"],
                    timestamp,
                    version,
                )
