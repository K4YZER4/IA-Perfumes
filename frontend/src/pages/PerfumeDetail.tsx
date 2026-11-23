import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api, { getErrorMessage } from '../api/client';
import PerfumeImage from '../components/PerfumeImage';
import Stars from '../components/Stars';
import type { InventoryItem, Perfume } from '../types';

export default function PerfumeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [perfume, setPerfume] = useState<Perfume | null>(null);
  const [item, setItem] = useState<InventoryItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        const [perfumeResponse, inventoryResponse] = await Promise.all([
          api.get(`/perfumes/${id}`),
          api.get('/inventory'),
        ]);
        setPerfume(perfumeResponse.data);
        setItem(
          inventoryResponse.data.find(
            (inventoryItem: InventoryItem) => inventoryItem.perfume.id === perfumeResponse.data.id,
          ) || null,
        );
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return <p className="muted center">Cargando perfume…</p>;
  }

  if (error) {
    return <p className="alert alert-error">{error}</p>;
  }

  if (!perfume) {
    return null;
  }

  return (
    <section>
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="back-link"
        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
      >
        ← Volver
      </button>

      <div className="detail-card">
        <PerfumeImage
          src={perfume.imageUrl}
          alt={`${perfume.brand} ${perfume.name}`}
          gender={perfume.gender}
          family={perfume.family}
          className="detail-image"
        />

        <div className="detail-body">
          <p className="eyebrow">{perfume.brand}</p>
          <h1>{perfume.name}</h1>

          <div className="detail-grid">
            <div>
              <span className="detail-label">Familia</span>
              <span>{perfume.family || 'No disponible'}</span>
            </div>
            <div>
              <span className="detail-label">Subfamilia</span>
              <span>{perfume.subfamily || 'No disponible'}</span>
            </div>
            <div>
              <span className="detail-label">Género</span>
              <span>{perfume.gender || 'No disponible'}</span>
            </div>
            <div>
              <span className="detail-label">Año</span>
              <span>{perfume.releaseYear || 'No disponible'}</span>
            </div>
          </div>

          {perfume.description && <p className="description">{perfume.description}</p>}

          {item ? (
            <div className="owned-box">
              <div>
                <p className="eyebrow">En tu inventario</p>
                <Stars value={item.rating} />
                {item.personalDescription && <p className="muted">{item.personalDescription}</p>}
              </div>
              <Link to={`/inventory/${item.id}/edit`} className="btn btn-secondary">
                Editar
              </Link>
            </div>
          ) : (
            <Link to={`/inventory/new/${perfume.id}`} className="btn btn-primary">
              Agregar a mi inventario
            </Link>
          )}
        </div>
      </div>
    </section>
  );
}
