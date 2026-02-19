"""
Unit tests for ECHMP Layer 2
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from layer2_consolidator import Layer2Consolidator


class TestLayer2Consolidator(unittest.TestCase):
    """Test suite for Layer 2 consolidation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        self.consolidator = Layer2Consolidator(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="test",
            similarity_threshold=0.85
        )
        self.consolidator.neo4j_driver = self.mock_driver
    
    def test_fetch_active_facts(self):
        """Test fetching ACTIVE facts from Neo4j."""
        # Mock Neo4j response
        mock_session = Mock()
        mock_result = [
            {
                "id": "fact1",
                "subject": "User",
                "relation": "enjoys",
                "object": "pizza",
                "timestamp": "2024-01",
                "text": "User enjoys pizza"
            },
            {
                "id": "fact2",
                "subject": "User",
                "relation": "likes",
                "object": "Italian food",
                "timestamp": "2024-02",
                "text": "User likes Italian food"
            }
        ]
        
        mock_session.run.return_value = mock_result
        self.mock_driver.session.return_value.__enter__.return_value = mock_session
        
        facts = self.consolidator._fetch_active_facts()
        
        self.assertEqual(len(facts), 2)
        self.assertEqual(facts[0]["id"], "fact1")
        self.assertEqual(facts[1]["subject"], "User")
    
    def test_process_2a_embeddings(self):
        """Test embedding generation and similarity computation."""
        facts = [
            {"id": "f1", "text": "User enjoys pizza"},
            {"id": "f2", "text": "User likes pizza"},
            {"id": "f3", "text": "User prefers wine"}
        ]
        
        embeddings, similarity_matrix = self.consolidator._process_2a_embeddings(facts)
        
        # Check embedding shape
        self.assertEqual(embeddings.shape[0], 3)
        self.assertEqual(embeddings.shape[1], 384)  # MiniLM dimension
        
        # Check similarity matrix shape
        self.assertEqual(similarity_matrix.shape, (3, 3))
        
        # Diagonal should be 1.0 (self-similarity)
        np.testing.assert_array_almost_equal(
            np.diag(similarity_matrix), 
            [1.0, 1.0, 1.0]
        )
        
        # Pizza facts should be more similar than wine fact
        pizza_sim = similarity_matrix[0, 1]
        wine_sim = similarity_matrix[0, 2]
        self.assertGreater(pizza_sim, wine_sim)
    
    def test_process_2b_clustering(self):
        """Test hierarchical clustering."""
        facts = [
            {"id": "f1", "text": "enjoys pizza"},
            {"id": "f2", "text": "likes pizza"},
            {"id": "f3", "text": "prefers wine"}
        ]
        
        # Create mock similarity matrix
        similarity_matrix = np.array([
            [1.0, 0.9, 0.4],  # f1 similar to f2
            [0.9, 1.0, 0.3],  # f2 similar to f1
            [0.4, 0.3, 1.0]   # f3 dissimilar
        ])
        
        clusters = self.consolidator._process_2b_clustering(facts, similarity_matrix)
        
        # Should create 2 clusters: [f1, f2] and [f3]
        self.assertEqual(len(clusters), 2)
        
        # Find pizza cluster
        pizza_cluster = [c for c in clusters if len(c) == 2][0]
        self.assertEqual(len(pizza_cluster), 2)
    
    @patch('layer2_consolidator.requests.post')
    def test_call_ollama(self, mock_post):
        """Test Ollama API call."""
        # Mock Ollama response
        mock_post.return_value.json.return_value = {
            "response": "User frequently enjoys pizza."
        }
        mock_post.return_value.raise_for_status = Mock()
        
        prompt = "Summarize: User ate pizza. User ordered pizza."
        result = self.consolidator._call_ollama(prompt)
        
        self.assertIn("pizza", result.lower())
        mock_post.assert_called_once()
    
    def test_process_2d_graph_update(self):
        """Test graph update with generalization nodes."""
        generalizations = [
            {
                "id": "gen1",
                "summary_text": "User enjoys pizza frequently",
                "source_facts": ["f1", "f2", "f3"],
                "cluster_id": 0,
                "fact_count": 3,
                "timestamp": "2024-02-19T08:00:00"
            }
        ]
        
        # Mock Neo4j session
        mock_session = Mock()
        mock_result = Mock()
        mock_result.single.return_value = {"count": 10}
        mock_session.run.return_value = mock_result
        
        self.mock_driver.session.return_value.__enter__.return_value = mock_session
        
        stats = self.consolidator._process_2d_graph_update(generalizations)
        
        # Verify stats structure
        self.assertIn("original_facts", stats)
        self.assertIn("compression_ratio", stats)
        self.assertGreater(stats["compression_ratio"], 0)
        self.assertLessEqual(stats["compression_ratio"], 1.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        self.consolidator = Layer2Consolidator()
        self.consolidator.neo4j_driver = Mock()
    
    def test_empty_facts(self):
        """Test handling of empty fact list."""
        embeddings, sim_matrix = self.consolidator._process_2a_embeddings([])
        self.assertEqual(len(embeddings), 0)
    
    def test_single_fact_clustering(self):
        """Test clustering with single fact."""
        facts = [{"id": "f1", "text": "Single fact"}]
        sim_matrix = np.array([[1.0]])
        
        clusters = self.consolidator._process_2b_clustering(facts, sim_matrix)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]), 1)


if __name__ == "__main__":
    unittest.main()
