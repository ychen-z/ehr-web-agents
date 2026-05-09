from typing import Literal

from pydantic import BaseModel

ScoreLabel = Literal["Strong", "Adequate", "Moderate", "Limited"]


class JDResult(BaseModel):
    job_title: str
    responsibilities: list[str]
    requirements: list[str]
    interview_focus: list[str]
    selling_points: list[str]


class ScreeningDimension(BaseModel):
    dimension: str
    score: ScoreLabel
    notes: str


class ScreenResumeResult(BaseModel):
    screening_dimensions: list[ScreeningDimension]
    strengths: list[str]
    risks: list[str]
    recommended_next_step: str


class QuestionGroup(BaseModel):
    competency: str
    questions: list[str]


class InterviewQuestionsResult(BaseModel):
    question_groups: list[QuestionGroup]


class InterviewFeedbackResult(BaseModel):
    feedback_summary: str
    evidence: list[str]
    concerns: list[str]
    decision_recommendation: str
