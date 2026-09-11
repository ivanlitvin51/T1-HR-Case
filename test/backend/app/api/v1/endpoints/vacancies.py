from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.hr import Vacancy
from app.schemas.hr import VacancyCreate, VacancyOut
from app.services.recsys.embedder import EmbeddingService

router = APIRouter()

@router.post("/", response_model=VacancyOut)
async def create_vacancy(
    vacancy_in: VacancyCreate,
    db: AsyncSession = Depends(get_db)
):
    # Формируем текст описания для Sentence-Transformers
    text_for_embed = EmbeddingService.build_vacancy_text(
        title=vacancy_in.title,
        description=vacancy_in.description,
        skills=vacancy_in.skills,
        experience_years=vacancy_in.experience_years,
        city=vacancy_in.city
    )
    vector = EmbeddingService.text_to_embedding(text_for_embed)

    vacancy = Vacancy(
        title=vacancy_in.title,
        description=vacancy_in.description,
        skills=vacancy_in.skills,
        min_salary=vacancy_in.min_salary,
        max_salary=vacancy_in.max_salary,
        experience_years=vacancy_in.experience_years,
        city=vacancy_in.city,
        embedding=vector
    )
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)
    return vacancy

@router.get("/", response_model=List[VacancyOut])
async def list_vacancies(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Vacancy).offset(skip).limit(limit).order_by(Vacancy.id.desc()))
    return result.scalars().all()

@router.get("/{vacancy_id}", response_model=VacancyOut)
async def get_vacancy(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
    vacancy = result.scalar_one_or_none()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy
