"""Concrete Sentence-Transformers text embedding implementation."""

import threading
from typing import List, Optional
from app.core.logging import get_logger
from app.domain.interfaces.embedder import TextEmbedderInterface

logger = get_logger(__name__)


class SentenceTransformerEmbedder(TextEmbedderInterface):
    """Generates dense semantic vector embeddings using local sentence-transformers models.
    
    Default Model: 'all-MiniLM-L6-v2'
    Domain Note: General-purpose English semantic embedding baseline; domain suitability for OIL SIF precursor semantics has not yet been empirically validated.
    Dimensionality: 384 dimensions
    Execution: Local, offline CPU/GPU inference without external API or cloud calls.
    Lifecycle: Thread-safe singleton model instance in memory.
    """

    _instance_lock = threading.Lock()
    _shared_model = None
    _shared_model_name: Optional[str] = None

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        expected_dimension: int = 384,
    ):
        self._model_name = model_name
        self._dimension = expected_dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_model(self):
        """Lazy load and cache sentence-transformers model instance."""
        if SentenceTransformerEmbedder._shared_model is None or SentenceTransformerEmbedder._shared_model_name != self._model_name:
            with SentenceTransformerEmbedder._instance_lock:
                if SentenceTransformerEmbedder._shared_model is None or SentenceTransformerEmbedder._shared_model_name != self._model_name:
                    logger.info(f"Loading local embedding model: {self._model_name}")
                    try:
                        from sentence_transformers import SentenceTransformer
                        SentenceTransformerEmbedder._shared_model = SentenceTransformer(self._model_name)
                        SentenceTransformerEmbedder._shared_model_name = self._model_name
                        logger.info(f"Successfully loaded embedding model: {self._model_name}")
                    except Exception as e:
                        logger.error(f"Failed to load embedding model '{self._model_name}': {e}")
                        raise RuntimeError(f"Embedding model '{self._model_name}' could not be initialized: {e}") from e
        return SentenceTransformerEmbedder._shared_model

    def embed_text(self, text: str) -> List[float]:
        """Generate a dense 384-dimensional embedding vector for a single text."""
        clean_text = text.strip() if text else ""
        if not clean_text:
            raise ValueError("Input text for embedding generation cannot be empty")

        model = self._get_model()
        try:
            vector = model.encode(clean_text, convert_to_numpy=True, normalize_embeddings=True)
            vector_list = vector.tolist()
            if len(vector_list) != self._dimension:
                raise ValueError(
                    f"Generated embedding dimension {len(vector_list)} does not match expected {self._dimension}"
                )
            return vector_list
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate dense 384-dimensional embeddings for a batch of text strings."""
        if not texts:
            return []

        clean_texts = [t.strip() for t in texts]
        for i, t in enumerate(clean_texts):
            if not t:
                raise ValueError(f"Batch item at index {i} is empty")

        model = self._get_model()
        try:
            vectors = model.encode(clean_texts, convert_to_numpy=True, normalize_embeddings=True)
            results = [v.tolist() for v in vectors]
            for i, vec in enumerate(results):
                if len(vec) != self._dimension:
                    raise ValueError(
                        f"Batch embedding at index {i} has dimension {len(vec)}, expected {self._dimension}"
                    )
            return results
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise
