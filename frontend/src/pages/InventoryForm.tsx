import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api, { getErrorMessage } from '../api/client';
import PerfumeImage from '../components/PerfumeImage';
import Stars from '../components/Stars';
import type { InventoryItem, Perfume } from '../types';

interface Props {
  mode: 'create' | 'edit';
}

export default function InventoryForm({ mode }: Props) {
  const { perfumeId, id } = useParams();
  const navigate = useNavigate();

  const [perfume, setPerfume] = useState<Perfume | null>(null);
  const [itemId, setItemId] = useState<string | null>(null);
  const [rating, setRating] = useState(4);
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        if (mode === 'create') {
          const { data } = await api.get(`/perfumes/${perfumeId}`);
          setPerfume(data);
        } else {
          const { data } = await api.get('/inventory');
          const found = data.find((item: InventoryItem) => item.id === id);
          if (!found) {
            setError('No encontramos ese elemento en tu inventario.');
            return;
          }
          setPerfume(found.perfume);
          setItemId(found.id);
          setRating(found.rating);
          setDescription(found.personalDescription || '');
        }
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [mode, perfumeId, id]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!perfume) {
      return;
    }

    setSaving(true);
    setError('');
    try {
      if (mode === 'create') {
        await api.post('/inventory', {
          perfumeId: perfume.id,
          rating,
          personalDescription: description,
        });
      } else {
        await api.patch(`/inventory/${itemId}`, {
          rating,
          personalDescription: description,
        });
      }
      navigate('/inventory');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!itemId || !window.confirm('¿Eliminar este perfume de tu inventario?')) {
      return;
    }
    try {
      await api.delete(`/inventory/${itemId}`);
      navigate('/inventory');
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  if (loading) {
    return <p className="muted center">Cargando…</p>;
  }

  if (!perfume) {
    return (
      <>
        <p className="alert alert-error">{error || 'Perfume no encontrado.'}</p>
        <Link to="/search" className="btn btn-secondary">
          Volver al catálogo
        </Link>
      </>
    );
  }

  return (
    <section>
      <Link to={mode === 'create' ? `/perfumes/${perfume.id}` : '/inventory'} className="back-link">
        ← Volver
      </Link>

      <div className="form-card">
        <div className="form-perfume">
          <PerfumeImage
            src={perfume.imageUrl}
            alt={`${perfume.brand} ${perfume.name}`}
            gender={perfume.gender}
            family={perfume.family}
          />
          <div>
            <p className="eyebrow">{perfume.brand}</p>
            <h1>{perfume.name}</h1>
            <p className="meta">{[perfume.family, perfume.subfamily].filter(Boolean).join(' · ')}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="stack">
          <div>
            <span className="field-label">Tu calificación</span>
            <Stars value={rating} onChange={setRating} />
            <p className="muted small">{rating} de 5 estrellas</p>
          </div>

          <label>
            Nota personal
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={500}
              rows={4}
              placeholder="¿Qué te parece este perfume? ¿Cuándo lo usarías?"
            />
            <span className="counter">{description.length}/500</span>
          </label>

          {error && <p className="alert alert-error">{error}</p>}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Guardando…' : mode === 'create' ? 'Agregar al inventario' : 'Guardar cambios'}
            </button>
            {mode === 'edit' && (
              <button type="button" className="btn btn-danger" onClick={handleDelete}>
                Eliminar del inventario
              </button>
            )}
          </div>
        </form>
      </div>
    </section>
  );
}
