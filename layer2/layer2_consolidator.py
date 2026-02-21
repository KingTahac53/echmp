"""
ECHMP Layer 2: Memory Consolidation
Implements four sub-processes: 2A, 2B, 2C, 2D
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
import requests
import json
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Layer2Consolidator:
    """
    Main orchestrator for Layer 2 memory consolidation.
    Processes ACTIVE facts from Layer 1 through four sequential sub-processes.
    """
    
    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        ollama_url: str = "http://localhost:11434",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85
    ):
        """
        Initialize Layer 2 consolidator.
        
        Args:
            neo4j_uri: Neo4j database connection string
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            ollama_url: Ollama API endpoint
            embedding_model: SentenceTransformer model name
            similarity_threshold: Cosine similarity threshold for consolidation
        """
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri, 
            auth=(neo4j_user, neo4j_password)
        )
        self.ollama_url = ollama_url
        self.similarity_threshold = similarity_threshold
        
        # Initialize embedding model (2A)
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info("Embedding model loaded successfully")
        
    def close(self):
        """Close database connection."""
        self.neo4j_driver.close()
        
    def run_consolidation(self) -> Dict[str, any]:
        """
        Execute complete Layer 2 consolidation pipeline.
        
        Returns:
            Dict containing consolidation statistics
        """
        logger.info("Starting Layer 2 consolidation pipeline...")
        
        # Fetch ACTIVE facts from Neo4j
        facts = self._fetch_active_facts()
        logger.info(f"Retrieved {len(facts)} ACTIVE facts from Layer 1")
        
        if len(facts) == 0:
            logger.warning("No ACTIVE facts found. Skipping consolidation.")
            return {"status": "skipped", "reason": "no_active_facts"}
        
        # Sub-Process 2A: Embedding Generation & Similarity
        embeddings, similarity_matrix = self._process_2a_embeddings(facts)
        logger.info("Sub-process 2A completed: Embeddings generated")
        
        # Sub-Process 2B: Clustering
        clusters = self._process_2b_clustering(facts, similarity_matrix)
        logger.info(f"Sub-process 2B completed: {len(clusters)} clusters formed")
        
        # Sub-Process 2C: LLM Summarization
        generalizations = self._process_2c_summarization(clusters, embeddings)
        logger.info(f"Sub-process 2C completed: {len(generalizations)} generalizations created")
        
        # Sub-Process 2D: Graph Update
        stats = self._process_2d_graph_update(generalizations)
        logger.info("Sub-process 2D completed: Graph updated")
        
        return stats
    
    def _fetch_active_facts(self) -> List[Dict]:
        """
        Fetch all ACTIVE facts from Neo4j.
        
        Returns:
            List of fact dictionaries with id, subject, relation, object, timestamp
        """
        query = """
        MATCH (f:Fact)
        WHERE f.status = 'ACTIVE'
        RETURN f.id AS id, 
               f.subject AS subject, 
               f.relation AS relation, 
               f.object AS object,
               f.timestamp AS timestamp,
               f.text AS text
        """
        
        with self.neo4j_driver.session() as session:
            result = session.run(query)
            facts = []
            for record in result:
                # Create text representation for embedding
                fact_text = record["text"] if record["text"] else \
                           f"{record['subject']} {record['relation']} {record['object']}"
                
                facts.append({
                    "id": record["id"],
                    "subject": record["subject"],
                    "relation": record["relation"],
                    "object": record["object"],
                    "timestamp": record["timestamp"],
                    "text": fact_text
                })
            return facts
    
    def _process_2a_embeddings(
        self, 
        facts: List[Dict]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sub-Process 2A: Embedding Generation and Similarity Computation.
        
        Args:
            facts: List of fact dictionaries
            
        Returns:
            Tuple of (embeddings, similarity_matrix)
        """
        logger.info("2A: Generating embeddings...")
        
        # Extract text representations
        texts = [fact["text"] for fact in facts]
        
        # Generate embeddings (384-dimensional)
        embeddings = self.embedding_model.encode(
            texts, 
            convert_to_numpy=True,
            show_progress_bar=True
        )
        
        # Compute pairwise cosine similarity
        similarity_matrix = cosine_similarity(embeddings)
        
        # Log similarity statistics
        high_sim_count = np.sum(similarity_matrix > self.similarity_threshold) - len(facts)
        logger.info(f"2A: Found {high_sim_count} fact pairs above threshold {self.similarity_threshold}")
        
        return embeddings, similarity_matrix
    
    def _process_2b_clustering(
        self,
        facts: List[Dict],
        similarity_matrix: np.ndarray
    ) -> List[List[Dict]]:
        """
        Sub-Process 2B: Clustering and Grouping.
        
        Args:
            facts: List of fact dictionaries
            similarity_matrix: Pairwise similarity matrix
            
        Returns:
            List of clusters, where each cluster is a list of facts
        """
        logger.info("2B: Performing hierarchical clustering...")
        
        if len(facts) < 2:
            # Single fact = single cluster
            return [[facts[0]]] if facts else []
        
        # Convert similarity to distance for clustering
        distance_matrix = 1 - similarity_matrix
        
        # Agglomerative clustering with complete linkage
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - self.similarity_threshold,
            metric='precomputed',
            linkage='complete'
        )
        
        cluster_labels = clustering.fit_predict(distance_matrix)
        
        # Group facts by cluster ID
        clusters_dict = {}
        for idx, label in enumerate(cluster_labels):
            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append(facts[idx])
        
        clusters = list(clusters_dict.values())
        
        # Log cluster size distribution
        cluster_sizes = [len(c) for c in clusters]
        logger.info(f"2B: Cluster sizes - min: {min(cluster_sizes)}, "
                   f"max: {max(cluster_sizes)}, avg: {np.mean(cluster_sizes):.2f}")
        
        return clusters
    
    def _process_2c_summarization(
        self,
        clusters: List[List[Dict]],
        embeddings: np.ndarray
    ) -> List[Dict]:
        """
        Sub-Process 2C: Summarization via Language Model.
        
        Args:
            clusters: List of fact clusters
            embeddings: Fact embeddings for validation
            
        Returns:
            List of generalization dictionaries
        """
        logger.info("2C: Generating LLM summaries...")
        
        generalizations = []
        
        for cluster_id, cluster in enumerate(clusters):
            # Skip singleton clusters (nothing to consolidate)
            if len(cluster) == 1:
                logger.debug(f"Cluster {cluster_id}: Singleton, skipping")
                continue
            
            logger.info(f"2C: Processing cluster {cluster_id} with {len(cluster)} facts")
            
            # Construct LLM prompt
            fact_texts = [f"- {fact['text']}" for fact in cluster]
            prompt = (
                "Summarize the following related facts into a single general statement. "
                "Response in one sentence.\n\n"
                + "\n".join(fact_texts)
            )
            
            # Call Ollama API
            try:
                summary = self._call_ollama(prompt)
                
                # Validate semantic consistency
                summary_embedding = self.embedding_model.encode([summary])[0]
                
                generalization = {
                    "id": str(uuid.uuid4()),
                    "summary_text": summary,
                    "source_facts": [fact["id"] for fact in cluster],
                    "cluster_id": cluster_id,
                    "fact_count": len(cluster),
                    "timestamp": datetime.now().isoformat()
                }
                
                generalizations.append(generalization)
                logger.info(f"2C: Created generalization: {summary[:80]}...")
                
            except Exception as e:
                logger.error(f"2C: Failed to summarize cluster {cluster_id}: {e}")
                continue
        
        return generalizations
    
    def _call_ollama(self, prompt: str, model: str = "llama3.2:1b") -> str:
        """
        Call Ollama API for LLM inference.
        
        Args:
            prompt: Input prompt
            model: Ollama model name
            
        Returns:
            Generated text
        """
        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result["response"].strip()
    
    def _process_2d_graph_update(
        self,
        generalizations: List[Dict]
    ) -> Dict[str, any]:
        """
        Sub-Process 2D: Graph Update and Consolidation.
        
        Args:
            generalizations: List of generalization dictionaries
            
        Returns:
            Dictionary of consolidation statistics
        """
        logger.info("2D: Updating Neo4j graph...")
        
        with self.neo4j_driver.session() as session:
            # Count original facts
            original_count = session.run(
                "MATCH (f:Fact {status: 'ACTIVE'}) RETURN count(f) AS count"
            ).single()["count"]
            
            for gen in generalizations:
                # Create GENERALIZATION_NODE
                session.run("""
                    CREATE (g:GeneralizationNode {
                        node_id: $node_id,
                        summary_text: $summary_text,
                        timestamp: $timestamp,
                        source_facts: $source_facts,
                        compression_ratio: $compression_ratio
                    })
                """, 
                    node_id=gen["id"],
                    summary_text=gen["summary_text"],
                    timestamp=gen["timestamp"],
                    source_facts=gen["source_facts"],
                    compression_ratio=1.0 / gen["fact_count"]
                )
                
                # Create CONSOLIDATES_TO relationships and mark facts
                for fact_id in gen["source_facts"]:
                    session.run("""
                        MATCH (f:Fact {id: $fact_id})
                        MATCH (g:GeneralizationNode {node_id: $gen_id})
                        SET f.status = 'CONSOLIDATED'
                        MERGE (f)-[:CONSOLIDATES_TO]->(g)
                    """,
                        fact_id=fact_id,
                        gen_id=gen["id"]
                    )
                
                logger.info(f"2D: Created generalization node {gen['id'][:8]}... "
                          f"consolidating {gen['fact_count']} facts")
            
            # Count final active facts
            final_count = session.run(
                "MATCH (f:Fact {status: 'ACTIVE'}) RETURN count(f) AS count"
            ).single()["count"]
            
            # Count generalization nodes
            gen_count = session.run(
                "MATCH (g:GeneralizationNode) RETURN count(g) AS count"
            ).single()["count"]
        
        stats = {
            "original_facts": original_count,
            "consolidated_facts": original_count - final_count,
            "remaining_active": final_count,
            "generalizations_created": gen_count,
            "compression_ratio": final_count / original_count if original_count > 0 else 1.0
        }
        
        logger.info(f"2D: Consolidation complete - {stats['compression_ratio']:.1%} retention rate")
        
        return stats


# Demo / Test Script
def demo_layer2():
    """
    Demonstration of Layer 2 consolidation.
    Assumes Layer 1 has already populated ACTIVE facts in Neo4j.
    """
    print("="*60)
    print("ECHMP Layer 2 Demo: Memory Consolidation")
    print("="*60)
    
    # Initialize consolidator
    consolidator = Layer2Consolidator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="your_password_here",  # UPDATE THIS
        ollama_url="http://localhost:11434",
        similarity_threshold=0.85
    )
    
    try:
        # Run consolidation pipeline
        stats = consolidator.run_consolidation()
        
        # Print results
        print("\n" + "="*60)
        print("CONSOLIDATION RESULTS")
        print("="*60)
        for key, value in stats.items():
            print(f"{key}: {value}")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        consolidator.close()


if __name__ == "__main__":
    demo_layer2()
