import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import api, { getErrorMessage } from '../api/client';
import PerfumeCard from '../components/PerfumeCard';
import type { RecommendationResponse } from '../types';

const POPULAR_NOTES = [
  { id: 'marino', label: 'Marino / Acuático', icon: '🌊' },
  { id: 'salado', label: 'Salado', icon: '🧂' },
  { id: 'fresco', label: 'Fresco / Limpio', icon: '🍃' },
  { id: 'citrico', label: 'Cítrico / Bergamota', icon: '🍋' },
  { id: 'vainilla', label: 'Vainilla / Dulce', icon: '🍦' },
  { id: 'cedro', label: 'Maderas / Cedro', icon: '🌲' },
  { id: 'sandalo', label: 'Sándalo', icon: '🪵' },
  { id: 'lavanda', label: 'Lavanda', icon: '🪻' },
  { id: 'cuero', label: 'Cuero', icon: '👞' },
  { id: 'cafe', label: 'Café', icon: '☕' },
  { id: 'canela', label: 'Canela / Especias', icon: '🍂' },
  { id: 'facil de gustar', label: 'Fácil de gustar', icon: '✨' },
];

const FAMILIES = [
  { id: 'CITRUS', label: 'Cítrica', icon: '🍋', desc: 'Fresca, chispeante, energizante' },
  { id: 'WOODY', label: 'Amaderada', icon: '🌲', desc: 'Cedro, vetiver, sándalo, sobria' },
  { id: 'FLORAL', label: 'Floral', icon: '🌸', desc: 'Rosas, jazmín, flores blancas' },
  { id: 'AMBERY (ORIENTAL)', label: 'Oriental / Ámbar', icon: '🔥', desc: 'Cálida, envolvente, vainilla y especias' },
  { id: 'AROMATIC FOUGERE', label: 'Aromática / Fougère', icon: '🌿', desc: 'Lavanda, hierbas, clásica y limpia' },
  { id: 'CHYPRE', label: 'Chipre', icon: '🍂', desc: 'Musgo, bergamota, terrosa y refinada' },
  { id: 'LEATHER', label: 'Cuero', icon: '👞', desc: 'Intensa, ahumada y distintiva' },
];

const CACHE_KEY = 'perfume_advisor_recommendations_cache';

interface RecommendationsCache {
  step: 1 | 2 | 3;
  selectedNotes: string[];
  selectedFamily: string;
  consulta: string;
  gender: 'Todos' | 'Hombre' | 'Mujer' | 'Unisex';
  topK: number;
  result: RecommendationResponse | null;
}

