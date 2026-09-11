from fastapi import APIRouter
from app.api.v1.endpoints import vacancies, candidates, interactions, match

api_router = APIRouter()

api_router.include_router(vacancies.router, prefix="/vacancies", tags=["Vacancies"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
api_router.include_router(interactions.router, prefix="/interactions", tags=["HR Interactions (ALS)"])
api_router.include_router(match.router, prefix="/match", tags=["RecSys Matching"])
