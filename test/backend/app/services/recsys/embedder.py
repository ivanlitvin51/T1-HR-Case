import logging
import numpy as np
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer model: {settings.EMBEDDING_MODEL}")
                cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                logger.warning(f"Failed to load real SentenceTransformer ({e}). Falling back to dummy embeddings for dev mode.")
                cls._model = "dummy"
        return cls._model

    @classmethod
    def text_to_embedding(cls, text: str) -> List[float]:
        """Генерация эмбеддинга для произвольного текста"""
        model = cls.get_model()
        if model == "dummy":
            # Fallback для быстрого локального теста без скачивания гигабайтов весов
            # Детерминированный псевдо-вектор от хэша текста
            np.random.seed(abs(hash(text)) % (2**32))
            vec = np.random.uniform(-1, 1, settings.EMBEDDING_DIM)
            norm = np.linalg.norm(vec)
            return (vec / norm).tolist() if norm > 0 else vec.tolist()

        try:
            vector = model.encode(text, normalize_embeddings=True)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * settings.EMBEDDING_DIM

    @classmethod
    def build_candidate_text(cls, title: str, bio: str, skills: List[str], experience_years: float, city: Optional[str]) -> str:
        skills_str = ", ".join(skills) if skills else "не указаны"
        return f"Должность: {title}. Опыт: {experience_years} лет. Город: {city or 'не указан'}. Навыки: {skills_str}. Описание: {bio}"

    @classmethod
    def build_vacancy_text(cls, title: str, description: str, skills: List[str], experience_years: float, city: Optional[str]) -> str:
        skills_str = ", ".join(skills) if skills else "не указаны"
        return f"Вакансия: {title}. Требуемый опыт: {experience_years} лет. Город: {city or 'не указан'}. Требуемые навыки: {skills_str}. Описание: {description}"
