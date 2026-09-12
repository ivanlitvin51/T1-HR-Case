import React, { useState, useEffect } from 'react';

export default function App() {
  const [vacancies, setVacancies] = useState([]);
  const [selectedVacancy, setSelectedVacancy] = useState(null);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const API_BASE = '/api/v1';

  // Загрузка списка вакансий
  const fetchVacancies = async () => {
    try {
      const res = await fetch(`${API_BASE}/vacancies/`);
      const data = await res.json();
      setVacancies(data);
      if (data.length > 0 && !selectedVacancy) {
        setSelectedVacancy(data[0]);
      }
    } catch (err) {
      console.error('Failed to load vacancies', err);
    }
  };

  // Загрузка подходящих кандидатов для выбранной вакансии
  const fetchMatches = async (vacancyId) => {
    if (!vacancyId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/match/vacancy/${vacancyId}?no_cache=true&_t=${Date.now()}`);
      const data = await res.json();
      setMatches(data.matches || []);
    } catch (err) {
      console.error('Failed to load matches', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVacancies();
  }, []);

  useEffect(() => {
    if (selectedVacancy) {
      fetchMatches(selectedVacancy.id);
    }
  }, [selectedVacancy]);

  // Сидирование тестовых данных
  const handleSeedDemoData = async () => {
    setStatusMsg('Генерация демо-данных...');
    try {
      const res = await fetch('/seed-demo-data', { method: 'POST' });
      await res.json();
      setStatusMsg('Демо-данные успешно созданы!');
      await fetchVacancies();
      setTimeout(() => setStatusMsg(''), 4000);
    } catch (err) {
      setStatusMsg('Ошибка сидирования данных');
    }
  };

  const actionLabels = {
    invite: 'Приглашен на интервью (+5)',
    like: 'Добавлен в шорт-лист (+2.5)',
    reject: 'Отказ (-1.5)',
    instant_reject: 'Быстрый инста-отказ (-3.5)',
  };

  // Запись действия HR (Implicit Feedback для ALS)
  const handleInteraction = async (candidateId, action) => {
    if (!selectedVacancy) return;
    try {
      const res = await fetch(`${API_BASE}/interactions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vacancy_id: selectedVacancy.id,
          candidate_id: candidateId,
          action: action,
        }),
      });
      const data = await res.json();
      const label = actionLabels[action] || action;
      setStatusMsg(`Действие сохранено: "${label}"! Скоринг пересчитан.`);
      setTimeout(() => setStatusMsg(''), 3000);
      // Мгновенное обновление скоров в интерфейсе
      await fetchMatches(selectedVacancy.id);
    } catch (err) {
      console.error('Interaction error', err);
    }
  };

  // Сброс истории действий HR и весов ALS
  const handleResetInteractions = async () => {
    setStatusMsg('Сброс действий и весов ALS...');
    try {
      const res = await fetch(`${API_BASE}/interactions/reset`, { method: 'POST' });
      await res.json();
      setStatusMsg('Все действия и ALS веса сброшены к исходным!');
      setTimeout(() => setStatusMsg(''), 3000);
      if (selectedVacancy) {
        await fetchMatches(selectedVacancy.id);
      }
    } catch (err) {
      setStatusMsg('Ошибка при сбросе действий');
    }
  };

  const getScoreColorClass = (score) => {
    if (score >= 0.75) return 'score-high';
    if (score >= 0.5) return 'score-mid';
    return 'score-low';
  };

  return (
    <div className="container">
      <header>
        <div>
          <h1>🎯 T1 HR RecSys Demo</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Гибридный скоринг: Content-Based (эмбеддинги) + Collaborative Filtering (ALS)
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {statusMsg && <span style={{ color: 'var(--accent-green)', fontSize: '13px' }}>{statusMsg}</span>}
          <button className="btn btn-primary" onClick={handleSeedDemoData}>
            ✨ Загрузить демо-данные
          </button>
          <button className="btn" style={{ background: '#475569', color: '#fff' }} onClick={handleResetInteractions}>
            🔄 Сбросить ALS
          </button>
        </div>
      </header>

      <div className="grid-2">
        {/* Левая колонка: Вакансии */}
        <div>
          <h2 style={{ fontSize: '18px', marginBottom: '12px' }}>Активные вакансии</h2>
          {vacancies.length === 0 ? (
            <div className="card" style={{ color: 'var(--text-muted)' }}>
              Нет вакансий. Нажмите "Загрузить демо-данные" выше.
            </div>
          ) : (
            vacancies.map((v) => (
              <div
                key={v.id}
                className="card"
                style={{
                  cursor: 'pointer',
                  borderColor: selectedVacancy?.id === v.id ? 'var(--accent-blue)' : 'var(--border-color)',
                  backgroundColor: selectedVacancy?.id === v.id ? '#1e293b' : '#0f172a',
                }}
                onClick={() => setSelectedVacancy(v)}
              >
                <div style={{ fontWeight: 600, fontSize: '16px', marginBottom: '4px' }}>{v.title}</div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  {v.city || 'Удаленно'} • Опыт от {v.experience_years} лет
                </div>
                <div>
                  {(v.skills || []).map((s, idx) => (
                    <span key={idx} className="tag">{s}</span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Правая колонка: Ранжированные кандидаты */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h2 style={{ fontSize: '18px' }}>
              Ранжированные кандидаты {selectedVacancy ? `под "${selectedVacancy.title}"` : ''}
            </h2>
            {loading && <span style={{ color: 'var(--accent-blue)', fontSize: '13px' }}>Считаем скоринг...</span>}
          </div>

          {matches.length === 0 && !loading ? (
            <div className="card" style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>
              Кандидаты не найдены.
            </div>
          ) : (
            matches.map((item) => {
              const { candidate, final_score, breakdown } = item;
              return (
                <div key={candidate.id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontSize: '18px', fontWeight: 600 }}>{candidate.full_name}</div>
                      <div style={{ color: 'var(--accent-blue)', fontSize: '14px', marginBottom: '4px' }}>
                        {candidate.title} • {candidate.city || 'Любой город'}
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                        Опыт: {candidate.experience_years} лет • ЗП ожидания: {candidate.expected_salary ? `${candidate.expected_salary.toLocaleString()} руб.` : 'Не указана'}
                      </div>
                    </div>
                    <div className={`score-pill ${getScoreColorClass(final_score)}`}>
                      {(final_score * 100).toFixed(1)}% Match
                    </div>
                  </div>

                  <p style={{ fontSize: '13px', margin: '12px 0', color: '#cbd5e1' }}>
                    {candidate.bio}
                  </p>

                  <div style={{ marginBottom: '12px' }}>
                    {(candidate.skills || []).map((s, idx) => (
                      <span key={idx} className="tag">{s}</span>
                    ))}
                  </div>

                  {/* Детализация скоринга (Explainable AI) */}
                  <div style={{ background: '#0f172a', padding: '12px', borderRadius: '8px', marginBottom: '14px' }}>
                    <div className="breakdown-row">
                      <span>Сходство эмбеддингов (Sentence-Transformers):</span>
                      <strong style={{ color: 'var(--text-primary)' }}>{(breakdown.vector_similarity * 100).toFixed(1)}%</strong>
                    </div>
                    <div className="breakdown-row">
                      <span>Совпадение требуемых навыков:</span>
                      <strong style={{ color: 'var(--text-primary)' }}>{(breakdown.skills_match_ratio * 100).toFixed(1)}%</strong>
                    </div>
                    <div className="breakdown-row">
                      <span>Соответствие опыту и грейду:</span>
                      <strong style={{ color: 'var(--text-primary)' }}>{(breakdown.experience_match * 100).toFixed(1)}%</strong>
                    </div>
                    <div className="breakdown-row">
                      <span>Коллаборативный скор (ALS матрица действий):</span>
                      <strong style={{ color: breakdown.collaborative_score !== null ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                        {breakdown.collaborative_score !== null 
                          ? `${(breakdown.collaborative_score * 100).toFixed(1)}% (вес: ${breakdown.collaborative_weight})`
                          : 'Холодный старт (нет истории)'}
                      </strong>
                    </div>
                  </div>

                  {/* Кнопки действий HR (Implicit Feedback) */}
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button className="btn btn-success" onClick={() => handleInteraction(candidate.id, 'invite')}>
                      ✉️ Пригласить на интервью (+5)
                    </button>
                    <button className="btn" style={{ background: '#3b82f6', color: '#fff' }} onClick={() => handleInteraction(candidate.id, 'like')}>
                      👍 В шорт-лист (+2.5)
                    </button>
                    <button className="btn btn-danger" onClick={() => handleInteraction(candidate.id, 'reject')}>
                      ❌ Отказать (-1.5)
                    </button>
                    <button className="btn" style={{ background: '#7f1d1d', color: '#fca5a5' }} onClick={() => handleInteraction(candidate.id, 'instant_reject')}>
                      ⚡ Инста-отказ (-3.5)
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
