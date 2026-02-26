# layer1/engine.py

import requests
import re
import json
import uuid
from datetime import datetime
from neo4j import GraphDatabase
from neo4j.time import DateTime as Neo4jDateTime


VALID_RELATIONS = {
    "Occupation",
    "Location",
    "RelationshipStatus",
    "FamilyStatus",
    "LifeEvent",
    "Duration",
    "Identity",
    "Activity",
    "Education",
    "LifeGoal",
    "Other"
}


class Layer1Engine:
    def __init__(
        self,
        ollama_url: str,
        ollama_model: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        use_llm: bool = False,
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )
        self.use_llm = use_llm

    # ============================================================
    # EXTRACTION LAYER
    # ============================================================

    def extract_triplets(self, utterance):
        deterministic = self._extract_deterministic(utterance)

        if not self.use_llm:
            return deterministic

        llm = self._extract_with_llm(utterance)

        combined = deterministic.copy()
        for item in llm:
            if item not in combined:
                combined.append(item)

        return combined

    def _extract_deterministic(self, utterance):
        utterance_lower = utterance.lower()
        triplets = []

        # ---------------- LOCATION ----------------
        move_match = re.search(r"moved (?:from|to) ([a-zA-Z\s]+)", utterance_lower)
        if move_match:
            triplets.append({
                "subject": "User",
                "relation": "Location",
                "object": move_match.group(1).strip().title(),
                "timestamp": ""
            })

        live_match = re.search(r"live(?:s|d)? in ([a-zA-Z\s]+)", utterance_lower)
        if live_match:
            triplets.append({
                "subject": "User",
                "relation": "Location",
                "object": live_match.group(1).strip().title(),
                "timestamp": ""
            })

        # ---------------- OCCUPATION ----------------
        job_match = re.search(r"work(?:ing)? (?:as|in) ([a-zA-Z\s]+)", utterance_lower)
        if job_match:
            triplets.append({
                "subject": "User",
                "relation": "Occupation",
                "object": job_match.group(1).strip().title(),
                "timestamp": ""
            })

        if "career" in utterance_lower:
            triplets.append({
                "subject": "User",
                "relation": "Occupation",
                "object": "Career Mentioned",
                "timestamp": ""
            })

        # ---------------- EDUCATION ----------------
        if any(word in utterance_lower for word in ["study", "school", "university", "college", "degree"]):
            triplets.append({
                "subject": "User",
                "relation": "Education",
                "object": "Education Mentioned",
                "timestamp": ""
            })

        # ---------------- RELATIONSHIP STATUS ----------------
        if "married" in utterance_lower:
            triplets.append({
                "subject": "User",
                "relation": "RelationshipStatus",
                "object": "Married",
                "timestamp": ""
            })

        if any(word in utterance_lower for word in ["divorce", "breakup", "single"]):
            triplets.append({
                "subject": "User",
                "relation": "RelationshipStatus",
                "object": "Single",
                "timestamp": ""
            })

        # ---------------- FAMILY STATUS ----------------
        if any(word in utterance_lower for word in ["children", "kids", "son", "daughter"]):
            triplets.append({
                "subject": "User",
                "relation": "FamilyStatus",
                "object": "Has Children",
                "timestamp": ""
            })

        # ---------------- IDENTITY ----------------
        if any(word in utterance_lower for word in ["transgender", "transitioning", "nonbinary"]):
            triplets.append({
                "subject": "User",
                "relation": "Identity",
                "object": "Gender Identity Mentioned",
                "timestamp": ""
            })

        # ---------------- LIFE EVENTS ----------------
        if any(word in utterance_lower for word in ["wedding", "graduated", "promotion", "adoption", "charity race"]):
            triplets.append({
                "subject": "User",
                "relation": "LifeEvent",
                "object": "Major Life Event",
                "timestamp": ""
            })

        if "talk" in utterance_lower and "school" in utterance_lower:
            triplets.append({
                "subject": "User",
                "relation": "LifeEvent",
                "object": "Public Speaking",
                "timestamp": ""
            })

        # ---------------- DURATION ----------------
        years_match = re.search(r"(\d+)\s+years?", utterance_lower)
        if years_match:
            triplets.append({
                "subject": "User",
                "relation": "Duration",
                "object": years_match.group(1) + " years",
                "timestamp": ""
            })

        # ---------------- ACTIVITIES ----------------
        activity_keywords = [
            "painting", "swimming", "camping", "running",
            "reading", "travel", "hiking", "cooking",
            "cycling", "gaming", "writing"
        ]

        for word in activity_keywords:
            if word in utterance_lower:
                triplets.append({
                    "subject": "User",
                    "relation": "Activity",
                    "object": word.title(),
                    "timestamp": ""
                })

        # ---------------- GOALS ----------------
        if any(phrase in utterance_lower for phrase in ["want to", "planning to", "thinking about", "hope to"]):
            triplets.append({
                "subject": "User",
                "relation": "LifeGoal",
                "object": "Future Plan Mentioned",
                "timestamp": ""
            })

        return triplets

    def _extract_with_llm(self, utterance) -> list[dict]:

        prompt = f"""
    Extract factual triplets as JSON array.

    Each item must contain:
    - subject = "User"
    - relation ∈ {list(VALID_RELATIONS)}
    - object = string
    - timestamp = YYYY-MM or ""

    Return ONLY a valid JSON array.
    No explanation text.

    TEXT:
    {utterance}
    """

        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": self.ollama_model,
                "messages": [
                    {"role": "system", "content": "You are a strict JSON extractor."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            },
            timeout=60
        )

        response.raise_for_status()

        raw = response.json()["message"]["content"]

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

            cleaned.append({
                "subject": "User",
                "relation": relation,
                "object": str(item.get("object", "")).strip(),
                "timestamp": str(item.get("timestamp", "")).strip(),
            })

        return cleaned
    # ============================================================
    # TIMESTAMP
    # ============================================================

    def parse_timestamp(self, ts):
        if not ts:
            now = datetime.utcnow()
            return datetime(now.year, now.month, 1)

        if isinstance(ts, datetime):
            return ts

        if isinstance(ts, Neo4jDateTime):
            return datetime(ts.year, ts.month, ts.day)

        if isinstance(ts, str):
            try:
                if len(ts) == 7:
                    ts = ts + "-01"
                return datetime.fromisoformat(ts)
            except:
                pass

        now = datetime.utcnow()
        return datetime(now.year, now.month, 1)

    # ============================================================
    # NEO4J OPERATIONS (NO id(f) USED)
    # ============================================================

    def _find_active_fact(self, tx, subject, relation):
        query = """
        MATCH (s:Entity {name:$subject})-[:HAS_FACT]->(f:Fact {relation:$relation, status:"ACTIVE"})
        RETURN f.fact_id AS fact_id,
               f.timestamp AS timestamp,
               f.version AS version
        LIMIT 1
        """
        result = tx.run(query, subject=subject, relation=relation).single()
        return dict(result) if result else None

    def _supersede_fact(self, tx, fact_id):
        query = """
        MATCH (f:Fact {fact_id:$fact_id})
        SET f.status = "SUPERSEDED"
        """
        tx.run(query, fact_id=fact_id)

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

            timestamp = triplet.get("timestamp", "")
            ts_new = self.parse_timestamp(timestamp)

            with self.driver.session() as session:

                existing = None

                if relation in [
                    "Occupation",
                    "Location",
                    "RelationshipStatus",
                    "LifeGoal",
                    "Identity"
                ]:
                    existing = session.execute_read(
                        self._find_active_fact,
                        "User",
                        relation,
                    )

                version = 1

                if existing:
                    ts_existing = self.parse_timestamp(existing["timestamp"])
                    version = existing["version"] + 1

                    if ts_new >= ts_existing:
                        session.execute_write(
                            self._supersede_fact,
                            existing["fact_id"]
                        )
                    else:
                        continue

                session.execute_write(
                    self._create_fact,
                    "User",
                    relation,
                    triplet["object"],
                    timestamp,
                    version,
                )

    def ingest_utterance_with_timestamp(self, utterance: str, session_timestamp: str):
        triplets = self.extract_triplets(utterance)

        for triplet in triplets:
            relation = triplet["relation"]

            if relation not in VALID_RELATIONS:
                continue

            # Use session timestamp (YYYY-MM-DD → YYYY-MM)
            timestamp = session_timestamp[:7] if session_timestamp else ""
            ts_new = self.parse_timestamp(timestamp)

            with self.driver.session() as session:

                existing = None

                if relation in [
                    "Occupation",
                    "Location",
                    "RelationshipStatus",
                    "LifeGoal",
                    "Identity"
                ]:
                    existing = session.execute_read(
                        self._find_active_fact,
                        "User",
                        relation,
                    )

                version = 1

                if existing:
                    ts_existing = self.parse_timestamp(existing["timestamp"])
                    version = existing["version"] + 1

                    if ts_new >= ts_existing:
                        session.execute_write(
                            self._supersede_fact,
                            existing["fact_id"]
                        )
                    else:
                        continue

                session.execute_write(
                    self._create_fact,
                    "User",
                    relation,
                    triplet["object"],
                    timestamp,
                    version,
                )
