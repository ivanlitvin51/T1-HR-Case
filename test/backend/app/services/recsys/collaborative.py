import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.sparse import csr_matrix

logger = logging.getLogger(__name__)

ACTION_WEIGHTS = {
    "invite": 5.0,
    "like": 2.5,
    "view": 1.0,
    "reject": -1.5,
    "instant_reject": -3.5,
}

class ALSEngine:
    _instance = None
    _model = None
    _vacancy_to_idx: Dict[int, int] = {}
    _idx_to_vacancy: Dict[int, int] = {}
    _candidate_to_idx: Dict[int, int] = {}
    _idx_to_candidate: Dict[int, int] = {}
    _is_trained: bool = False
    _direct_feedback: Dict[Tuple[int, int], float] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ALSEngine()
        return cls._instance

    def record_direct_feedback(self, vacancy_id: int, candidate_id: int, weight: float):
        """Мгновенная онлайн-корректировка скоринга при действии HR"""
        key = (vacancy_id, candidate_id)
        self._direct_feedback[key] = self._direct_feedback.get(key, 0.0) + weight
        logger.info(f"Recorded online feedback for pair {key}: cumulative weight = {self._direct_feedback[key]}")

    def reset(self):
        """Сброс обученной модели ALS и очистка матриц"""
        self._model = None
        self._vacancy_to_idx.clear()
        self._idx_to_vacancy.clear()
        self._candidate_to_idx.clear()
        self._idx_to_candidate.clear()
        self._direct_feedback.clear()
        self._is_trained = False
        logger.info("ALSEngine state and online feedback have been reset.")

    def fit(self, interactions: List[Tuple[int, int, float]]):
        """
        interactions: список кортежей (vacancy_id, candidate_id, weight)
        Строит разреженную матрицу (вакансии x кандидаты) и обучает ALS
        """
        if len(interactions) < 3:
            logger.info("Not enough interactions for ALS training (< 3). Skipping.")
            self._is_trained = False
            return

        try:
            from implicit.als import AlternatingLeastSquares
            
            vacancies = list({item[0] for item in interactions})
            candidates = list({item[1] for item in interactions})

            self._vacancy_to_idx = {v: i for i, v in enumerate(vacancies)}
            self._idx_to_vacancy = {i: v for i, v in enumerate(vacancies)}
            self._candidate_to_idx = {c: i for i, c in enumerate(candidates)}
            self._idx_to_candidate = {i: c for i, c in enumerate(candidates)}

            rows = []
            cols = []
            data = []

            for v_id, c_id, weight in interactions:
                # В implicit confidence обычно положительный, смещаем отрицательные веса
                # Либо используем шкалу уверенности (confidence = 1 + alpha * weight)
                shifted_weight = max(0.1, weight + 4.0) 
                rows.append(self._vacancy_to_idx[v_id])
                cols.append(self._candidate_to_idx[c_id])
                data.append(shifted_weight)

            # Строки: вакансии, столбцы: кандидаты
            matrix = csr_matrix((data, (rows, cols)), shape=(len(vacancies), len(candidates)))

            # Обучаем модель ALS для Implicit Feedback
            factors = min(16, min(len(vacancies), len(candidates)))
            model = AlternatingLeastSquares(factors=factors, regularization=0.05, iterations=15, random_state=42)
            model.fit(matrix)

            self._model = model
            self._is_trained = True
            logger.info(f"ALS successfully trained on {len(interactions)} interactions.")
        except Exception as e:
            logger.error(f"Error training ALS model: {e}")
            self._is_trained = False

    def predict_score(self, vacancy_id: int, candidate_id: int) -> Tuple[Optional[float], float]:
        """
        Возвращает (collaborative_score, confidence_weight).
        1) Мгновенно учитывает действия HR (онлайн-фидбек) через логистическую сигмоиду.
        2) Если обучена матрица ALS, комбинирует ее скрытые факторы.
        """
        pair_key = (vacancy_id, candidate_id)
        has_direct = pair_key in self._direct_feedback
        direct_w = self._direct_feedback.get(pair_key, 0.0)

        als_factor_score = None
        if self._is_trained and self._model is not None:
            if vacancy_id in self._vacancy_to_idx and candidate_id in self._candidate_to_idx:
                try:
                    v_idx = self._vacancy_to_idx[vacancy_id]
                    c_idx = self._candidate_to_idx[candidate_id]
                    v_factors = self._model.user_factors[v_idx]
                    c_factors = self._model.item_factors[c_idx]
                    raw_score = float(np.dot(v_factors, c_factors))
                    als_factor_score = 1.0 / (1.0 + np.exp(-raw_score))
                except Exception as e:
                    logger.error(f"Error computing ALS dot product: {e}")

        if has_direct:
            # Преобразуем накопленный вес через сигмоиду:
            # +5.0 (invite) -> ~0.92, +2.5 (like) -> ~0.78, -1.5 (reject) -> ~0.32, -3.5 (instant reject) -> ~0.15
            direct_score = 1.0 / (1.0 + np.exp(-direct_w / 2.0))
            if als_factor_score is not None:
                final_collab = 0.7 * direct_score + 0.3 * als_factor_score
            else:
                final_collab = direct_score
            return float(final_collab), 0.35

        elif als_factor_score is not None:
            return float(als_factor_score), 0.35

        return None, 0.0
