from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticGrouper:
    """
    Groups memories based on semantic similarity.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85,
    ):
        self.model = SentenceTransformer(model_name)
        self.threshold = similarity_threshold

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        """
        return self.model.encode(texts, convert_to_numpy=True)

    def group_memories(self, memories: List[Dict]) -> List[List[Dict]]:
        """
        Group semantically similar memories.

        Each memory dict is expected to have a `memory` field (string).
        """
        if not memories:
            return []

        texts = [m["memory"] for m in memories]
        embeddings = self.embed_texts(texts)

        similarity_matrix = cosine_similarity(embeddings)

        visited = set()
        groups = []

        for i in range(len(memories)):
            if i in visited:
                continue

            group = [memories[i]]
            visited.add(i)

            for j in range(i + 1, len(memories)):
                if j in visited:
                    continue

                if similarity_matrix[i][j] >= self.threshold:
                    group.append(memories[j])
                    visited.add(j)

            groups.append(group)

        return groups
