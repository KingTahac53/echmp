# layer1_demo.py
import os
import requests
from neo4j import GraphDatabase
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "password"  # match earlier docker run

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


# ---------- Helper: call Ollama to extract triplet ----------
def extract_triplet_with_ollama(utterance):
    prompt = f"""
You are an information extraction system.

TASK:
Extract exactly ONE factual triplet from the text.

OUTPUT FORMAT RULES (MANDATORY):
- Output ONLY valid JSON
- Do NOT add explanations
- Do NOT add extra text
- Do NOT wrap in markdown

JSON SCHEMA:
{{
  "subject": "User",
  "relation": "WorksAs | Location | Other",
  "object": "string",
  "timestamp": "YYYY-MM"
}}

TEXT:
{utterance}
"""

    payload = {
        "model": "llama3.1:8b",  # confirmed installed
        "prompt": prompt,
        "stream": False,
        "temperature": 0,
    }

    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
    r.raise_for_status()
    data = r.json()

    raw = data.get("response", "")
    print("\n--- RAW OLLAMA OUTPUT ---")
    print(raw)
    print("--- END RAW OUTPUT ---\n")

    import json, re

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("Ollama did not return JSON.\n" "Raw output was:\n" + raw)

    return json.loads(match.group())


# ---------- Normalization ----------
def normalize_triplet(trip):
    # Canonical subject normalization
    subj_raw = trip.get("subject", "").strip().lower()
    if subj_raw in ["i", "me", "my", "myself"]:
        subj = "User"
    else:
        subj = trip.get("subject", "User").strip()

    rel = trip.get("relation", "").strip().lower()
    obj = trip.get("object", "").strip()

    # Canonical relation mapping
    rel_map = {
        "worksas": "WorksAs",
        "works as": "WorksAs",
        "is a": "WorksAs",
        "lives in": "Location",
        "moved to": "Location",
        "located in": "Location",
    }

    rel_norm = rel_map.get(rel, rel.replace(" ", "_").capitalize())

    # Timestamp (may be empty)
    ts = trip.get("timestamp", "").strip()

    return {
        "subject": subj,
        "relation": rel_norm,
        "object": obj,
        "timestamp": ts,
    }


# ---------- Neo4j helpers ----------
def parse_timestamp(ts):
    # If timestamp missing or empty → use current month
    if not ts:
        now = datetime.utcnow()
        return datetime(now.year, now.month, 1)

    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        try:
            return datetime.fromisoformat(ts + "-01")
        except ValueError:
            # Last-resort fallback
            now = datetime.utcnow()
            return datetime(now.year, now.month, 1)


def find_existing_fact(tx, subject, relation):
    q = """
    MATCH (f:Fact {subject:$subject, relation:$relation, status:"ACTIVE"})
    RETURN f LIMIT 1
    """
    res = tx.run(q, subject=subject, relation=relation).single()
    return res["f"] if res else None


def archive_fact(tx, node_id):
    q = """
    MATCH (f) WHERE id(f) = $nid
    SET f.status = 'ARCHIVED'
    RETURN id(f) as id
    """
    tx.run(q, nid=node_id)


def create_fact(tx, subject, relation, obj, timestamp):
    q = """
    CREATE (f:Fact {subject:$subject, relation:$relation, object:$object, timestamp:$timestamp, status:"ACTIVE"})
    RETURN id(f) as id
    """
    r = tx.run(
        q, subject=subject, relation=relation, object=obj, timestamp=timestamp
    ).single()
    return r["id"]


# ---------- Core logic ----------
def process_utterance_and_apply(utterance):
    print("Extracting triplet from utterance:", utterance)
    trip = extract_triplet_with_ollama(utterance)
    norm = normalize_triplet(trip)
    ts_new = parse_timestamp(norm["timestamp"])
    with driver.session() as session:
        existing = session.execute_read(
            find_existing_fact, norm["subject"], norm["relation"]
        )
        if existing:
            # compare timestamps (Neo4j stored timestamp as string)
            ts_existing = parse_timestamp(existing.get("timestamp"))
            existing_id = existing.id
            if ts_new > ts_existing:
                # supersede old
                print("New fact is newer -> superseding old fact id:", existing_id)
                session.execute_write(archive_fact, existing_id)
                new_id = session.execute_write(
                    create_fact,
                    norm["subject"],
                    norm["relation"],
                    norm["object"],
                    norm["timestamp"],
                )
                print("Inserted new fact id:", new_id)
            else:
                print("Existing fact is newer; rejecting incoming fact.")
        else:
            new_id = session.execute_write(
                create_fact,
                norm["subject"],
                norm["relation"],
                norm["object"],
                norm["timestamp"],
            )
            print("Inserted new fact id:", new_id)


if __name__ == "__main__":
    # Example usage: first utterance
    process_utterance_and_apply(
        "Month 1: I just started a new job as a teacher in Seattle."
    )
    # later utterance that should supersede:
    process_utterance_and_apply(
        "Month 6: Great news, I got promoted to principal and I'm moving to Portland."
    )
