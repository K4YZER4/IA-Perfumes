import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import api, { getErrorMessage } from '../api/client';
import PerfumeCard from '../components/PerfumeCard';
import type { Perfume } from '../types';

export default function Search() {
  const [search, setSearch] = useState('');
  const [gender, setGender] = useState('');
  const [perfumes, setPerfumes] = useState<Perfume[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load(term = search, selectedGender = gender) {
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get('/perfumes', {
        params: {
          search: term || undefined,
          gender: selectedGender || undefined,
          limit: 60,
        },
      });
      setPerfumes(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load('', '');
  }, []);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    load();
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Catálogo</p>
          <h1>Buscar perfumes</h1>
          <p className="subtitle">Encuentra fragancias por nombre o marca.</p>
        </div>
      </div>

      <form className="search-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Ej. Sauvage, Dior, Afnan…"
          aria-label="Buscar perfume"
        />
        <select value={gender} onChange={(event) => setGender(event.target.value)} aria-label="Género">
          <option value="">Todos</option>
          <option value="Male">Hombre</option>
          <option value="Female">Mujer</option>
          <option value="Unisex">Unisex</option>
        </select>
        <button type="submit" className="btn btn-primary">
          Buscar
        </button>
      </form>

      {error && <p className="alert alert-error">{error}</p>}

      {loading ? (
        <p className="muted center">Buscando perfumes…</p>
      ) : perfumes.length === 0 ? (
        <div className="empty-state">
          <h2>Sin resultados</h2>
          <p>No encontramos perfumes con esos criterios. Prueba con otra marca o nombre.</p>
        </div>
      ) : (
        <>
          <p className="results-count">{perfumes.length} perfumes encontrados</p>
          <div className="grid">
            {perfumes.map((perfume) => (
              <PerfumeCard key={perfume.id} perfume={perfume} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
