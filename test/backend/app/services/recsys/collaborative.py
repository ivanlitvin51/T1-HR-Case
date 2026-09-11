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

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ALSEngine()
        return cls._instance

    def reset(self):
        """Сброс обученной модели ALS и очистка матриц"""
        self._model = None
        self._vacancy_to_idx.clear()
        self._idx_to_vacancy.clear()
        self._candidate_to_idx.clear()
        self._idx_to_candidate.clear()
        self._is_trained = False
        logger.info("ALSEngine state has been reset.")

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
        Если модели нет или нет данных по паре, возвращает (None, 0.0)
        """
        if not self._is_trained or self._model is None:
            return None, 0.0

        if vacancy_id not in self._vacancy_to_idx or candidate_id not in self._candidate_to_idx:
            # Холодный старт: сущность еще не встречалась в матрице
            return None, 0.0

        try:
            v_idx = self._vacancy_to_idx[vacancy_id]
            c_idx = self._candidate_to_idx[candidate_id]

            v_factors = self._model.user_factors[v_idx]
            c_factors = self._model.item_factors[c_idx]

            # Скалярное произведение скрытых факторов
            raw_score = float(np.dot(v_factors, c_factors))
            # Сигмоида для нормирования в [0, 1]
            norm_score = 1.0 / (1.0 + np.exp(-raw_score))
            
            # Вес влияния ALS (чем больше факторов/взаимодействий, тем выше доверие)
            confidence = 0.35
            return norm_score, confidence
        except Exception as e:
            logger.error(f"Error predicting ALS score: {e}")
            return None, 0.0
