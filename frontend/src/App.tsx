import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import GuestRoute from './components/GuestRoute';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Search from './pages/Search';
import PerfumeDetail from './pages/PerfumeDetail';
import Inventory from './pages/Inventory';
import InventoryForm from './pages/InventoryForm';
import Recommendations from './pages/Recommendations';
import Profile from './pages/Profile';

function HomeRedirect() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="center-screen">Cargando…</div>;
  }

  return <Navigate to={user ? '/search' : '/login'} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<GuestRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/search" element={<Search />} />
            <Route path="/perfumes/:id" element={<PerfumeDetail />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/inventory/new/:perfumeId" element={<InventoryForm mode="create" />} />
            <Route path="/inventory/:id/edit" element={<InventoryForm mode="edit" />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/profile" element={<Profile />} />
          </Route>
        </Route>

        <Route path="/" element={<HomeRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
