import json
from layer1.engine import Layer1Engine

# ---------------- CONFIG ----------------

LOCOMO_PATH = "data/locomo/locomo10.json"

engine = Layer1Engine(
    ollama_url="http://localhost:11434",
    ollama_model="llama3.1:8b",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password",
    use_llm=False,  # deterministic for now
)

with engine.driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n;")

# ---------------- RESET DB ----------------

with engine.driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n;")

# ---------------- LOAD DATA ----------------

with open(LOCOMO_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

sample = data[0]  # only first conversation
conversation = sample["conversation"]

print("Ingesting sample_id:", sample["sample_id"])

# ---------------- INGEST FIRST 3 SESSIONS ----------------

sessions_to_process = 3
utterance_count = 0

# Automatically detect session keys
session_keys = [
    k
    for k in conversation.keys()
    if k.startswith("session_") and not k.endswith("_date_time")
]

session_keys = sorted(session_keys, key=lambda x: int(x.split("_")[1]))


utterance_count = 0

for session_key in session_keys[:5]:  # maybe first 5 sessions
    date_key = session_key + "_date_time"
    session_date = conversation.get(date_key, "")

    for turn in conversation[session_key]:
        text = turn["text"]
        engine.ingest_utterance_with_timestamp(text, session_date)
        utterance_count += 1


print("Utterances processed:", utterance_count)

# ---------------- METRICS ----------------

with engine.driver.session() as session:
    total_facts = session.run("MATCH (f:Fact) RETURN count(f) AS count").single()[
        "count"
    ]

    active = session.run(
        "MATCH (f:Fact {status:'ACTIVE'}) RETURN count(f) AS count"
    ).single()["count"]

    superseded = session.run(
        "MATCH (f:Fact {status:'SUPERSEDED'}) RETURN count(f) AS count"
    ).single()["count"]

print("\n--- Layer 1 Metrics ---")
print("Total facts:", total_facts)
print("Active facts:", active)
print("Superseded facts:", superseded)
print("Conflicts resolved:", superseded)
print("Session keys detected:", session_keys[:5])
