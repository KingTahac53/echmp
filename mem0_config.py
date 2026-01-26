# mem0_config.py
import os

BASE_OLLAMA = "http://localhost:11434"  # default Ollama URL

MEM0_CONFIG = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "mixtral:8x7b",  # pick a local model you've installed in Ollama
            "temperature": 0.0,
            "max_tokens": 1024,
            "ollama_base_url": BASE_OLLAMA,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {"model": "nomic-embed-text:latest", "ollama_base_url": BASE_OLLAMA},
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {"host": "localhost", "port": 6333, "collection_name": "mem0_test"},
    },
    # Graph memory is optional; for Layer1 we'll write to Neo4j directly
}
