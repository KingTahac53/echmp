# Layer 1 — Neo4j Validation Commands

This document demonstrates the correctness of the hierarchical fact memory layer.

Layer 1 implements:

- Fact extraction
- Temporal ordering
- Conflict resolution
- Versioning
- Historical traceability

---

## 1. View All Facts

MATCH (f:Fact)
RETURN f.relation, f.status, f.version, f.timestamp
ORDER BY f.relation, f.version;

Purpose:
Shows all stored facts.
Verifies:

- Version increments
- ACTIVE vs SUPERSEDED status
- Temporal ordering
- Historical trace

Expected Output After Demo:

Location | SUPERSEDED | 1 | 2023-01
Location | ACTIVE | 2 | 2023-06
WorksAs | SUPERSEDED | 1 | 2023-01
WorksAs | ACTIVE | 2 | 2023-06

This demonstrates that newer facts supersede older ones.

---

## 2. Count Facts By Status

MATCH (f:Fact)
RETURN f.status, count(\*) AS count;

Purpose:
Measures conflict resolution impact.

Expected:

SUPERSEDED | 2
ACTIVE | 2

This proves 2 conflicts were resolved.

---

## 3. Total Extracted Facts

MATCH (f:Fact)
RETURN count(\*) AS total_facts;

Purpose:
Shows total number of fact nodes created.

Expected:
4

---

## 4. Visual Graph View

MATCH (s:Entity)-[:HAS_FACT]->(f:Fact)-[:TARGET]->(o:Entity)
RETURN s, f, o;

Purpose:
Visualizes hierarchical memory structure:

User
└── HAS_FACT
├── Fact (ACTIVE)
├── Fact (SUPERSEDED)
└── TARGET → Entity

This demonstrates structured fact graph instead of opaque memory blobs.
