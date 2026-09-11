import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.config import settings
from app.models.hr import Vacancy, Candidate
from app.schemas.hr import MatchResponse, MatchResultItem
from app.services.recsys.matcher import HybridMatcher

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_redis_client():
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return None

@router.get("/vacancy/{vacancy_id}", response_model=MatchResponse)
async def match_candidates_for_vacancy(
    vacancy_id: int,
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    no_cache: bool = Query(False, description="Игнорировать Redis кэш"),
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"match_v1:vacancy:{vacancy_id}:limit:{limit}:min_score:{min_score}"
    redis_client = await get_redis_client()

    # 1. Проверяем Redis кэш
    if redis_client and not no_cache:
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return MatchResponse.model_validate_json(cached_data)
        except Exception as e:
            logger.warning(f"Redis get cache error: {e}")

    # 2. Получаем вакансию
    v_res = await db.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
    vacancy = v_res.scalar_one_or_none()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    # 3. Получаем всех кандидатов (в будущем можно делать векторный pre-filtering через pgvector)
    c_res = await db.execute(select(Candidate))
    candidates = c_res.scalars().all()

    # 4. Скоринг через Hybrid RecSys Engine (Content-Based + ALS)
    matched_items: List[MatchResultItem] = []
    for cand in candidates:
        match_item = HybridMatcher.score_candidate(vacancy, cand)
        if match_item.final_score >= min_score:
            matched_items.append(match_item)

    # 5. Сортировка по итоговому скору (от лучших к худшим)
    matched_items.sort(key=lambda x: x.final_score, reverse=True)
    top_matches = matched_items[:limit]

    response = MatchResponse(
        vacancy_id=vacancy_id,
        total_candidates_analyzed=len(candidates),
        matches=top_matches
    )

    # 6. Сохранение в Redis кэш на 60 секунд
    if redis_client:
        try:
            await redis_client.setex(cache_key, 60, response.model_dump_json())
            await redis_client.aclose()
        except Exception as e:
            logger.warning(f"Redis set cache error: {e}")

    return response
