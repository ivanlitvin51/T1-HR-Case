from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Vacancy Schemas ---
class VacancyBase(BaseModel):
    title: str = Field(..., example="Senior Python / FastAPI Developer")
    description: str = Field(..., example="Ищем опытного бэкенд разработчика со знанием FastAPI, PostgreSQL и Docker")
    skills: List[str] = Field(default_factory=list, example=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"])
    min_salary: Optional[float] = Field(None, example=250000)
    max_salary: Optional[float] = Field(None, example=350000)
    experience_years: float = Field(0.0, example=3.0)
    city: Optional[str] = Field(None, example="Москва")

class VacancyCreate(VacancyBase):
    pass

class VacancyOut(VacancyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Candidate Schemas ---
class CandidateBase(BaseModel):
    full_name: str = Field(..., example="Иван Иванов")
    title: str = Field(..., example="Python Backend Developer")
    bio: str = Field(..., example="Разрабатывал микросервисы на FastAPI, оптимизировал запросы в PostgreSQL, работал с Redis")
    skills: List[str] = Field(default_factory=list, example=["Python", "FastAPI", "PostgreSQL", "Git"])
    expected_salary: Optional[float] = Field(None, example=280000)
    experience_years: float = Field(0.0, example=4.0)
    city: Optional[str] = Field(None, example="Москва")
    raw_doc_id: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateOut(CandidateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- HR Interaction Schemas ---
class HRInteractionCreate(BaseModel):
    vacancy_id: int
    candidate_id: int
    action: str = Field(..., example="invite", description="view, like, invite, reject, instant_reject")

class HRInteractionOut(BaseModel):
    id: int
    vacancy_id: int
    candidate_id: int
    action: str
    weight: float
    created_at: datetime

    class Config:
        from_attributes = True


# --- Matching & RecSys Schemas ---
class MatchScoreBreakdown(BaseModel):
    vector_similarity: float
    skills_match_ratio: float
    experience_match: float
    salary_fit: float
    content_score: float
    collaborative_score: Optional[float] = None
    collaborative_weight: float

class MatchResultItem(BaseModel):
    candidate: CandidateOut
    final_score: float
    breakdown: MatchScoreBreakdown

class MatchResponse(BaseModel):
    vacancy_id: int
    total_candidates_analyzed: int
    matches: List[MatchResultItem]
