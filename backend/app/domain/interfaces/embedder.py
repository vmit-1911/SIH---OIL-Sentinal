"""Abstract interface for text embedding generation."""

from abc import ABC, abstractmethod
from typing import List


class TextEmbedderInterface(ABC):
    """Port for text embedding generators (e.g., Sentence-Transformers).
    
    Exposes fixed-length dense vector generation and model metadata.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension (e.g. 384)."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Underlying embedding model identifier."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate a dense embedding vector for a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate dense embedding vectors for a batch of text strings."""
        pass

