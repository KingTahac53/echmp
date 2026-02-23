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
    use_llm=False,  # deterministic mode (stable & fast)
)

# ---------------- RESET DATABASE ----------------

print("Resetting Neo4j database...")
with engine.driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n;")

# ---------------- LOAD DATA ----------------

with open(LOCOMO_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Loaded {len(data)} conversations from LoCoMo\n")

total_utterances = 0
conversation_counter = 0

# ---------------- INGEST ALL CONVERSATIONS ----------------

for sample in data:
    conversation_counter += 1
    print(f"Ingesting sample {conversation_counter}: {sample['sample_id']}")

    conversation = sample["conversation"]

    # Automatically detect session keys
    session_keys = [
        k for k in conversation.keys()
        if k.startswith("session_") and not k.endswith("_date_time")
    ]

    session_keys = sorted(session_keys, key=lambda x: int(x.split("_")[1]))

    for session_key in session_keys:
        date_key = session_key + "_date_time"
        session_date = conversation.get(date_key, "")

        for turn in conversation[session_key]:
            text = turn["text"]
            engine.ingest_utterance_with_timestamp(text, session_date)
            total_utterances += 1

print("\n--- INGESTION COMPLETE ---")
print("Total utterances processed:", total_utterances)

# ---------------- METRICS ----------------

with engine.driver.session() as session:
    total_facts = session.run(
        "MATCH (f:Fact) RETURN count(f) AS count"
    ).single()["count"]

    active = session.run(
        "MATCH (f:Fact {status:'ACTIVE'}) RETURN count(f) AS count"
    ).single()["count"]

    superseded = session.run(
        "MATCH (f:Fact {status:'SUPERSEDED'}) RETURN count(f) AS count"
    ).single()["count"]

    relation_distribution = list(session.run(
        """
        MATCH (f:Fact)
        RETURN f.relation AS relation, count(*) AS count
        ORDER BY count DESC
        """
    ))


print("\n--- Layer 1 Metrics ---")
print("Total facts:", total_facts)
print("Active facts:", active)
print("Superseded facts:", superseded)
print("Conflicts resolved:", superseded)

print("\n--- Relation Distribution ---")
for record in relation_distribution:
    print(f"{record['relation']}: {record['count']}")
