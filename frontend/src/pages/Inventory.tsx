import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api, { getErrorMessage } from '../api/client';
import PerfumeCard from '../components/PerfumeCard';
import type { InventoryItem } from '../types';

export default function Inventory() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [search, setSearch] = useState('');
  const [rating, setRating] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get('/inventory');
      setItems(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(id: string) {
    if (!window.confirm('¿Eliminar este perfume de tu inventario?')) {
      return;
    }
    try {
      await api.delete(`/inventory/${id}`);
      setItems((current) => current.filter((item) => item.id !== id));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  const filtered = items.filter((item) => {
    const term = search.trim().toLowerCase();
    const matchesSearch =
      !term ||
      item.perfume.name.toLowerCase().includes(term) ||
      item.perfume.brand.toLowerCase().includes(term);
    const matchesRating = !rating || item.rating === Number(rating);
    return matchesSearch && matchesRating;
  });

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Tu colección</p>
          <h1>Mi inventario</h1>
          <p className="subtitle">{items.length} perfumes guardados.</p>
        </div>
        <Link to="/search" className="btn btn-secondary">
          Explorar perfumes
        </Link>
      </div>

      <div className="filter-bar">
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Filtrar por nombre o marca"
        />
        <select value={rating} onChange={(event) => setRating(event.target.value)}>
          <option value="">Todas las calificaciones</option>
          <option value="5">5 estrellas</option>
          <option value="4">4 estrellas</option>
          <option value="3">3 estrellas</option>
          <option value="2">2 estrellas</option>
          <option value="1">1 estrella</option>
        </select>
      </div>

      {error && <p className="alert alert-error">{error}</p>}

      {loading ? (
        <p className="muted center">Cargando inventario…</p>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <h2>Tu inventario está vacío</h2>
          <p>Busca un perfume y agrégalo para empezar a recibir mejores recomendaciones.</p>
          <Link to="/search" className="btn btn-primary">
            Buscar perfumes
          </Link>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <h2>Sin coincidencias</h2>
          <p>Ningún perfume de tu inventario coincide con el filtro.</p>
        </div>
      ) : (
        <div className="grid">
          {filtered.map((item) => (
            <PerfumeCard
              key={item.id}
              perfume={item.perfume}
              rating={item.rating}
              footer={
                <>
                  <Link to={`/inventory/${item.id}/edit`} className="btn btn-ghost btn-small">
                    Editar
                  </Link>
                  <button
                    type="button"
                    className="btn btn-danger btn-small"
                    onClick={() => handleDelete(item.id)}
                  >
                    Eliminar
                  </button>
                </>
              }
            />
          ))}
        </div>
      )}
    </section>
  );
}
