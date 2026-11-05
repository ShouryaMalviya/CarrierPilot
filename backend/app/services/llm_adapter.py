"""Optional LLM provider adapter with safety filters, prompt injection guards, and deterministic fallback."""

from abc import ABC, abstractmethod
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.interview import INTERVIEW_ETHICAL_DISCLAIMER
from app.schemas.rubric import DimensionScore, RubricFeedback
from app.services import rubric_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Known prompt injection and system override signatures
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|directions|prompts|rules)",
    r"(?i)disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|directions|prompts|rules)",
    r"(?i)forget\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|directions)",
    r"(?i)you\s+are\s+now\s+(?:in\s+)?(?:developer\s+mode|dan|unfiltered|jailbroken)",
    r"(?i)system\s*:\s*(?:you\s+are|override|give)",
    r"(?i)<system>.*?</system>",
    r"(?i)\[system\].*?\[/system\]",
    r"(?i)give\s+(?:me|this\s+candidate|the\s+user)\s+(?:a\s+score\s+of\s+)?(?:100|maximum|perfect)",
    r"(?i)you\s+must\s+award\s+(?:100|20|maximum)",
    r"(?i)bypass\s+(?:all\s+)?(?:safety|content|rubric)\s+(?:filters|evaluations)",
]


def sanitize_response_text(user_response: str) -> Tuple[str, bool, List[str]]:
    """Sanitize user response, detect adversarial prompt-injection patterns, and neutralize overrides.

    Returns:
        (sanitized_text, injection_detected, detected_patterns)
    """
    clean_text = user_response.strip()
    detected_patterns: List[str] = []

    for pattern in PROMPT_INJECTION_PATTERNS:
        matches = re.findall(pattern, clean_text)
        if matches:
            detected_patterns.extend(matches)
            # Neutralize the matched injection attempt
            clean_text = re.sub(pattern, "[POTENTIAL_INJECTION_NEUTRALIZED]", clean_text)

    injection_detected = len(detected_patterns) > 0
    return clean_text, injection_detected, detected_patterns


def validate_and_bound_feedback(
    feedback: RubricFeedback,
    user_response: str,
) -> RubricFeedback:
    """Enforce strict bounding, verify quote citations, and validate ethical disclaimers on model output."""
    bounded_dimensions: Dict[str, DimensionScore] = {}

    for dim_key, dim_score in feedback.dimension_scores.items():
        # Clamp dimension score to [0.0, 20.0]
        clamped_score = round(max(0.0, min(20.0, float(dim_score.score))), 1)

        # Verify positive evidence quotes exist in the user's response
        verified_evidence: List[str] = []
        resp_lower = user_response.lower()
        for quote in dim_score.positive_evidence:
            clean_quote = quote.rstrip(".").strip().lower()
            if clean_quote in resp_lower or any(word in resp_lower for word in clean_quote.split() if len(word) > 4):
                verified_evidence.append(quote)

        bounded_dimensions[dim_key] = DimensionScore(
            dimension=dim_score.dimension,
            label=dim_score.label,
            score=clamped_score,
            max_score=20.0,
            feedback=dim_score.feedback,
            positive_evidence=verified_evidence,
        )

    # Recompute total score from bounded dimensions
    total_score = round(sum(d.score for d in bounded_dimensions.values()), 1)
    total_score = max(0.0, min(100.0, total_score))

    return RubricFeedback(
        rubric_version=feedback.rubric_version,
        total_score=total_score,
        dimension_scores=bounded_dimensions,
        key_concepts_covered=feedback.key_concepts_covered,
        key_concepts_missed=feedback.key_concepts_missed,
        positive_highlights=feedback.positive_highlights,
        actionable_improvements=feedback.actionable_improvements,
        summary=feedback.summary,
        disclaimer=INTERVIEW_ETHICAL_DISCLAIMER,
    )


# ==============================================================================
# Adapter Interface and Implementations
# ==============================================================================

class BaseLLMAdapter(ABC):
    """Abstract base class for mock interview coaching evaluation adapters."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider is currently configured and operational."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Unique provider identifier (e.g. 'local', 'openai', 'anthropic', 'mock')."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Underlying model identifier."""
        pass

    @abstractmethod
    def evaluate_response(
        self,
        question_text: str,
        user_response: str,
        role: str,
        competency: str,
        key_concepts: List[str],
    ) -> RubricFeedback:
        """Evaluate candidate response according to the 5-dimension coaching rubric."""
        pass


