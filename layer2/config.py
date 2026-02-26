"""
Configuration for ECHMP Layer 2
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Neo4j Configuration
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # Ollama Configuration
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:1b")
    
    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL", 
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # Consolidation Parameters
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    MIN_CLUSTER_SIZE = int(os.getenv("MIN_CLUSTER_SIZE", "2"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
