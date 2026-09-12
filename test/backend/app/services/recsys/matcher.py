import math
from typing import List, Tuple
from app.models.hr import Vacancy, Candidate
from app.schemas.hr import MatchResultItem, MatchScoreBreakdown, CandidateOut
from app.services.recsys.collaborative import ALSEngine

class HybridMatcher:

    @staticmethod
    def calculate_vector_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Косинусное сходство между двумя эмбеддингами"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.5
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0 or norm_b == 0:
            return 0.5
        cosine = dot / (norm_a * norm_b)
        # Приводим [-1, 1] к [0, 1]
        return max(0.0, min(1.0, (cosine + 1.0) / 2.0))

    @staticmethod
    def calculate_skills_ratio(vacancy_skills: List[str], candidate_skills: List[str]) -> float:
        """Пересечение требуемых хард/софт скиллов"""
        if not vacancy_skills:
            return 1.0
        if not candidate_skills:
            return 0.0

        v_set = {s.strip().lower() for s in vacancy_skills if s}
        c_set = {s.strip().lower() for s in candidate_skills if s}

        matched = v_set.intersection(c_set)
        return len(matched) / len(v_set)

    @staticmethod
    def calculate_experience_score(required_exp: float, candidate_exp: float) -> float:
        """Оценка соответствия опыта (штраф за недостаток опыта, умеренный бонус за превышение)"""
        if required_exp <= 0:
            return 1.0
        diff = candidate_exp - required_exp
        if diff >= 0:
            return min(1.0, 0.9 + 0.1 * min(diff / 3.0, 1.0))
        else:
            # Недобор опыта: например если надо 3 года, а есть 1.5 года -> 0.5
            return max(0.2, 1.0 + (diff / required_exp) * 0.7)

    @staticmethod
    def calculate_salary_fit(min_sal: float, max_sal: float, expected_sal: float) -> float:
        """Оценка соответствия зарплатных ожиданий"""
        if not expected_sal or (not min_sal and not max_sal):
            return 1.0  # Нейтрально, если вилка не указана

        upper_bound = max_sal or (min_sal * 1.3)
        lower_bound = min_sal or (max_sal * 0.7)

        if lower_bound <= expected_sal <= upper_bound:
            return 1.0
        elif expected_sal < lower_bound:
            return 0.95  # Кандидат просит меньше вилки — отлично
        else:
            # Просит больше вилки: штрафуем пропорционально превышению
            excess = (expected_sal - upper_bound) / upper_bound
            return max(0.1, 1.0 - excess)

    @classmethod
    def score_candidate(cls, vacancy: Vacancy, candidate: Candidate) -> MatchResultItem:
        # 1. Сходство эмбеддингов
        vec_sim = cls.calculate_vector_similarity(vacancy.embedding, candidate.embedding)

        # 2. Пересечение скиллов
        skills_ratio = cls.calculate_skills_ratio(vacancy.skills or [], candidate.skills or [])

        # 3. Опыт
        exp_score = cls.calculate_experience_score(vacancy.experience_years or 0.0, candidate.experience_years or 0.0)

        # 4. Зарплатный фит
        salary_fit = cls.calculate_salary_fit(vacancy.min_salary, vacancy.max_salary, candidate.expected_salary)

        # 5. Итоговый Content-Based скор (веса эвристик)
        content_score = (
            0.45 * vec_sim +
            0.30 * skills_ratio +
            0.15 * exp_score +
            0.10 * salary_fit
        )

        # 6. Коллаборативный скор (ALS implicit feedback)
        als_engine = ALSEngine.get_instance()
        als_score, als_weight = als_engine.predict_score(vacancy.id, candidate.id)

        # 7. Финальный гибридный скоринг с правильным Boost / Penalty
        if als_score is not None and als_weight > 0:
            if als_score >= 0.5:
                # Положительное действие (Приглашение, Шорт-лист):
                # Гарантированно увеличивает скоринг кандидата (бонус к оставшемуся запасу до 100%)
                boost_factor = (als_score - 0.5) / 0.5  # от 0.0 до 1.0
                final_score = content_score + (1.0 - content_score) * (boost_factor * 0.75)
            else:
                # Отрицательное действие (Отказ, Инста-отказ):
                # Гарантированно снижает скоринг пропорционально штрафу
                penalty_factor = (0.5 - als_score) / 0.5  # от 0.0 до 1.0
                final_score = content_score * (1.0 - penalty_factor * 0.45)
            final_score = max(0.01, min(1.0, final_score))
        else:
            final_score = content_score
            als_weight = 0.0

        breakdown = MatchScoreBreakdown(
            vector_similarity=round(vec_sim, 4),
            skills_match_ratio=round(skills_ratio, 4),
            experience_match=round(exp_score, 4),
            salary_fit=round(salary_fit, 4),
            content_score=round(content_score, 4),
            collaborative_score=round(als_score, 4) if als_score is not None else None,
            collaborative_weight=round(als_weight, 2)
        )

        return MatchResultItem(
            candidate=CandidateOut.model_validate(candidate),
            final_score=round(final_score, 4),
            breakdown=breakdown
        )
