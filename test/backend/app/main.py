from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, async_session_maker
from app.api.v1.router import api_router
from app.services.mongo import MongoService
from app.services.recsys.embedder import EmbeddingService
from app.models.hr import Vacancy, Candidate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("hr_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing PostgreSQL schema and pgvector extension...")
    try:
        await init_db()
        logger.info("PostgreSQL and pgvector successfully initialized.")

        # Режим песочницы: сброс накопленных действий HR и весов ALS при перезапуске
        from sqlalchemy import delete
        from app.models.hr import HRInteraction
        from app.services.recsys.collaborative import ALSEngine
        async with async_session_maker() as db:
            await db.execute(delete(HRInteraction))
            await db.commit()
        ALSEngine.get_instance().reset()
        logger.info("Dev sandbox: HR interactions and ALS weights cleared on startup for fresh testing.")
    except Exception as e:
        logger.error(f"Failed to initialize DB: {e}")

    yield

    logger.info("Shutting down services...")
    await MongoService.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="HR-Tech Recommendation System Engine (Content-Based + ALS Collaborative Filtering)",
    lifespan=lifespan
)

# CORS Middleware (для React фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System"])
async def healthcheck():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.post("/seed-demo-data", tags=["System"])
async def seed_demo_data():
    """Быстрое наполнение тестовой БД демонстрационными вакансиями и кандидатами"""
    async with async_session_maker() as db:
        # Создаем тестовую вакансию
        v_text = EmbeddingService.build_vacancy_text(
            title="Senior Python Backend Developer",
            description="Разработка высоконагруженных микросервисов на FastAPI, оптимизация PostgreSQL, работа с Redis и Docker.",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
            experience_years=3.0,
            city="Москва"
        )
        vacancy = Vacancy(
            title="Senior Python Backend Developer",
            description="Разработка высоконагруженных микросервисов на FastAPI, оптимизация PostgreSQL, работа с Redis и Docker.",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
            min_salary=250000,
            max_salary=350000,
            experience_years=3.0,
            city="Москва",
            embedding=EmbeddingService.text_to_embedding(v_text)
        )
        db.add(vacancy)

        # Кандидат 1: Идеальный Python разработчик
        c1_text = EmbeddingService.build_candidate_text(
            title="Senior Python Developer",
            bio="5 лет коммерческого опыта разработки бэкенда на Python, FastAPI, SQLAlchemy, Redis, Docker, PostgreSQL.",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Git"],
            experience_years=5.0,
            city="Москва"
        )
        c1 = Candidate(
            full_name="Алексей Смирнов",
            title="Senior Python Developer",
            bio="5 лет коммерческого опыта разработки бэкенда на Python, FastAPI, SQLAlchemy, Redis, Docker, PostgreSQL.",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Git"],
            expected_salary=300000,
            experience_years=5.0,
            city="Москва",
            embedding=EmbeddingService.text_to_embedding(c1_text)
        )
        db.add(c1)

        # Кандидат 2: Начинающий джуниор разработчик
        c2_text = EmbeddingService.build_candidate_text(
            title="Junior Python Developer",
            bio="Выпускник курсов, делал учебные пет-проекты на Django и SQLite, учу FastAPI и Docker.",
            skills=["Python", "Django", "SQLite", "Git"],
            experience_years=0.5,
            city="Санкт-Петербург"
        )
        c2 = Candidate(
            full_name="Дмитрий Кузнецов",
            title="Junior Python Developer",
            bio="Выпускник курсов, делал учебные пет-проекты на Django и SQLite, учу FastAPI и Docker.",
            skills=["Python", "Django", "SQLite", "Git"],
            expected_salary=70000,
            experience_years=0.5,
            city="Санкт-Петербург",
            embedding=EmbeddingService.text_to_embedding(c2_text)
        )
        db.add(c2)

        # Кандидат 3: Бариста / Непрофильный
        c3_text = EmbeddingService.build_candidate_text(
            title="Старший Бариста / Администратор кофейни",
            bio="Умею варить эспрессо, настраивать помол, обучать персонал, вести учет расходников и кассу.",
            skills=["Приготовление кофе", "Клиентский сервис", "Кассовая дисциплина"],
            experience_years=3.0,
            city="Москва"
        )
        c3 = Candidate(
            full_name="Сергей Васильев",
            title="Старший Бариста",
            bio="Умею варить эспрессо, настраивать помол, обучать персонал, вести учет расходников и кассу.",
            skills=["Приготовление кофе", "Клиентский сервис", "Кассовая дисциплина"],
            expected_salary=60000,
            experience_years=3.0,
            city="Москва",
            embedding=EmbeddingService.text_to_embedding(c3_text)
        )
        db.add(c3)

        await db.commit()
        return {"status": "ok", "message": "Demo data seeded successfully!"}
