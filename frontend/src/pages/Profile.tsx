import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    api
      .get('/inventory')
      .then((response) => setCount(response.data.length))
      .catch(() => setCount(null));
  }, []);

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Cuenta</p>
          <h1>Mi perfil</h1>
        </div>
      </div>

      <div className="profile-card">
        <div className="avatar">{user?.name?.charAt(0).toUpperCase()}</div>
        <div className="profile-info">
          <h2>{user?.name}</h2>
          <p className="muted">{user?.email}</p>
          <p className="muted small">
            {count === null ? 'Cargando inventario…' : `${count} perfumes en tu inventario`}
          </p>
        </div>
        <button type="button" className="btn btn-danger" onClick={handleLogout}>
          Cerrar sesión
        </button>
      </div>
    </section>
  );
}
