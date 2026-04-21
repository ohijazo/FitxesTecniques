import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom';
import { api } from './api/client';
import Login from './pages/Login';
import LlistaFitxes from './pages/LlistaFitxes';
import DetallFitxa from './pages/DetallFitxa';
import NovaFitxa from './pages/NovaFitxa';
import EditarFitxa from './pages/EditarFitxa';
import AdminUsuaris from './pages/AdminUsuaris';
import AdminDestins from './pages/AdminDestins';
import AdminSeccions from './pages/AdminSeccions';
import ControlRevisions from './pages/ControlRevisions';

function ProtectedRoute({ children, usuari, rolsPermesos }) {
  if (!usuari) return <Navigate to="/login" />;
  if (rolsPermesos && !rolsPermesos.includes(usuari.rol)) {
    return <p>No tens permisos per accedir a aquesta pàgina.</p>;
  }
  return children;
}

function NavBar({ usuari, onLogout }) {
  return (
    <nav className="container-fluid">
      <ul>
        <li><Link to="/"><strong>FC Fitxes Tècniques</strong></Link></li>
      </ul>
      <ul>
        <li><Link to="/">Fitxes</Link></li>
        <li><Link to="/control-revisions">Control revisions</Link></li>
        {(usuari.rol === 'admin' || usuari.rol === 'editor') && (
          <li><Link to="/fitxes/nova">Nova fitxa</Link></li>
        )}
        {usuari.rol === 'admin' && (
          <>
            <li><Link to="/admin/seccions">Camps</Link></li>
            <li><Link to="/admin/destins">Destins</Link></li>
            <li><Link to="/admin/usuaris">Usuaris</Link></li>
          </>
        )}
        <li style={{ marginLeft: 'auto' }}>
          <span className="user-info">{usuari.nom}</span>
          <a href="#" onClick={(e) => { e.preventDefault(); onLogout(); }}>Sortir</a>
        </li>
      </ul>
    </nav>
  );
}

function App() {
  const [usuari, setUsuari] = useState(() => {
    const saved = localStorage.getItem('usuari');
    return saved ? JSON.parse(saved) : null;
  });

  const handleLogin = (u) => setUsuari(u);
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('usuari');
    setUsuari(null);
  };

  // Refresh token cada hora
  useEffect(() => {
    if (!usuari) return;
    const interval = setInterval(() => {
      api.refreshToken()
        .then((data) => { if (data.token) localStorage.setItem('token', data.token); })
        .catch(() => { handleLogout(); });
    }, 60 * 60 * 1000); // 1 hora
    return () => clearInterval(interval);
  }, [usuari]);

  return (
    <BrowserRouter>
      {usuari && <NavBar usuari={usuari} onLogout={handleLogout} />}
      <main className="container" style={{ paddingTop: '2rem', paddingBottom: '3rem' }}>
        <Routes>
          <Route path="/login" element={
            usuari ? <Navigate to="/" /> : <Login onLogin={handleLogin} />
          } />
          <Route path="/" element={
            <ProtectedRoute usuari={usuari}><LlistaFitxes /></ProtectedRoute>
          } />
          <Route path="/fitxes/nova" element={
            <ProtectedRoute usuari={usuari} rolsPermesos={['admin', 'editor']}><NovaFitxa /></ProtectedRoute>
          } />
          <Route path="/fitxes/:id" element={
            <ProtectedRoute usuari={usuari}><DetallFitxa /></ProtectedRoute>
          } />
          <Route path="/fitxes/:id/editar" element={
            <ProtectedRoute usuari={usuari} rolsPermesos={['admin', 'editor']}><EditarFitxa /></ProtectedRoute>
          } />
          <Route path="/control-revisions" element={
            <ProtectedRoute usuari={usuari}><ControlRevisions /></ProtectedRoute>
          } />
          <Route path="/admin/seccions" element={
            <ProtectedRoute usuari={usuari} rolsPermesos={['admin']}><AdminSeccions /></ProtectedRoute>
          } />
          <Route path="/admin/usuaris" element={
            <ProtectedRoute usuari={usuari} rolsPermesos={['admin']}><AdminUsuaris /></ProtectedRoute>
          } />
          <Route path="/admin/destins" element={
            <ProtectedRoute usuari={usuari} rolsPermesos={['admin']}><AdminDestins /></ProtectedRoute>
          } />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
