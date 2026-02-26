from mem0 import Memory
from neo4j import GraphDatabase
from layer1.schemas import fact_to_sentence

# Mem0 config
config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "echmp_fact_eval",
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
memory.delete_all(user_id="echmp_fact")

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    results = session.run("""
        MATCH (s:Entity)-[:HAS_FACT]->(f:Fact {status:"ACTIVE"})-[:TARGET]->(o:Entity)
        RETURN s.name AS subject,
               f.relation AS relation,
               o.name AS object
    """)

    facts = list(results)

print("ACTIVE facts from Layer1:", len(facts))

for fact in facts:
    sentence = fact_to_sentence(fact["subject"], fact["relation"], fact["object"])
    memory.add(sentence, user_id="echmp_fact")

all_memories = list(memory.get_all(user_id="echmp_fact"))
print("Mem0 entries after ECHMP fact export:", len(all_memories))