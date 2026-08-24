import { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, Link, NavLink, Navigate, useLocation } from 'react-router-dom';
import { api } from './api/client';
import { ToastProvider } from './components/Toast';
import Login from './pages/Login';
import LlistaFitxes from './pages/LlistaFitxes';
import DetallFitxa from './pages/DetallFitxa';
import NovaFitxa from './pages/NovaFitxa';
import EditarFitxa from './pages/EditarFitxa';
import AdminUsuaris from './pages/AdminUsuaris';
import AdminDestins from './pages/AdminDestins';
import AdminEstats from './pages/AdminEstats';
import AdminSeccions from './pages/AdminSeccions';
import ControlRevisions from './pages/ControlRevisions';
import AdminEliminacions from './pages/AdminEliminacions';
import JobDetail from './pages/JobDetail';
import Jobs from './pages/Jobs';
import BulkEdit from './pages/BulkEdit';
import BulkDistribuir from './pages/BulkDistribuir';
import Ajuda from './pages/Ajuda';

function ProtectedRoute({ children, usuari, rolsPermesos }) {
  if (!usuari) return <Navigate to="/login" />;
  if (rolsPermesos && !rolsPermesos.includes(usuari.rol)) {
    return (
      <div className="empty-state">
        <h2>Aquesta pàgina no és per al teu perfil</h2>
        <p>El teu rol és <strong>{usuari.rol}</strong> i aquesta secció demana un altre nivell d'accés.
          Si hi has d'entrar, demana-ho a un administrador.</p>
        <Link to="/">Tornar a les fitxes</Link>
      </div>
    );
  }
  return children;
}

// Enllaços del desplegable "Configuració" segons el rol.
const CONFIG_LINKS = {
  admin: [
    { to: '/admin/usuaris', label: 'Usuaris' },
    { to: '/admin/destins', label: 'Destins' },
    { to: '/admin/estats', label: 'Estats' },
    { to: '/admin/seccions', label: 'Camps' },
    { to: '/control-revisions', label: 'Control revisions' },
    { to: '/admin/eliminacions', label: 'Eliminacions' },
    { to: '/jobs', label: 'Jobs massius' },
  ],
  distribuidor: [
    { to: '/admin/destins', label: 'Destins' },
    { to: '/jobs', label: 'Jobs massius' },
  ],
};

function ConfigMenu({ links }) {
  const [obert, setObert] = useState(false);
  const wrapper = useRef(null);

  // Obrir amb clic (no amb hover): amb hover el menú era inabastable amb
  // teclat i en tàctil. Es tanca amb Esc o clicant fora.
  useEffect(() => {
    if (!obert) return;
    const onKey = (e) => { if (e.key === 'Escape') setObert(false); };
    const onClickFora = (e) => {
      if (wrapper.current && !wrapper.current.contains(e.target)) setObert(false);
    };
    window.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClickFora);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClickFora);
    };
  }, [obert]);

  return (
    <li className="nav-dropdown-wrapper" ref={wrapper}>
      <button type="button" className="nav-dropdown-trigger"
        aria-expanded={obert} aria-haspopup="true"
        onClick={() => setObert((v) => !v)}>
        Configuració &#9662;
      </button>
      {obert && (
        <div className="nav-dropdown">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} onClick={() => setObert(false)}>{l.label}</NavLink>
          ))}
        </div>
      )}
    </li>
  );
}

function NoTrobada() {
  return (
    <div className="empty-state">
      <h2>Aquesta pàgina no existeix</h2>
      <p>L'adreça que has seguit no correspon a cap secció de l'aplicació.</p>
      <Link to="/">Tornar a les fitxes</Link>
    </div>
  );
}

function NavBar({ usuari, onLogout }) {
  const configLinks = CONFIG_LINKS[usuari.rol];
  const classeActiu = ({ isActive }) => (isActive ? 'nav-link actiu' : 'nav-link');

  return (
    <nav className="container-fluid">
      <ul>
        <li><Link to="/"><strong>FC Fitxes Tècniques</strong></Link></li>
      </ul>
      <ul>
        <li><NavLink to="/" end className={classeActiu}>Fitxes</NavLink></li>
        {(usuari.rol === 'admin' || usuari.rol === 'editor') && (
          <li><NavLink to="/fitxes/nova" className={classeActiu}>Nova fitxa</NavLink></li>
        )}
        {configLinks && <ConfigMenu links={configLinks} />}
        {!configLinks && (
          <li><NavLink to="/control-revisions" className={classeActiu}>Control revisions</NavLink></li>
        )}
        <li style={{ marginLeft: 'auto' }}><NavLink to="/ajuda" className={classeActiu}>Ajuda</NavLink></li>
        <li>
          <span className="user-info">{usuari.nom}</span>
          <button type="button" className="nav-logout" onClick={onLogout}>Sortir</button>
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
    const labels = { seccions: 'Camps', usuaris: 'Usuaris', destins: 'Destins', tipus: 'Tipus', eliminacions: 'Eliminacions', estats: 'Estats' };
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
              <ProtectedRoute usuari={usuari}><LlistaFitxes usuari={usuari} /></ProtectedRoute>
            } />
            <Route path="/fitxes/nova" element={
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin', 'editor']}><NovaFitxa /></ProtectedRoute>
            } />
            <Route path="/fitxes/bulk-edit" element={
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin']}><BulkEdit /></ProtectedRoute>
            } />
            <Route path="/fitxes/bulk-distribuir" element={
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin', 'editor', 'distribuidor']}><BulkDistribuir /></ProtectedRoute>
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
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin', 'distribuidor']}><AdminDestins /></ProtectedRoute>
            } />
            <Route path="/admin/estats" element={
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin']}><AdminEstats /></ProtectedRoute>
            } />
            <Route path="/admin/eliminacions" element={
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin']}><AdminEliminacions /></ProtectedRoute>
            } />
            <Route path="/jobs" element={
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin', 'editor', 'distribuidor']}><Jobs /></ProtectedRoute>
            } />
            <Route path="/jobs/:id" element={
              <ProtectedRoute usuari={usuari} rolsPermesos={['admin', 'editor', 'distribuidor']}><JobDetail /></ProtectedRoute>
            } />
            <Route path="/ajuda" element={
              <ProtectedRoute usuari={usuari}><Ajuda /></ProtectedRoute>
            } />
            <Route path="*" element={
              usuari ? <NoTrobada /> : <Navigate to="/login" />
            } />
          </Routes>
        </main>
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
