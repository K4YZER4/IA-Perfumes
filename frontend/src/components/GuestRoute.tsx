import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function GuestRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="center-screen">Cargando…</div>;
  }

  if (user) {
    return <Navigate to="/search" replace />;
  }

  return <Outlet />;
}