function loadCache(): RecommendationsCache | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export default function Recommendations() {
  const cached = loadCache();

  const [step, setStep] = useState<1 | 2 | 3>(cached?.step ?? 1);
  const [selectedNotes, setSelectedNotes] = useState<string[]>(cached?.selectedNotes ?? []);
  const [selectedFamily, setSelectedFamily] = useState<string>(cached?.selectedFamily ?? '');
  const [consulta, setConsulta] = useState(cached?.consulta ?? '');
  const [gender, setGender] = useState<'Todos' | 'Hombre' | 'Mujer' | 'Unisex'>(cached?.gender ?? 'Todos');
  const [topK, setTopK] = useState(cached?.topK ?? 10);
  const [result, setResult] = useState<RecommendationResponse | null>(cached?.result ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Persistir en sessionStorage cada vez que el usuario modifica algo
  useEffect(() => {
    try {
      const payload: RecommendationsCache = {
        step,
        selectedNotes,
        selectedFamily,
        consulta,
        gender,
        topK,
        result,
      };
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload));
    } catch {
      // Ignorar quota errors
    }
  }, [step, selectedNotes, selectedFamily, consulta, gender, topK, result]);

  function handleReset() {
    sessionStorage.removeItem(CACHE_KEY);
    setStep(1);
    setSelectedNotes([]);
    setSelectedFamily('');
    setConsulta('');
    setGender('Todos');
    setTopK(10);
    setResult(null);
    setError('');
  }

  function toggleNote(id: string) {
    setSelectedNotes((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }

  function buildFullQuery(): string {
    const parts: string[] = [];
    if (selectedFamily) {
      parts.push(selectedFamily.toLowerCase());
    }
    if (selectedNotes.length > 0) {
      parts.push(selectedNotes.join(' '));
    }
    if (consulta.trim()) {
      parts.push(consulta.trim());
    }
    return parts.join(' ').trim();
  }

  async function handleRecommend(event?: FormEvent) {
    if (event) event.preventDefault();

    const fullQuery = buildFullQuery();
    if (!fullQuery) {
      setError('Por favor selecciona alguna nota, familia o escribe una descripción.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const { data } = await api.post('/recommendations', {
        consulta: fullQuery,
        topK,
        gender,
      });
      setResult(data);
    } catch (err) {
      setError(getErrorMessage(err));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Asistente Inteligente</p>
          <h1>Recomendaciones de Perfumes</h1>
          <p className="subtitle">
            Flujo guiado paso a paso para encontrar tu fragancia ideal.
          </p>
        </div>
        {(result || selectedNotes.length > 0 || selectedFamily || consulta) && (
          <button type="button" className="btn btn-ghost" onClick={handleReset}>
            ↺ Nueva búsqueda
          </button>
        )}
      </div>

      <div className="wizard-container">
        {/* Stepper bar */}
        <div className="wizard-steps">
          <button
            type="button"
            className={`wizard-step-indicator ${step === 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}
            onClick={() => setStep(1)}
          >
            <span className="wizard-step-badge">1</span>
            <span>Notas & Acordes</span>
          </button>
          <div className="wizard-step-line" />
          <button
            type="button"
            className={`wizard-step-indicator ${step === 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}
            onClick={() => setStep(2)}
          >
            <span className="wizard-step-badge">2</span>
            <span>Familia Olfativa</span>
          </button>
          <div className="wizard-step-line" />
          <button
            type="button"
            className={`wizard-step-indicator ${step === 3 ? 'active' : ''}`}
            onClick={() => setStep(3)}
          >
            <span className="wizard-step-badge">3</span>
            <span>Descripción & Filtros</span>
          </button>
        </div>

        {/* Paso 1: Notas */}
        {step === 1 && (
          <div className="wizard-body">
            <h2 className="wizard-title">¿Qué notas te gustaría que tenga?</h2>
            <p className="wizard-desc">
              Selecciona una o más notas olfativas o sensaciones (puedes omitir si prefieres).
            </p>
            <div className="chips-grid">
              {POPULAR_NOTES.map((note) => {
                const isSelected = selectedNotes.includes(note.id);
                return (
                  <button
                    key={note.id}
                    type="button"
                    className={`chip-btn ${isSelected ? 'selected' : ''}`}
                    onClick={() => toggleNote(note.id)}
                  >
                    <span>{note.icon}</span>
                    <span>{note.label}</span>
                  </button>
                );
              })}
            </div>
            <div className="wizard-actions">
              <span className="muted small">
                {selectedNotes.length} seleccionadas
              </span>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setStep(2)}
              >
                Siguiente →
              </button>
            </div>
          </div>
        )}

        {/* Paso 2: Familia */}
        {step === 2 && (
          <div className="wizard-body">
            <h2 className="wizard-title">¿Tienes preferencia de familia olfativa?</h2>
            <p className="wizard-desc">
              Elige el carácter principal de la fragancia (opcional).
            </p>
            <div className="chips-grid">
              {FAMILIES.map((fam) => {
                const isSelected = selectedFamily === fam.id;
                return (
                  <button
                    key={fam.id}
                    type="button"
                    className={`chip-btn ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedFamily(isSelected ? '' : fam.id)}
                  >
                    <span>{fam.icon}</span>
                    <span>{fam.label}</span>
                  </button>
                );
              })}
            </div>
            <div className="wizard-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setStep(1)}
              >
                ← Atrás
              </button>
              <div className="wizard-actions-right">
                {selectedFamily && (
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setSelectedFamily('')}
                  >
                    Limpiar selección
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setStep(3)}
                >
                  Siguiente →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Paso 3: Descripción, Género y Envío */}
        {step === 3 && (
          <form className="wizard-body" onSubmit={handleRecommend}>
            <h2 className="wizard-title">Detalla tu búsqueda</h2>
            <p className="wizard-desc">
              Escribe libremente cualquier ocasión, estación o sensación (ej. «para verano», «para oficina»).
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.4rem' }}>
              <input
                type="text"
                value={consulta}
                onChange={(event) => setConsulta(event.target.value)}
                placeholder="Ej. perfume para verano, citas, clima caluroso..."
                autoFocus
              />

              <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap' }}>
                <select
                  style={{ flex: 1, minWidth: '180px' }}
                  value={gender}
                  onChange={(event) => setGender(event.target.value as any)}
                >
                  <option value="Todos">Género: Todos</option>
                  <option value="Hombre">Hombre (incluye Unisex)</option>
                  <option value="Mujer">Mujer (incluye Unisex)</option>
                  <option value="Unisex">Solo Unisex</option>
                </select>

                <select
                  style={{ width: '130px' }}
                  value={topK}
                  onChange={(event) => setTopK(Number(event.target.value))}
                >
                  <option value={5}>Top 5</option>
                  <option value={10}>Top 10</option>
                  <option value={20}>Top 20</option>
                </select>
              </div>
            </div>

            {/* Resumen de filtros antes de recomendar */}
            {(selectedNotes.length > 0 || selectedFamily) && (
              <div style={{ marginBottom: '1.2rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                <span className="muted small">Filtros acumulados:</span>
                {selectedFamily && (
                  <span className="badge" style={{ background: '#ede6dc' }}>
                    Familia: {FAMILIES.find((f) => f.id === selectedFamily)?.label}
                  </span>
                )}
                {selectedNotes.map((n) => (
                  <span key={n} className="badge" style={{ background: '#e8f0fe', color: '#1a73e8' }}>
                    {POPULAR_NOTES.find((pn) => pn.id === n)?.label || n}
                  </span>
                ))}
              </div>
            )}

            <div className="wizard-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setStep(2)}
              >
                ← Atrás
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Analizando catálogo…' : '¡Obtener Recomendaciones! ✨'}
              </button>
            </div>
          </form>
        )}
      </div>

      {error && <p className="alert alert-error">{error}</p>}

      {/* Resultados */}
      {result && (
        <>
          <div className="recommend-meta">
            <span className="badge">{result.resultados.length} recomendaciones</span>
            <span className="muted">
              Catálogo: {result.totalCatalogo.toLocaleString('es-MX')} perfumes
              {result.excluidosHate > 0 && ` · ${result.excluidosHate} excluidos`}
            </span>
          </div>

          {result.resultados.length === 0 ? (
            <div className="empty-state">
              <h2>Sin recomendaciones</h2>
              <p>Prueba combinando otras notas o ajustando el filtro de género.</p>
            </div>
          ) : (
            <div className="grid">
              {result.resultados.map((perfume) => (
                <PerfumeCard
                  key={perfume.id}
                  perfume={perfume}
                  footer={
                    <>
                      <span className="score">{perfume.puntuacion.toFixed(3)}</span>
                      <Link to={`/inventory/new/${perfume.id}`} className="btn btn-primary btn-small">
                        Agregar
                      </Link>
                    </>
                  }
                />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
