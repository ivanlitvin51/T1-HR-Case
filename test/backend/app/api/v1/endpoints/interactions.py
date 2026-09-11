from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db, async_session_maker
from app.models.hr import HRInteraction
from app.schemas.hr import HRInteractionCreate, HRInteractionOut
from app.services.recsys.collaborative import ALSEngine, ACTION_WEIGHTS

router = APIRouter()

async def retrain_als_background():
    """Фоновое дообучение матрицы ALS при накоплении взаимодействий"""
    async with async_session_maker() as db:
        result = await db.execute(select(HRInteraction.vacancy_id, HRInteraction.candidate_id, HRInteraction.weight))
        rows = result.all()
        interactions = [(r[0], r[1], float(r[2])) for r in rows]
        if len(interactions) >= 3:
            engine = ALSEngine.get_instance()
            engine.fit(interactions)

@router.post("/", response_model=HRInteractionOut)
async def record_interaction(
    interaction_in: HRInteractionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    action_key = interaction_in.action.lower()
    weight = ACTION_WEIGHTS.get(action_key, 1.0)

    interaction = HRInteraction(
        vacancy_id=interaction_in.vacancy_id,
        candidate_id=interaction_in.candidate_id,
        action=action_key,
        weight=weight
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    # Фоновый триггер переобучения ALS
    background_tasks.add_task(retrain_als_background)

    return interaction

@router.get("/", response_model=List[HRInteractionOut])
async def list_interactions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(HRInteraction).offset(skip).limit(limit).order_by(HRInteraction.id.desc()))
    return result.scalars().all()

@router.post("/reset")
async def reset_interactions(
    db: AsyncSession = Depends(get_db)
):
    """Полный сброс всех действий HR и возврат ALS к исходному состоянию"""
    from sqlalchemy import delete
    import redis.asyncio as aioredis
    from app.core.config import settings

    # 1. Удаляем все взаимодействия из БД
    await db.execute(delete(HRInteraction))
    await db.commit()

    # 2. Сбрасываем матрицу и модель ALS в оперативной памяти
    ALSEngine.get_instance().reset()

    # 3. Инвалидируем кэш поисковой выдачи в Redis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        keys = await redis_client.keys("match_v1:*")
        if keys:
            await redis_client.delete(*keys)
        await redis_client.aclose()
    except Exception:
        pass

    return {
        "status": "ok",
        "message": "Все взаимодействия HR и веса ALS успешно сброшены! Скоринг вернулся к исходному Content-Based."
    }

