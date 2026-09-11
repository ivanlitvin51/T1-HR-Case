"""
Автономная демонстрация рекомендательной системы (RecSys Engine) T1 HR-Case.
Работает локально на чистом Python без Docker, PostgreSQL и Redis.
"""
import math
import sys
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 1. Веса действий HR для коллаборативной фильтрации (Implicit Feedback)
ACTION_WEIGHTS = {
    "invite": 5.0,           # Приглашен на интервью
    "like": 2.5,             # Добавлен в шорт-лист
    "view": 1.0,             # Просмотр профиля
    "reject": -1.5,          # Обычный отказ
    "instant_reject": -3.5,  # Инста-отказ (< 5 сек)
}

# 2. Модуль эмбеддингов
def generate_text_embedding(text: str, dim: int = 312) -> np.ndarray:
    """Детерминированный вектор на основе текста (симуляция Sentence-Transformers)"""
    np.random.seed(abs(hash(text)) % (2**32))
    vec = np.random.uniform(-1, 1, dim)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    dot = np.dot(v1, v2)
    norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.5
    cos = dot / (norm1 * norm2)
    return float(max(0.0, min(1.0, (cos + 1.0) / 2.0)))

# 3. Content-Based скоринг
def calculate_skills_overlap(v_skills, c_skills):
    if not v_skills:
        return 1.0
    v_set = {s.lower().strip() for s in v_skills}
    c_set = {s.lower().strip() for s in c_skills}
    return len(v_set.intersection(c_set)) / len(v_set)

def calculate_exp_match(req_exp, cand_exp):
    if req_exp <= 0:
        return 1.0
    diff = cand_exp - req_exp
    if diff >= 0:
        return min(1.0, 0.9 + 0.1 * min(diff / 3.0, 1.0))
    return max(0.2, 1.0 + (diff / req_exp) * 0.7)

def calculate_salary_fit(min_s, max_s, exp_s):
    if not exp_s or (not min_s and not max_s):
        return 1.0
    if min_s <= exp_s <= max_s:
        return 1.0
    if exp_s < min_s:
        return 0.95
    excess = (exp_s - max_s) / max_s
    return max(0.1, 1.0 - excess)

# 4. Демо-данные
vacancy = {
    "id": 1,
    "title": "Senior Python Developer",
    "description": "Разработка микросервисов на FastAPI, PostgreSQL, Redis, Docker.",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    "experience_years": 3.0,
    "min_salary": 250000,
    "max_salary": 350000,
}
vacancy["embedding"] = generate_text_embedding(vacancy["title"] + " " + " ".join(vacancy["skills"]))

candidates = [
    {
        "id": 101,
        "name": "Алексей Смирнов",
        "title": "Senior Python Developer",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
        "experience_years": 5.0,
        "expected_salary": 300000,
    },
    {
        "id": 102,
        "name": "Дмитрий Кузнецов",
        "title": "Junior Python Developer",
        "skills": ["Python", "Django", "SQLite"],
        "experience_years": 0.5,
        "expected_salary": 70000,
    },
    {
        "id": 103,
        "name": "Сергей Васильев",
        "title": "Старший Бариста",
        "skills": ["Приготовление кофе", "Касса"],
        "experience_years": 3.0,
        "expected_salary": 60000,
    }
]

for c in candidates:
    c["embedding"] = generate_text_embedding(c["title"] + " " + " ".join(c["skills"]))

def rank_candidates(interactions_dict=None):
    if interactions_dict is None:
        interactions_dict = {}

    results = []
    for c in candidates:
        vec_sim = cosine_similarity(vacancy["embedding"], c["embedding"])
        skills_ratio = calculate_skills_overlap(vacancy["skills"], c["skills"])
        exp_score = calculate_exp_match(vacancy["experience_years"], c["experience_years"])
        sal_score = calculate_salary_fit(vacancy["min_salary"], vacancy["max_salary"], c["expected_salary"])

        # Content-based скор
        content_score = (
            0.45 * vec_sim +
            0.30 * skills_ratio +
            0.15 * exp_score +
            0.10 * sal_score
        )

        # Collaborative / ALS скор
        als_weight = 0.0
        als_score = None
        if c["id"] in interactions_dict:
            act = interactions_dict[c["id"]]
            raw_w = ACTION_WEIGHTS.get(act, 0.0)
            als_score = 1.0 / (1.0 + math.exp(-raw_w / 2.0))
            als_weight = 0.35
            final_score = (1.0 - als_weight) * content_score + als_weight * als_score
        else:
            final_score = content_score

        results.append({
            "candidate": c,
            "final_score": final_score,
            "content_score": content_score,
            "als_score": als_score,
            "als_weight": als_weight,
            "vec_sim": vec_sim,
            "skills": skills_ratio,
            "exp": exp_score,
        })

    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results

def print_table(results, title="ТАБЛИЦА РАНЖИРОВАНИЯ"):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print(f"{'Кандидат':<20} | {'Должность':<24} | {'Итого':<8} | {'Content':<8} | {'ALS (CF)':<10}")
    print("-" * 80)
    for r in results:
        cand = r["candidate"]
        als_str = f"{r['als_score']*100:.1f}%" if r["als_score"] is not None else "Холодный"
        print(f"{cand['name']:<20} | {cand['title']:<24} | {r['final_score']*100:5.1f}%  | {r['content_score']*100:5.1f}%  | {als_str:<10}")
    print("=" * 80)

if __name__ == "__main__":
    print("\n--- ЭТАП 1: Исходный скоринг (Холодный старт, чистый Content-Based) ---")
    initial_results = rank_candidates()
    print_table(initial_results, "ИСХОДНЫЙ СКОРИНГ (ДО ВЗАИМОДЕЙСТВИЙ HR)")

    print("\n--- ЭТАП 2: Симуляция действий HR ---")
    print("HR выполнил действия:")
    print("  • Алексей Смирнов  -> Приглашен на интервью (invite: +5.0 баллов)")
    print("  • Сергей Васильев  -> Инста-отказ (instant_reject: -3.5 баллов)")

    interactions = {
        101: "invite",
        103: "instant_reject"
    }

    updated_results = rank_candidates(interactions)
    print_table(updated_results, "ОБНОВЛЕННЫЙ СКОРИНГ (С УЧЕТОМ ALS МАТРИЦЫ)")
