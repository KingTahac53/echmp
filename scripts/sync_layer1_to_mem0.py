from mem0 import Memory
from layer1.engine import Layer1Engine
from layer1.schemas import fact_to_sentence

# ---------------- CONFIG ----------------

mem0_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "echmp_fact_memory_v2",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 384,
        },
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1:8b",
            "temperature": 0,
            "ollama_base_url": "http://localhost:11434",
        },
    },
}

engine = Layer1Engine(
    ollama_url="http://localhost:11434",
    ollama_model="llama3.1:8b",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password",
)

memory = Memory.from_config(mem0_config)

# ---------------- FETCH ACTIVE FACTS ----------------

with engine.driver.session() as session:
    results = session.run(
        """
        MATCH (s:Entity)-[:HAS_FACT]->(f:Fact {status:"ACTIVE"})-[:TARGET]->(o:Entity)
        RETURN s.name AS subject,
               f.relation AS relation,
               o.name AS object,
               f.timestamp AS timestamp
    """
    )

    facts = list(results)
    facts = facts[:20]

print(f"Active facts retrieved: {len(facts)}")

# ---------------- SYNC TO MEM0 ----------------
memory.delete_all(user_id="echmp_user_0")

for fact in facts:
    sentence = fact_to_sentence(fact["subject"], fact["relation"], fact["object"])

    memory.add(
        sentence,
        user_id="echmp_user_0",
        metadata={
            "relation": fact["relation"],
            "timestamp": str(fact["timestamp"]),
            "source": "layer1_fact",
        },
    )


print("Sync complete.")

# ---------------- VERIFY ----------------

all_memories = list(memory.get_all(user_id="echmp_user_0"))
print(f"Total Mem0 entries (ECHMP facts): {len(all_memories)}")
