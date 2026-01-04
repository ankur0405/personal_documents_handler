import numpy as np
from src.common.utils import get_logger

logger = get_logger(__name__)


class DiscoveryEngine:
    """
    Enterprise-grade classifier that uses unsupervised clustering.
    It identifies relationships between documents based on vector similarity
    rather than a hardcoded list of categories.
    """
    def __init__(self, similarity_threshold=0.85):
        # Threshold: How similar must two docs be to
        # be long to the same category?

        self.threshold = similarity_threshold
        # Stores 'Centroids' (the average vector) for discovered topics
        self.discovered_clusters = {}

    def calculate_similarity(self, vec_a, vec_b):
        """Mathematical Cosine Similarity using NumPy for high performance."""
        a = np.array(vec_a)
        b = np.array(vec_b)
        # Formula: (A dot B) / (||A|| * ||B||)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def categorize_document(self, doc_id, doc_vector, doc_text):
        """
        Determines the class of a document by comparing its vector
        to known discovery clusters.
        """
        best_match = None
        highest_sim = 0.0  # Tracks the closest 'Vibe' found so far

        # Compare new document against all previously discovered patterns
        for cluster_id, centroid in self.discovered_clusters.items():
            sim = self.calculate_similarity(doc_vector, centroid)
            if sim > highest_sim:
                highest_sim = sim
                best_match = cluster_id

        # Enterprise Logic: If no close match, create a new dynamic topic
        if highest_sim < self.threshold:
            new_topic_id = f"Discovery_{doc_id[:8]}"
            self.discovered_clusters[new_topic_id] = doc_vector
            logger.info(f"New semantic pattern discovered: {new_topic_id}")
            return new_topic_id

        return best_match
