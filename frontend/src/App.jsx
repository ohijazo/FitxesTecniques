import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { api } from './api/client';
import { ToastProvider } from './components/Toast';
import Login from './pages/Login';
import LlistaFitxes from './pages/LlistaFitxes';
import DetallFitxa from './pages/DetallFitxa';
import NovaFitxa from './pages/NovaFitxa';
import EditarFitxa from './pages/EditarFitxa';
import AdminUsuaris from './pages/AdminUsuaris';
import AdminDestins from './pages/AdminDestins';
import AdminSeccions from './pages/AdminSeccions';
import ControlRevisions from './pages/ControlRevisions';
import AdminEliminacions from './pages/AdminEliminacions';
import Ajuda from './pages/Ajuda';

function ProtectedRoute({ children, usuari, rolsPermesos }) {
  if (!usuari) return <Navigate to="/login" />;
  if (rolsPermesos && !rolsPermesos.includes(usuari.rol)) {
    return <p>No tens permisos per accedir a aquesta pagina.</p>;
  }
  return children;
}

function NavBar({ usuari, onLogout }) {
  const [showConfig, setShowConfig] = useState(false);

  return (
    <nav className="container-fluid">
      <ul>
        <li><Link to="/"><strong>FC Fitxes Tecniques</strong></Link></li>
      </ul>
      <ul>
        <li><Link to="/">Fitxes</Link></li>
        {(usuari.rol === 'admin' || usuari.rol === 'editor') && (
          <li><Link to="/fitxes/nova">Nova fitxa</Link></li>
        )}
        {usuari.rol === 'admin' && (
          <li className="nav-dropdown-wrapper"
            onMouseEnter={() => setShowConfig(true)}
            onMouseLeave={() => setShowConfig(false)}>
            <a href="#" onClick={(e) => e.preventDefault()} className="nav-dropdown-trigger">
              Configuracio &#9662;
            </a>
            {showConfig && (
              <div className="nav-dropdown">
                <Link to="/control-revisions" onClick={() => setShowConfig(false)}>Control revisions</Link>
                <Link to="/admin/destins" onClick={() => setShowConfig(false)}>Destins</Link>
                <Link to="/admin/usuaris" onClick={() => setShowConfig(false)}>Usuaris</Link>
                <Link to="/admin/seccions" onClick={() => setShowConfig(false)}>Camps</Link>
                <Link to="/admin/eliminacions" onClick={() => setShowConfig(false)}>Eliminacions</Link>
              </div>
            )}
          </li>
        )}
        {usuari.rol !== 'admin' && (
          <li><Link to="/control-revisions">Control revisions</Link></li>
        )}
        <li style={{ marginLeft: 'auto' }}><Link to="/ajuda">Ajuda</Link></li>
        <li>
          <span className="user-info">{usuari.nom}</span>
          <a href="#" onClick={(e) => { e.preventDefault(); onLogout(); }}>Sortir</a>
        </li>
      </ul>
    </nav>
  );
}

function Breadcrumbs() {
  const location = useLocation();
  const path = location.pathname;

  if (path === '/' || path === '/login') return null;

  const crumbs = [{ label: 'Fitxes', to: '/' }];

  if (path.startsWith('/fitxes/nova')) {
    crumbs.push({ label: 'Nova fitxa' });
  } else if (path.match(/^\/fitxes\/\d+\/editar$/)) {
    const id = path.split('/')[2];
    crumbs.push({ label: `Fitxa #${id}`, to: `/fitxes/${id}` });
    crumbs.push({ label: 'Editar' });
  } else if (path.match(/^\/fitxes\/\d+$/)) {
    const id = path.split('/')[2];
    crumbs.push({ label: `Fitxa #${id}` });
  } else if (path === '/control-revisions') {
    crumbs.push({ label: 'Control revisions' });
  } else if (path === '/ajuda') {
    crumbs.push({ label: 'Ajuda' });
  } else if (path.startsWith('/admin/')) {
    const section = path.split('/')[2];
    const labels = { seccions: 'Camps', usuaris: 'Usuaris', destins: 'Destins', tipus: 'Tipus', eliminacions: 'Eliminacions' };
    crumbs[0] = { label: 'Admin', to: '/' };
    crumbs.push({ label: labels[section] || section });
  }

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {crumbs.map((c, i) => (
        <span key={i}>
          {i > 0 && <span className="breadcrumb-sep">/</span>}
          {c.to && i < crumbs.length - 1 ? (
            <Link to={c.to}>{c.label}</Link>
          ) : (
            <span className="breadcrumb-current">{c.label}</span>
          )}
        </span>
      ))}
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
    }, 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, [usuari]);

  return (
    <BrowserRouter>
      <ToastProvider>
        {usuari && <NavBar usuari={usuari} onLogout={handleLogout} />}
        <main className="container" style={{ paddingTop: '1rem', paddingBottom: '3rem' }}>
          {usuari && <Breadcrumbs />}
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
            <Route path="/admin/eliminacions" element={
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin']}><AdminEliminacions /></ProtectedRoute>
            } />
            <Route path="/ajuda" element={
              <ProtectedRoute usuari={usuari}><Ajuda /></ProtectedRoute>
            } />
          </Routes>
        </main>
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
