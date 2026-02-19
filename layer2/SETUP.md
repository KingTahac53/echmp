# ECHMP Layer 2 Setup & Integration Guide

## Prerequisites

1. **Python 3.11+** installed
2. **Neo4j** running on bolt://localhost:7687
3. **Ollama** running on http://localhost:11434
4. **Docker Desktop** (for Neo4j if not installed)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
# Edit .env with your Neo4j password
```

### 3. Pull Ollama Model

```bash
ollama pull llama3.2:1b
```

### 4. Verify Services

**Check Neo4j:**
```bash
curl http://localhost:7474
# Should return Neo4j browser
```

**Check Ollama:**
```bash
curl http://localhost:11434/api/version
# Should return version JSON
```

## Integration with Layer 1

Layer 2 expects facts in Neo4j with this schema:

```cypher
(:Fact {
    id: String,
    subject: String,
    relation: String,
    object: String,
    timestamp: String,
    status: 'ACTIVE' | 'CONSOLIDATED' | 'SUPERSEDED',
    text: String (optional, for better embeddings)
})
```

### Sample Data Setup

Run this Cypher query in Neo4j Browser to create test facts:

```cypher
// Create test facts
CREATE (f1:Fact {
    id: 'fact_001',
    subject: 'User',
    relation: 'enjoys',
    object: 'pizza',
    timestamp: '2024-01-15',
    status: 'ACTIVE',
    text: 'User enjoys eating pizza'
})

CREATE (f2:Fact {
    id: 'fact_002',
    subject: 'User',
    relation: 'likes',
    object: 'Italian food',
    timestamp: '2024-01-20',
    status: 'ACTIVE',
    text: 'User likes Italian food'
})

CREATE (f3:Fact {
    id: 'fact_003',
    subject: 'User',
    relation: 'ordered',
    object: 'pizza',
    timestamp: '2024-02-03',
    status: 'ACTIVE',
    text: 'User ordered pizza from restaurant'
})

CREATE (f4:Fact {
    id: 'fact_004',
    subject: 'User',
    relation: 'prefers',
    object: 'wine',
    timestamp: '2024-02-10',
    status: 'ACTIVE',
    text: 'User prefers red wine'
})
```

## Running Layer 2

### Basic Usage

```python
from layer2_consolidator import Layer2Consolidator

# Initialize
consolidator = Layer2Consolidator(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="your_password",
    similarity_threshold=0.85
)

# Run consolidation
stats = consolidator.run_consolidation()

# Print results
print(stats)

# Cleanup
consolidator.close()
```

### Command Line

```bash
python layer2_consolidator.py
```

## Verification

### Check Consolidation Results

```cypher
// View all generalization nodes
MATCH (g:GeneralizationNode)
RETURN g.summary_text, g.source_facts, g.compression_ratio

// View consolidated facts
MATCH (f:Fact {status: 'CONSOLIDATED'})-[:CONSOLIDATES_TO]->(g:GeneralizationNode)
RETURN f.text AS original_fact, g.summary_text AS generalization

// Count consolidation impact
MATCH (f:Fact)
RETURN f.status AS status, count(f) AS count
```

### Expected Results

With the sample data above:
- **3 pizza-related facts** should be consolidated into 1 generalization
- **1 wine fact** remains singleton (not consolidated)
- **Compression ratio**: ~75% (3 facts → 1 generalization + 1 singleton)

## Troubleshooting

### Issue: "Embedding model download failed"

**Solution:**
```python
# Download model manually
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
```

### Issue: "Neo4j connection refused"

**Solution:**
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Start Neo4j if stopped
docker start neo4j
```

### Issue: "Ollama connection failed"

**Solution:**
```bash
# Check Ollama service
ollama list

# Start Ollama (Mac/Linux)
ollama serve
```

### Issue: "No ACTIVE facts found"

**Solution:**
- Verify Layer 1 populated facts
- Check fact status: `MATCH (f:Fact) RETURN f.status, count(f)`
- Insert test data (see Sample Data Setup above)

## Performance Tuning

### Large Datasets (1000+ facts)

```python
# Adjust batch processing
consolidator = Layer2Consolidator(
    similarity_threshold=0.85,  # Lower = more aggressive consolidation
)

# Monitor memory usage
import psutil
print(f"Memory: {psutil.virtual_memory().percent}%")
```

### Speed Optimization

1. **Use GPU for embeddings** (if available):
   - SentenceTransformer automatically uses CUDA
   - Verify: `torch.cuda.is_available()`

2. **Reduce clustering complexity**:
   - Use `single` linkage instead of `complete`
   - Adjust `distance_threshold`

3. **Batch Ollama calls**:
   - Process multiple clusters in parallel
   - Use `asyncio` for concurrent requests

## Next Steps

1. ✅ Verify Layer 2 consolidation works
2. ⏭️ Implement Layer 3 (Strategic Pruning)
3. ⏭️ Integrate with LoCoMo evaluation
4. ⏭️ Run end-to-end pipeline

## API Reference

### Layer2Consolidator

#### Constructor Parameters

- `neo4j_uri` (str): Neo4j connection URI
- `neo4j_user` (str): Neo4j username
- `neo4j_password` (str): Neo4j password
- `ollama_url` (str): Ollama API endpoint
- `embedding_model` (str): SentenceTransformer model name
- `similarity_threshold` (float): Cosine similarity threshold (0-1)

#### Methods

- `run_consolidation()` → Dict: Execute full pipeline
- `close()`: Close database connection

#### Return Statistics

```python
{
    'original_facts': int,          # Facts before consolidation
    'consolidated_facts': int,      # Facts consolidated
    'remaining_active': int,        # Facts still ACTIVE
    'generalizations_created': int, # New GENERALIZATION nodes
    'compression_ratio': float      # Retention rate (0-1)
}
```

## Contact & Support

- **GitHub**: https://github.com/KingTahac53/echmp
- **Team**: Team 4 (Gopi, Taha, Pramod, Veera)
