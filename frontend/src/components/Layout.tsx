import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/search" className="brand">
            Perfume <span>Advisor</span>
          </NavLink>

          <nav className="main-nav">
            <NavLink to="/search">Buscar</NavLink>
            <NavLink to="/inventory">Mi inventario</NavLink>
            <NavLink to="/recommendations">Recomendaciones</NavLink>
            <NavLink to="/profile">Perfil</NavLink>
          </nav>

          <div className="user-box">
            <span>{user?.name}</span>
            <button type="button" className="btn btn-ghost btn-small" onClick={handleLogout}>
              Salir
            </button>
          </div>
        </div>
      </header>

      <main className="page">
        <Outlet />
      </main>
    </>
  );
}
