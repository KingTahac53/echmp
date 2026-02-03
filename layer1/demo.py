# layer1/demo.py
from layer1.engine import Layer1Engine

engine = Layer1Engine(
    ollama_url="http://localhost:11434",
    ollama_model="llama3.1:8b",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password",
)

engine.ingest_utterance("Month 1: I just started a new job as a teacher in Seattle.")

engine.ingest_utterance(
    "Month 6: Great news, I got promoted to principal and I'm moving to Portland."
)

print("Layer 1 ingestion complete.")
