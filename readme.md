# ECHMP – Event-Centric Hierarchical Memory Pruning

This repository contains the implementation of **ECHMP**, a capstone project extending long-term memory systems for conversational AI agents.

## Project Overview

ECHMP introduces **human-like strategic forgetting** into memory-augmented LLM agents by:

- Resolving contradictory facts using temporal logic
- Normalizing and structuring dialogue facts
- Archiving outdated information instead of overwriting
- Preparing the foundation for memory consolidation and pruning

This project extends **Mem0** and is evaluated using the **LoCoMo benchmark**.

---

## Current Status (MVP)

✅ Layer 1: Conflict Resolution & Normalization

- Local LLM (Ollama) for fact extraction
- Canonical subject & relation normalization
- Temporal conflict resolution
- Graph-based memory storage (Neo4j)

---

## Tech Stack

- Python 3.11
- Ollama (local LLM)
- Neo4j (graph memory)
- Qdrant (vector memory – upcoming)
- mem0 (integration planned)

---

## Running Layer 1 Demo

```bash
python layer1/demo.py
```

Ensure the following are running:

- Ollama (http://localhost:11434)
- Neo4j (bolt://localhost:7687)
- Docker Desktop

## Roadmap

- ✅ Layer 1 – Conflict Resolution

- Layer 2 – Memory Consolidation

- Layer 3 – Strategic Pruning

- Mem0 Integration

- LoCoMo Evaluation

## Authors

Team 4 – University Capstone Project