class LocalDeterministicAdapter(BaseLLMAdapter):
    """Deterministic, 100% offline fallback adapter using rubric heuristic analysis."""

    def is_available(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "local"

    def get_model_name(self) -> str:
        return "deterministic-rubric-v1"

    def evaluate_response(
        self,
        question_text: str,
        user_response: str,
        role: str,
        competency: str,
        key_concepts: List[str],
    ) -> RubricFeedback:
        return rubric_service.evaluate_response(
            question_text=question_text,
            user_response=user_response,
            role=role,
            competency=competency,
            key_concepts=key_concepts,
        )


class MockLLMAdapter(BaseLLMAdapter):
    """Configurable mock adapter for testing LLM pathways, injection safety, and error handling."""

    def __init__(
        self,
        canned_feedback: Optional[RubricFeedback] = None,
        raise_error: Optional[Exception] = None,
        simulate_invalid_json: bool = False,
        provider_name: str = "mock-openai",
        model_name: str = "mock-gpt-4o",
    ):
        self._canned_feedback = canned_feedback
        self._raise_error = raise_error
        self._simulate_invalid_json = simulate_invalid_json
        self._provider_name = provider_name
        self._model_name = model_name
        self._calls: List[Dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return self._provider_name

    def get_model_name(self) -> str:
        return self._model_name

    def evaluate_response(
        self,
        question_text: str,
        user_response: str,
        role: str,
        competency: str,
        key_concepts: List[str],
    ) -> RubricFeedback:
        self._calls.append({
            "question_text": question_text,
            "user_response": user_response,
            "role": role,
            "competency": competency,
            "key_concepts": key_concepts,
        })

        if self._raise_error:
            raise self._raise_error

        if self._simulate_invalid_json:
            raise ValidationError.from_exception_data(
                title="MockValidationError",
                line_errors=[],
            )

        if self._canned_feedback:
            return self._canned_feedback

        # Default fallback to deterministic rubric evaluation wrapped in mock
        return rubric_service.evaluate_response(
            question_text=question_text,
            user_response=user_response,
            role=role,
            competency=competency,
            key_concepts=key_concepts,
        )


# ==============================================================================
# LLM Provider Manager with Resilient Fallback
# ==============================================================================

class LLMProviderManager:
    """Manages LLM providers with prompt safety checks and deterministic local fallback."""

    def __init__(self):
        self._fallback_adapter = LocalDeterministicAdapter()
        self._adapter: BaseLLMAdapter = self._init_default_adapter()

    def _init_default_adapter(self) -> BaseLLMAdapter:
        """Initialize provider based on application configuration."""
        if settings.AI_PROVIDER == "local" or not settings.AI_API_KEY:
            return self._fallback_adapter
        # When an external key is configured, could instantiate remote adapter;
        # defaults to fallback if not supported
        return self._fallback_adapter

    def get_adapter(self) -> BaseLLMAdapter:
        return self._adapter

    def set_adapter(self, adapter: BaseLLMAdapter) -> None:
        """Swap active adapter (useful for testing or runtime provider selection)."""
        self._adapter = adapter

    def reset_default_adapter(self) -> None:
        """Reset to the default configured adapter."""
        self._adapter = self._init_default_adapter()

    def evaluate(
        self,
        question_text: str,
        user_response: str,
        role: str = "Full-Stack Engineer",
        competency: str = "System Design",
        key_concepts: Optional[List[str]] = None,
    ) -> Tuple[RubricFeedback, str, bool, Optional[str]]:
        """Evaluate response with prompt injection defense, schema validation, and fallback.

        Returns:
            (RubricFeedback, provider_name_used, is_fallback, fallback_reason)
        """
        expected_concepts = key_concepts or []

        # 1. Sanitize input and detect prompt-injection attempts
        sanitized_text, injection_detected, patterns = sanitize_response_text(user_response)
        if injection_detected:
            logger.warning(
                "Potential prompt-injection detected in candidate response: %s",
                patterns,
            )

        # 2. Check if active adapter is non-local and available
        adapter = self._adapter
        is_external = adapter.get_provider_name() != "local"

        if is_external and adapter.is_available():
            try:
                raw_feedback = adapter.evaluate_response(
                    question_text=question_text,
                    user_response=sanitized_text,
                    role=role,
                    competency=competency,
                    key_concepts=expected_concepts,
                )
                # Enforce bounds and verify quotes against actual candidate response
                validated_feedback = validate_and_bound_feedback(raw_feedback, user_response)
                return validated_feedback, adapter.get_provider_name(), False, None
            except Exception as exc:
                reason = f"Provider '{adapter.get_provider_name()}' failed ({type(exc).__name__}: {str(exc)}); fell back to local deterministic rubric"
                logger.warning(reason)
                # Fall back safely to local deterministic rubric
                fallback_feedback = self._fallback_adapter.evaluate_response(
                    question_text=question_text,
                    user_response=user_response,
                    role=role,
                    competency=competency,
                    key_concepts=expected_concepts,
                )
                return fallback_feedback, "local", True, reason

        # 3. Local deterministic evaluation (default)
        feedback = self._fallback_adapter.evaluate_response(
            question_text=question_text,
            user_response=user_response,
            role=role,
            competency=competency,
            key_concepts=expected_concepts,
        )
        return feedback, "local", False, None

    def get_status(self) -> Dict[str, Any]:
        """Telemetry status of the LLM provider system."""
        adapter = self._adapter
        return {
            "active_provider": adapter.get_provider_name(),
            "model_name": adapter.get_model_name(),
            "is_available": adapter.is_available(),
            "fallback_adapter": self._fallback_adapter.get_provider_name(),
            "fallback_model": self._fallback_adapter.get_model_name(),
            "configured_ai_provider": settings.AI_PROVIDER,
            "has_api_key": bool(settings.AI_API_KEY),
        }


# Global singleton manager instance
llm_manager = LLMProviderManager()
