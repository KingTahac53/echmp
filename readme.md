# 🧠 ECHMP – Event-Centric Hierarchical Memory Pruning

This repository contains the implementation of **ECHMP**, a capstone project extending long-term memory systems for conversational AI agents.

---

## 📌 Project Overview

ECHMP introduces **human-like strategic forgetting** into memory-augmented LLM agents by:

- Resolving contradictory facts using temporal logic (**Layer 1**)
- Consolidating semantically similar facts (**Layer 2**)
- Pruning low-importance memories using graph-based scoring (**Layer 3**)

The system extends **Mem0** and is evaluated using the **LoCoMo benchmark**.

---

## 🏗️ Architecture

The system is implemented as a **3-layer pipeline**:

### 🔹 Layer 1 – Conflict Resolution & Fact Extraction
- Extracts structured facts *(subject, relation, object)*
- Resolves conflicts using temporal logic
- Stores facts in Neo4j graph

### 🔹 Layer 2 – Semantic Consolidation
- Groups similar facts using embeddings
- Summarizes clusters into generalized memory nodes

### 🔹 Layer 3 – Strategic Pruning
- Assigns importance scores using:
  - Graph centrality
  - Event relevance
  - Recency
  - Frequency
- Archives low-importance facts

---

## 🛠️ Tech Stack

- **Python 3.11**
- **Neo4j** (Graph Database)
- **Ollama** (Local LLM)
- **Sentence Transformers** (Embeddings)
- **Scikit-learn** (Clustering)

---

## ⚙️ Setup Requirements

Ensure the following services are running:

- Neo4j → `bolt://localhost:7687`  
- Ollama → `http://localhost:11434`  
- Python virtual environment activated  

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Full Pipeline Execution

### Step 1 — Ingest LoCoMo Dataset (Layer 1)

```bash
python -m scripts.ingest_locomo_layer1
```

**This will:**
- Process conversations  
- Extract facts using LLM  
- Store structured data in Neo4j  

---

### Step 2 — Run Layer 2 (Semantic Consolidation)

#### Debug Script to check dependencies before consolidation
```bash
python.exe .\layer2\debug_layer2.py
```

```bash
python.exe .\layer2\layer2_consolidator.py 
```

**This will:**
- Generate embeddings  
- Cluster similar facts  
- Create consolidated memory nodes  

---

### Step 3 — Run Layer 3 (Pruning)

```bash
python -m layer3.pruning_engine
```

**This will:**
- Compute importance scores  
- Archive low-value facts  
- Retain critical memories  

---

## 📊 Evaluation

Evaluation scripts and outputs are available in:

```
evaluation/
```

### Includes:

- Mem0 baseline results → `evaluation/Mem0_Analysis.ipynb`  
- ECHMP query evaluation → `evaluation/echmp_queries.md`  
- Neo4j output screenshots → `evaluation/echmp_results/`  

---

## 🔍 Example Query (Neo4j)

```cypher
MATCH (u:Entity {name:"User"})
-[:HAS_FACT]->(f:Fact {relation:"Occupation", status:"ACTIVE"})
-[:TARGET]->(o:Entity)
RETURN o.name
```

---

## 📈 Current Status

- ✅ Layer 1 – Implemented  
- ✅ Layer 2 – Implemented  
- ✅ Layer 3 – Implemented  
- ✅ Evaluation Completed  

---

## 👥 Authors

**Team 4 – University Capstone Project**
