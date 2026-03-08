"""
Layer 3 Diagnostics
===================
Run this script to validate your environment before running the pruner.

    python layer3/debug_layer3.py
"""

import os
import sys


def check_python():
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 10
    status = "✅" if ok else "❌"
    print(f"{status} Python {v.major}.{v.minor}.{v.micro}  (need ≥ 3.10)")
    return ok


def check_neo4j():
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 1 AS ping")
            result.single()
        driver.close()
        print(f"✅ Neo4j connected at {uri}")
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return False


def check_layer2_data():
    """Verify that Layer 2 has run and data exists for Layer 3."""
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            active = session.run(
                "MATCH (f:Fact {status:'ACTIVE'}) RETURN count(f) AS n"
            ).single()["n"]
            gens = session.run(
                "MATCH (g:GeneralizationNode) RETURN count(g) AS n"
            ).single()["n"]
        driver.close()
        print(f"✅ ACTIVE facts: {active}  |  GeneralizationNodes: {gens}")
        if active == 0 and gens == 0:
            print("   ⚠️  No data found — run Layer 1 + Layer 2 first.")
        return True
    except Exception as e:
        print(f"❌ Data check failed: {e}")
        return False


def check_imports():
    modules = [
        ("neo4j",   "neo4j"),
        ("networkx", "networkx"),
        ("dotenv",  "python-dotenv"),
    ]
    all_ok = True
    for mod, pkg in modules:
        try:
            __import__(mod)
            print(f"✅ {pkg} installed")
        except ImportError:
            print(f"❌ {pkg} missing — pip install {pkg}")
            all_ok = False
    return all_ok


def check_gds():
    """Optional: check if Neo4j GDS is available."""
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("CALL gds.version() YIELD version RETURN version")
        driver.close()
        print("✅ Neo4j GDS plugin available (fast PageRank)")
        return True
    except Exception:
        print("ℹ️  Neo4j GDS not available — will use Python PageRank fallback")
        return False


if __name__ == "__main__":
    print("=" * 55)
    print("ECHMP Layer 3 — Environment Diagnostics")
    print("=" * 55)

    results = [
        check_python(),
        check_imports(),
        check_neo4j(),
        check_layer2_data(),
    ]
    check_gds()  # optional, not counted in pass/fail

    print("=" * 55)
    if all(results):
        print("✅ All checks passed. Ready to run Layer 3.")
        print("   python layer3/layer3_pruner.py")
    else:
        print("❌ Some checks failed. Fix issues above before running.")
    print("=" * 55)
