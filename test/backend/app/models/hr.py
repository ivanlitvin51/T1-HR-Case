from datetime import datetime
from typing import List, Optional
from sqlalchemy import Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.config import settings

class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    min_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Sentence-transformer vector embedding
    embedding = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interactions: Mapped[List["HRInteraction"]] = relationship("HRInteraction", back_populates="vacancy", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)  # Желаемая должность
    bio: Mapped[str] = mapped_column(Text)                       # Текст резюме
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    expected_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Ссылка на сырой JSON в MongoDB (после парсинга)
    raw_doc_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Sentence-transformer vector embedding
    embedding = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interactions: Mapped[List["HRInteraction"]] = relationship("HRInteraction", back_populates="candidate", cascade="all, delete-orphan")


class HRInteraction(Base):
    __tablename__ = "hr_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey("vacancies.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    
    # 'view', 'like', 'invite', 'reject', 'instant_reject'
    action: Mapped[str] = mapped_column(String(50))
    # Вес для ALS implicit feedback: invite = 5.0, like = 2.0, view = 1.0, reject = -1.0, instant_reject = -3.0
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="interactions")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="interactions")
