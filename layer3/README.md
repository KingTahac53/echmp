# ECHMP Layer 3: Strategic Pruning

## Overview

Layer 3 is the final pruning stage of the ECHMP pipeline. It scores every **ACTIVE** `Fact` node and every `GeneralizationNode` (produced by Layer 2) across four dimensions, then decides whether to **RETAIN** or **ARCHIVE** each node.

---

## Scoring Formula

```
PruneScore = 0.40 × Centrality
           + 0.30 × EventAnchor
           + 0.20 × Recency
           + 0.10 × Frequency
```

| Dimension | Weight | Method |
|-----------|--------|--------|
| **Centrality** | 0.40 | PageRank on Neo4j graph (GDS or Python fallback) |
| **EventAnchor** | 0.30 | Life-event keyword match (1.0 = match, 0.2 = mundane) |
| **Recency** | 0.20 | Exponential decay with 30-day half-life |
| **Frequency** | 0.10 | Normalised retrieval count |

---

## Pruning Thresholds

| Score | Decision |
|-------|----------|
| `>= 0.60` | **RETAIN** |
| `0.30 – 0.59` | **RETAIN** (boundary — conservative) |
| `< 0.30` | **ARCHIVE** |

---

## Worked Examples (from project spec)

| Node | C | E | R | F | Score | Decision |
|------|---|---|---|---|-------|----------|
| User is Principal (hub, job event, recent) | 0.85 | 1.0 | 0.90 | 0.80 | **0.90** | RETAIN |
| User ate pizza Jan 15 (isolated, old) | 0.05 | 0.2 | 0.001 | 0.0 | **0.10** | ARCHIVE |
| User moved to Portland (hub, location event) | 0.75 | 1.0 | 0.85 | 0.70 | **0.84** | RETAIN |

---

## File Structure

```
layer3/
├── layer3_pruner.py      # Main pruning engine
├── scoring.py            # Standalone scoring functions
├── config.py             # Tunable parameters
├── test_layer3.py        # Unit tests (pytest)
├── debug_layer3.py       # Environment diagnostics
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # This file
```

---

## Quick Start

### 1. Install dependencies

```bash
cd layer3
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Neo4j credentials
```

### 3. Run diagnostics

```bash
python layer3/debug_layer3.py
```

### 4. Run Layer 3

```bash
python layer3/layer3_pruner.py
```

### 5. Run tests

```bash
python -m pytest layer3/test_layer3.py -v
```

---

## Pipeline Position

```
LoCoMo Conversations
       ↓
Layer 1 — Conflict Resolution + Versioned Facts  →  Neo4j (ACTIVE/SUPERSEDED)
       ↓
Layer 2 — Semantic Consolidation (MiniLM + Llama) →  GeneralizationNodes
       ↓
Layer 3 — Strategic Pruning (PageRank + Event)   →  RETAIN / ARCHIVED
       ↓
Final Memory: Compact, accurate, event-grounded
```

---

## PageRank: GDS vs Python Fallback

Layer 3 automatically detects whether the **Neo4j Graph Data Science (GDS)** plugin is installed:

- **With GDS** → runs `gds.pageRank.stream()` directly in the database (fast, scalable)
- **Without GDS** → fetches the adjacency list and runs power-iteration PageRank in Python

To install GDS: https://neo4j.com/docs/graph-data-science/current/installation/

---

## Neo4j Schema Expected

Layer 3 reads:
```cypher
// From Layer 1
(s:Entity)-[:HAS_FACT]->(f:Fact {status:'ACTIVE'})-[:TARGET]->(o:Entity)

// From Layer 2
(g:GeneralizationNode)
```

Layer 3 writes:
```cypher
// Archived nodes
SET f.status = 'ARCHIVED'
SET f.archived_at = datetime()
SET f.prune_score = <float>

// Retained nodes (score stored for observability)
SET f.prune_score = <float>
```

---

## Configuration

Edit `layer3/config.py` to tune the pruner:

```python
W_CENTRALITY   = 0.40   # PageRank weight
W_EVENT_ANCHOR = 0.30   # Life-event weight
W_RECENCY      = 0.20   # Time-decay weight
W_FREQUENCY    = 0.10   # Retrieval-freq weight

RETAIN_THRESHOLD  = 0.60
ARCHIVE_THRESHOLD = 0.30
RECENCY_HALF_LIFE_DAYS = 30.0
```

---

**ECHMP Project — Team 4**  
Gopinath CS · Taha · Pramod · Veera  
https://github.com/KingTahac53/echmp
