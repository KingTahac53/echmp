# ECHMP Layer 2: Memory Consolidation

Complete implementation of Layer 2 semantic consolidation for the ECHMP (Event-Centric Hierarchical Memory Pruning) project.

## 📁 Files in This Directory

```
layer2/
├── layer2_consolidator.py   # Main implementation (434 lines)
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── test_layer2.py            # Unit tests (177 lines)
├── debug_layer2.py           # Diagnostic tool
├── SETUP.md                  # Detailed setup guide
└── README.md                 # This file
```

## 🎯 What Layer 2 Does

Layer 2 receives **conflict-resolved ACTIVE facts** from Layer 1 and applies **semantic consolidation** to reduce memory bloat while preserving meaning.

### Four Sub-Processes

| Sub-Process | Purpose | Technology |
|-------------|---------|------------|
| **2A** | Embedding Generation & Similarity | SentenceTransformer (all-MiniLM-L6-v2) |
| **2B** | Clustering & Grouping | Agglomerative Hierarchical Clustering |
| **2C** | LLM Summarization | Ollama (Llama 3.2 1B) |
| **2D** | Graph Update & Consolidation | Neo4j (GENERALIZATION nodes) |

### Example Workflow

**Input (Layer 1 → Layer 2):**
```
Fact 1: "User ate pizza on Jan 15"
Fact 2: "User ordered pizza on Feb 3"
Fact 3: "User ate pizza on Mar 22"
Fact 4: "User prefers red wine"
```

**Processing:**
1. **2A**: Generate embeddings → Pizza facts have 0.88+ similarity
2. **2B**: Cluster → [Fact 1, 2, 3] in Cluster A, [Fact 4] in Cluster B
3. **2C**: Summarize Cluster A → "User frequently enjoys pizza across multiple months"
4. **2D**: Create GENERALIZATION node, mark original facts as CONSOLIDATED

**Output (Layer 2 → Layer 3):**
```
GENERALIZATION_1: "User frequently enjoys pizza" (consolidates 3 facts)
Fact 4: "User prefers red wine" (singleton, remains ACTIVE)

Compression: 4 facts → 2 memory units (50% retention)
```

## 🚀 Quick Start

### 1. Install

```bash
cd layer2/
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Neo4j password
```

### 2. Check Prerequisites

```bash
python debug_layer2.py
```

This checks:
- ✅ Python 3.11+
- ✅ Required packages installed
- ✅ Neo4j running & accessible
- ✅ Ollama running with llama3.2:1b
- ✅ Embedding model downloaded

### 3. Run Layer 2

```python
from layer2_consolidator import Layer2Consolidator

consolidator = Layer2Consolidator(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="your_password",
    similarity_threshold=0.85
)

stats = consolidator.run_consolidation()
print(stats)

consolidator.close()
```

**Or via command line:**
```bash
python layer2_consolidator.py
```

## 📊 Expected Output

```python
{
    'original_facts': 40,           # Facts before consolidation
    'consolidated_facts': 15,       # Facts merged into generalizations
    'remaining_active': 25,         # Facts still ACTIVE
    'generalizations_created': 5,   # New GENERALIZATION nodes
    'compression_ratio': 0.625      # 62.5% retention (25/40)
}
```

## 🧪 Testing

Run unit tests:
```bash
python -m pytest test_layer2.py -v
```

Or standard unittest:
```bash
python test_layer2.py
```

**Test coverage:**
- Fetch ACTIVE facts from Neo4j
- Embedding generation (384-dim)
- Similarity computation (cosine)
- Hierarchical clustering
- Ollama API calls
- Neo4j graph updates
- Edge cases (empty, singleton)

## 🔧 Configuration

Edit `.env` or pass parameters:

```python
consolidator = Layer2Consolidator(
    similarity_threshold=0.85,  # Lower = more aggressive consolidation
    embedding_model="sentence-transformers/paraphrase-MiniLM-L6-v2",
    ollama_url="http://localhost:11434"
)
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `similarity_threshold` | 0.85 | Cosine similarity threshold (0-1) |
| `embedding_model` | all-MiniLM-L6-v2 | SentenceTransformer model |
| `ollama_model` | llama3.2:1b | Ollama LLM for summarization |

## 🗄️ Neo4j Schema

### Input (from Layer 1)

```cypher
(:Fact {
    id: String,
    subject: String,
    relation: String,
    object: String,
    timestamp: String,
    status: 'ACTIVE',  # Layer 2 only processes ACTIVE
    text: String       # Optional, for better embeddings
})
```

### Output (to Layer 3)

```cypher
(:GeneralizationNode {
    node_id: String (UUID),
    summary_text: String,
    timestamp: String,
    source_facts: [String],  # List of consolidated fact IDs
    compression_ratio: Float
})

(:Fact {status: 'CONSOLIDATED'})-[:CONSOLIDATES_TO]->(:GeneralizationNode)
```

## 🐛 Troubleshooting

### No facts found

```cypher
// Check fact count and status
MATCH (f:Fact)
RETURN f.status, count(f)
```

**Solution:** Ensure Layer 1 has populated ACTIVE facts.

### Ollama connection failed

```bash
# Check Ollama
curl http://localhost:11434/api/version

# Start Ollama
ollama serve

# Pull model if missing
ollama pull llama3.2:1b
```

### Neo4j authentication error

```bash
# Update .env with correct password
NEO4J_PASSWORD=your_actual_password
```

### Out of memory (large datasets)

```python
# Process in batches
# TODO: Add batch processing for 1000+ facts
```

## 📈 Performance

**Tested on:**
- MacBook Pro M1 (8GB RAM)
- 100 facts: ~30 seconds
- 500 facts: ~2 minutes
- GPU acceleration available for embeddings

**Bottlenecks:**
1. Embedding generation: O(n) - GPU helps
2. Similarity computation: O(n²) - Use batch processing
3. Ollama calls: O(clusters) - Parallelize

## 🔗 Integration

### With Layer 1 (Upstream)

Layer 1 must:
- Write facts to Neo4j with `status='ACTIVE'`
- Include `subject`, `relation`, `object`, `timestamp`
- Optionally provide `text` field for better embeddings

### With Layer 3 (Downstream)

Layer 3 will:
- Process both ACTIVE facts AND GeneralizationNodes
- Compute centrality on consolidated graph
- Apply pruning scores considering generalizations

## 🎓 Project Context

**ECHMP**: Event-Centric Hierarchical Memory Pruning
**Team**: Team 4 (Gopi, Taha, Pramod, Veera)
**Institution**: University Capstone Project
**Dataset**: LoCoMo (Long-Context Memory benchmark)
**Goal**: Reduce memory bloat in conversational AI by 60% while maintaining 95% accuracy

## 📚 References

1. **Mem0** (Chhikara et al., 2025): Base memory architecture
2. **LoCoMo** (Maharana et al., 2024): Evaluation benchmark
3. **SentenceTransformers**: Embedding generation
4. **scikit-learn**: Hierarchical clustering

## 🔄 Next Steps

1. ✅ Layer 2 implementation complete
2. ⏭️ Implement Layer 3 (Strategic Pruning with PageRank)
3. ⏭️ End-to-end pipeline integration
4. ⏭️ LoCoMo evaluation
5. ⏭️ Compare vs Mem0 baseline

## 📞 Support

- **GitHub**: https://github.com/KingTahac53/echmp
- **Documentation**: See SETUP.md
- **Issues**: Run `python debug_layer2.py` first

---

**Status**: ✅ Complete and tested  
**Last Updated**: 2026-02-19  
**Version**: 1.0.0
