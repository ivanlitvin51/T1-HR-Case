from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any

from app.core.database import get_db
from app.models.hr import Candidate
from app.schemas.hr import CandidateCreate, CandidateOut
from app.services.recsys.embedder import EmbeddingService
from app.services.mongo import MongoService

router = APIRouter()

@router.post("/", response_model=CandidateOut)
async def create_candidate(
    candidate_in: CandidateCreate,
    raw_payload: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    # 1. Сохранение сырого JSON в MongoDB (сырые данные парсинга hh.ru / pdf)
    raw_doc_id = None
    if raw_payload:
        raw_doc_id = await MongoService.save_raw_document("raw_resumes", raw_payload)

    # 2. Вычисление эмбеддинга
    text_for_embed = EmbeddingService.build_candidate_text(
        title=candidate_in.title,
        bio=candidate_in.bio,
        skills=candidate_in.skills,
        experience_years=candidate_in.experience_years,
        city=candidate_in.city
    )
    vector = EmbeddingService.text_to_embedding(text_for_embed)

    # 3. Сохранение структурированных данных и вектора в PostgreSQL
    candidate = Candidate(
        full_name=candidate_in.full_name,
        title=candidate_in.title,
        bio=candidate_in.bio,
        skills=candidate_in.skills,
        expected_salary=candidate_in.expected_salary,
        experience_years=candidate_in.experience_years,
        city=candidate_in.city,
        raw_doc_id=raw_doc_id or candidate_in.raw_doc_id,
        embedding=vector
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate

@router.get("/", response_model=List[CandidateOut])
async def list_candidates(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Candidate).offset(skip).limit(limit).order_by(Candidate.id.desc()))
    return result.scalars().all()

@router.get("/{candidate_id}", response_model=CandidateOut)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@router.get("/{candidate_id}/raw")
async def get_candidate_raw(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение оригинального распарсенного JSON из MongoDB"""
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate or not candidate.raw_doc_id:
        raise HTTPException(status_code=404, detail="Raw document not found")
    
    doc = await MongoService.get_raw_document("raw_resumes", candidate.raw_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document in MongoDB not found")
    return doc
