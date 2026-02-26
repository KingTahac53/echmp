from mem0 import Memory
from neo4j import GraphDatabase

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "echmp_generalized_eval",
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

memory = Memory.from_config(config)
memory.delete_all(user_id="echmp_generalized")

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    results = session.run("""
        MATCH (g:GeneralizationNode)
        RETURN g.summary_text AS summary
    """)

    summaries = list(results)

print("Generalizations created:", len(summaries))

for item in summaries:
    memory.add(item["summary"], user_id="echmp_generalized")

all_memories = list(memory.get_all(user_id="echmp_generalized"))
print("Mem0 entries after generalization export:", len(all_memories))