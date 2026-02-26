#!/usr/bin/env python3
"""
Debug and validation script for Layer 2
Checks all prerequisites and runs diagnostics
"""

import sys
import subprocess
import requests
from neo4j import GraphDatabase

def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor} (requires 3.11+)")
        return False

def check_dependencies():
    """Check if required packages are installed."""
    print("\n📦 Checking dependencies...")
    packages = [
        "sentence_transformers",
        "torch",
        "sklearn",
        "neo4j",
        "requests",
        "numpy"
    ]
    
    all_installed = True
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"   ✅ {pkg}")
        except ImportError:
            print(f"   ❌ {pkg} (not installed)")
            all_installed = False
    
    return all_installed

def check_neo4j():
    """Check Neo4j connection."""
    print("\n🗄️  Checking Neo4j...")
    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")  # Default credentials
        )
        driver.verify_connectivity()
        
        # Count facts
        with driver.session() as session:
            result = session.run("MATCH (f:Fact) RETURN count(f) AS count")
            count = result.single()["count"]
            print(f"   ✅ Neo4j connected")
            print(f"   📊 Found {count} facts in database")
        
        driver.close()
        return True
    except Exception as e:
        print(f"   ❌ Neo4j connection failed: {e}")
        return False

def check_ollama():
    """Check Ollama API."""
    print("\n🤖 Checking Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        if response.status_code == 200:
            version = response.json().get("version", "unknown")
            print(f"   ✅ Ollama running (version: {version})")
            
            # Check if model is available
            response = requests.get("http://localhost:11434/api/tags")
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            
            if "llama3.1:1b" in model_names:
                print(f"   ✅ llama3.1:1b model available")
            else:
                print(f"   ⚠️  llama3.1:1b not found. Available: {model_names}")
            
            return True
    except Exception as e:
        print(f"   ❌ Ollama connection failed: {e}")
        return False

def check_embedding_model():
    """Check embedding model download."""
    print("\n🧠 Checking embedding model...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Test encoding
        test_embedding = model.encode(["Test sentence"])
        print(f"   ✅ Embedding model loaded")
        print(f"   📏 Embedding dimension: {test_embedding.shape[1]}")
        return True
    except Exception as e:
        print(f"   ❌ Embedding model failed: {e}")
        return False

def run_diagnostics():
    """Run all diagnostic checks."""
    print("="*60)
    print("ECHMP Layer 2 Diagnostic Tool")
    print("="*60)
    
    results = {
        "Python": check_python_version(),
        "Dependencies": check_dependencies(),
        "Neo4j": check_neo4j(),
        "Ollama": check_ollama(),
        "Embeddings": check_embedding_model()
    }
    
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All checks passed! Layer 2 is ready to run.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix issues before running Layer 2.")
        print("\nQuick Fixes:")
        if not results["Dependencies"]:
            print("  → pip install -r requirements.txt")
        if not results["Neo4j"]:
            print("  → docker start neo4j")
        if not results["Ollama"]:
            print("  → ollama serve")
            print("  → ollama pull llama3.1:1b")
        return 1

if __name__ == "__main__":
    sys.exit(run_diagnostics())
