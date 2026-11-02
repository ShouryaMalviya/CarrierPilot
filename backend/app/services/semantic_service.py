"""Optional semantic similarity adapter with lazy loading and transparent lexical fallback."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from app.services.matching_service import compute_tfidf_similarity


class EmbeddingProvider(ABC):
    """Abstract base provider for textual embedding generation and similarity."""

    @abstractmethod
    def get_model_name(self) -> str:
        """Return identifier of the underlying model or heuristic."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if model is loaded and ready for inference."""
        pass

    @abstractmethod
    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts (0.0 to 1.0)."""
        pass


class SentenceTransformerAdapter(EmbeddingProvider):
    """Lazy-loaded adapter for sentence-transformers embedding models."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._loaded = False
        self._load_error: Optional[str] = None

    def get_model_name(self) -> str:
        return self.model_name

    def is_available(self) -> bool:
        return self._loaded and self._model is not None

    def load_model(self) -> bool:
        """Attempt to load sentence-transformers model. Never raises uncaught exceptions."""
        if self._loaded and self._model is not None:
            return True
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(self.model_name)
            self._loaded = True
            self._load_error = None
            return True
        except Exception as exc:
            self._loaded = False
            self._model = None
            self._load_error = f"{type(exc).__name__}: {str(exc)}"
            return False

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        if not self.is_available():
            if not self.load_model():
                raise RuntimeError(
                    f"SentenceTransformer '{self.model_name}' could not be loaded: {self._load_error}"
                )

        import numpy as np

        embeddings = self._model.encode([text_a, text_b])
        norm_a = np.linalg.norm(embeddings[0])
        norm_b = np.linalg.norm(embeddings[1])

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        sim = float(np.dot(embeddings[0], embeddings[1]) / (norm_a * norm_b))
        return round(max(0.0, min(1.0, sim)), 4)


class MockEmbeddingAdapter(EmbeddingProvider):
    """Deterministic mock embedding provider for offline testing and verification."""

    def __init__(self, fixed_similarity: float = 0.85, model_name: str = "mock-mini-lm"):
        self.fixed_similarity = fixed_similarity
        self.model_name = model_name
        self.call_count = 0

    def get_model_name(self) -> str:
        return self.model_name

    def is_available(self) -> bool:
        return True

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        self.call_count += 1
        if not text_a or not text_b or not text_a.strip() or not text_b.strip():
            return 0.0
        return self.fixed_similarity


class SemanticSimilarityManager:
    """Manages semantic embedding provider lifecycle and transparent lexical fallback."""

    def __init__(self):
        self._provider: EmbeddingProvider = SentenceTransformerAdapter()

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    def set_provider(self, provider: EmbeddingProvider) -> None:
        """Inject a custom or mock provider (useful for testing without downloads)."""
        self._provider = provider

    def reset_default_provider(self) -> None:
        """Reset back to the default lazy sentence-transformers adapter."""
        self._provider = SentenceTransformerAdapter()

    def compute_similarity(
        self,
        text_a: str,
        text_b: str,
        prefer_semantic: bool = True,
    ) -> Tuple[float, str, bool, Optional[str]]:
        """Compute textual similarity, returning (similarity_score, mode, is_fallback, fallback_reason).

        Modes:
            - 'semantic': successfully computed via neural sentence embeddings.
            - 'lexical_fallback': semantic requested but unavailable, safely defaulted to TF-IDF.
            - 'lexical': lexical explicitly requested.
        """
        if prefer_semantic:
            if self._provider.is_available():
                try:
                    sim = self._provider.compute_similarity(text_a, text_b)
                    return sim, "semantic", False, None
                except Exception as exc:
                    reason = f"Semantic model inference failed ({type(exc).__name__}); falling back to TF-IDF"
                    fallback_sim = compute_tfidf_similarity(text_a, text_b)
                    return fallback_sim, "lexical_fallback", True, reason
            else:
                # Attempt lazy load
                if hasattr(self._provider, "load_model") and callable(self._provider.load_model):
                    loaded = self._provider.load_model()
                    if loaded:
                        try:
                            sim = self._provider.compute_similarity(text_a, text_b)
                            return sim, "semantic", False, None
                        except Exception as exc:
                            reason = f"Semantic inference failed after load ({type(exc).__name__}); falling back to TF-IDF"
                            fallback_sim = compute_tfidf_similarity(text_a, text_b)
                            return fallback_sim, "lexical_fallback", True, reason

                # Provider unavailable -> transparent fallback
                last_error = getattr(self._provider, "_load_error", None)
                reason = (
                    f"SentenceTransformer '{self._provider.get_model_name()}' unavailable "
                    f"({last_error or 'weights not loaded; offline mode'}); using deterministic TF-IDF fallback"
                )
                fallback_sim = compute_tfidf_similarity(text_a, text_b)
                return fallback_sim, "lexical_fallback", True, reason
        else:
            lexical_sim = compute_tfidf_similarity(text_a, text_b)
            return lexical_sim, "lexical", True, "Lexical TF-IDF explicitly requested"

    def get_status(self) -> dict:
        """Diagnostic state inspection for health and administrative transparency."""
        is_avail = self._provider.is_available()
        return {
            "is_available": is_avail,
            "model_name": self._provider.get_model_name(),
            "provider_type": type(self._provider).__name__,
            "fallback_mode": not is_avail,
            "last_error": getattr(self._provider, "_load_error", None),
        }


# Global singleton instance
semantic_manager = SemanticSimilarityManager()

