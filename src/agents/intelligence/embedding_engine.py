import torch
from sentence_transformers import SentenceTransformer
from src.config.loader import config
from src.common.utils import get_logger

logger = get_logger(__name__)


class EmbeddingEngine:

    def __init__(self):
        # Determine best device (MPS for Mac, CUDA for Linux, or CPU) [cite: 24]
        self.device = "mps" if torch.backends.mps.is_available() else "cpu" [cite: 24, 25]
        self.model_name = config.model_name
        self.dimension = config.model_dimension

        logger.info(f"🧠 Initializing EmbeddingEngine on {self.device}...")
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"✅ Model {self.model_name} loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise

    def get_embeddings(self, text: str):
        """Generates a normalized vector for the input text."""
        if not text.strip():
            return [0.0] * self.dimension

        try:
            # Generate and convert to list for JSON serialization [cite: 48]
            embeddings = self.model.encode([text])[0].tolist()
            return embeddings
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            return [0.0] * self.dimension
