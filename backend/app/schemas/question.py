"""Pydantic data schemas for diagnostic practice questions and topic taxonomy."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


DifficultyLevel = Literal["easy", "medium", "hard"]
QuestionType = Literal["mcq", "code_snippet", "scenario"]


class QuestionOption(BaseModel):
    """A single multiple-choice answer option."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=5, description="Option identifier, e.g. 'A', 'B', 'C', 'D'")
    text: str = Field(..., min_length=1, max_length=1000, description="Option display text")


class QuestionBase(BaseModel):
    """Shared base schema for technical practice questions."""

    topic: str = Field(..., min_length=2, max_length=100, description="Knowledge domain topic, e.g. 'Python', 'SQL'")
    difficulty: DifficultyLevel = Field("medium", description="Question difficulty: easy, medium, or hard")
    question_type: QuestionType = Field("mcq", description="Question format: mcq, code_snippet, scenario")
    prompt: str = Field(..., min_length=10, description="Question scenario or problem statement")
    options: List[QuestionOption] = Field(
        ...,
        min_length=2,
        max_length=6,
        description="List of distinct answer options (typically 4)",
    )


class QuestionCreate(QuestionBase):
    """Schema for authoring/seeding a new practice question with answer key and explanation."""

    answer_key: str = Field(..., min_length=1, max_length=5, description="The ID of the correct option")
    explanation: str = Field(
        ...,
        min_length=10,
        description="Comprehensive educational explanation of the correct answer and distractor rationale",
    )
    rubric_version: str = Field("1.0.0", max_length=50)
    is_synthetic: bool = Field(True, description="True for synthetic/curated benchmark questions")
    is_active: bool = Field(True, description="Whether question is active for practice")

    @model_validator(mode="after")
    def validate_answer_key_in_options(self) -> "QuestionCreate":
        """Verify that answer_key matches one of the provided option IDs."""
        valid_ids = {opt.id.strip().upper() for opt in self.options}
        if self.answer_key.strip().upper() not in valid_ids:
            raise ValueError(
                f"answer_key '{self.answer_key}' must correspond to one of the option IDs: {sorted(list(valid_ids))}"
            )
        # Ensure unique option IDs
        if len(valid_ids) != len(self.options):
            raise ValueError("All question option IDs must be unique.")
        return self


class QuestionUpdate(BaseModel):
    """Schema for updating an existing question."""

    topic: Optional[str] = Field(None, min_length=2, max_length=100)
    difficulty: Optional[DifficultyLevel] = None
    question_type: Optional[QuestionType] = None
    prompt: Optional[str] = Field(None, min_length=10)
    options: Optional[List[QuestionOption]] = Field(None, min_length=2, max_length=6)
    answer_key: Optional[str] = Field(None, min_length=1, max_length=5)
    explanation: Optional[str] = Field(None, min_length=10)
    is_active: Optional[bool] = None


class QuestionPublic(BaseModel):
    """Public delivery schema for active practice sessions.

    Guards answer integrity by strictly omitting answer_key and explanation
    until the user submits an attempt.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    difficulty: str
    question_type: str
    prompt: str
    options: List[QuestionOption]
    created_at: datetime


class QuestionDetail(QuestionPublic):
    """Full detail schema including answer_key and explanation (for authoring or post-submission review)."""

    answer_key: str
    explanation: str
    rubric_version: str
    is_active: bool
    is_synthetic: bool


class TopicSummary(BaseModel):
    """Summary of questions available within a topic domain."""

    topic: str
    total_questions: int
    easy_count: int
    medium_count: int
    hard_count: int


class QuestionListResponse(BaseModel):
    """Paginated collection of public practice questions."""

    items: List[QuestionPublic]
    total: int
    skip: int
    limit: int


class QuestionSeedResponse(BaseModel):
    """Response payload for question bank seed operation."""

    seeded_count: int
    total_count: int
    message: str
