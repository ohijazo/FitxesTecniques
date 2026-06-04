import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import FitxaForm from '../components/FitxaForm';

/**
 * Edició massiva — mateix layout que l'edició individual (FitxaForm),
 * però en mode bulk: només els camps tocats per l'usuari s'aplicaran a
 * totes les fitxes seleccionades. La capçalera, les taules i les
 * imatges queden bloquejades.
 */

function calcularVariants(fitxes) {
  const variesByKey = {};
  const unionByKey = {};
  const KEYS = new Set();
  fitxes.forEach((f) => {
    const c = f.versions?.find((v) => v.activa)?.contingut || {};
    Object.keys(c).forEach((k) => KEYS.add(k));
  });
  KEYS.forEach((k) => {
    const values = fitxes.map((f) => {
      const c = f.versions?.find((v) => v.activa)?.contingut || {};
      return JSON.stringify(c[k] ?? null);
    });
    const unique = new Set(values);
    if (unique.size === 1) {
      unionByKey[k] = JSON.parse([...unique][0]);
    } else {
      variesByKey[k] = true;
      // Mantenim la clau perquè FitxaForm renderitzi el camp (amb valor buit)
      unionByKey[k] = '';
    }
  });
  return { unionByKey, variesByKey };
}

function ConfirmModal({ fitxes, canvis, onConfirm, onCancel }) {
  const [descripcio, setDescripcio] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (e) => {
    e.preventDefault();
    if (descripcio.trim().length < 10) {
      setError('La descripció del canvi ha de tenir com a mínim 10 caràcters.');
      return;
    }
    if (!password) {
      setError('Cal la contrasenya per confirmar.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onConfirm(descripcio.trim(), password);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const camps = Object.keys(canvis);

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0 }}>Aplicar canvis a {fitxes.length} fitxes</h3>
          <button className="outline secondary btn-sm" onClick={onCancel}>&times;</button>
        </div>

        <p style={{ fontSize: '0.88rem', color: 'var(--gray-600)' }}>
          Es crearà una nova versió per a cada fitxa seleccionada amb els camps modificats.
        </p>

        <div style={{ marginBottom: '1rem' }}>
          <strong style={{ fontSize: '0.85rem' }}>Camps que es modificaran ({camps.length}):</strong>
          <ul style={{ fontSize: '0.85rem', marginTop: '0.3rem' }}>
            {camps.map((k) => <li key={k}><code>{k}</code></li>)}
          </ul>
        </div>

        <details style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>
          <summary style={{ cursor: 'pointer' }}>Fitxes afectades ({fitxes.length})</summary>
          <ul style={{ marginTop: '0.3rem', columns: 3, columnGap: '1rem' }}>
            {fitxes.map((f) => (
              <li key={f.id} style={{ breakInside: 'avoid' }}><code>{f.art_codi}</code> &mdash; {f.nom_producte}</li>
            ))}
          </ul>
        </details>

        <form onSubmit={enviar}>
          <label>
            Descripció del canvi *
            <textarea value={descripcio} onChange={(e) => setDescripcio(e.target.value)}
              required minLength={10} rows={3}
              placeholder="Ex: Actualització de pesticidas i vida útil per nova normativa" />
          </label>
          <label>
            Confirma amb la teva contrasenya *
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              required autoComplete="current-password" />
          </label>

          {error && <p style={{ color: 'var(--danger)', fontSize: '0.88rem', marginBottom: '0.5rem' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="outline secondary" onClick={onCancel}>Cancel·lar</button>
            <button type="submit" disabled={loading} aria-busy={loading}>
              {loading ? 'Aplicant...' : `Aplicar a ${fitxes.length} fitxes`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function BulkEdit() {
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();

  const fitxaIds = location.state?.fitxa_ids || [];

  const [fitxes, setFitxes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [touchedKeys, setTouchedKeys] = useState(() => new Set());
  const [pendingChanges, setPendingChanges] = useState(null);

  useEffect(() => {
    if (fitxaIds.length === 0) {
      setError('No hi ha fitxes seleccionades.');
      setLoading(false);
      return;
    }
    Promise.all(fitxaIds.map((id) => api.detallFitxa(id)))
      .then((results) => {
        setFitxes(results);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const { unionByKey, variesByKey } = useMemo(() => calcularVariants(fitxes), [fitxes]);

  const initialData = useMemo(() => ({
    art_codi: '',
    nom_producte: '',
    categoria: '',
    descripcio_canvi: '',
    contingut: unionByKey,
  }), [unionByKey]);

  const onTouch = useMemo(() => (k) => {
    setTouchedKeys((prev) => {
      if (prev.has(k)) return prev;
      const next = new Set(prev);
      next.add(k);
      return next;
    });
  }, []);

  const bulkContext = useMemo(() => ({
    fitxes,
    variesByKey,
    touchedCount: touchedKeys.size,
    onTouch,
  }), [fitxes, variesByKey, touchedKeys, onTouch]);

  const handleSubmit = async ({ contingut }) => {
    // Construir el dict de canvis només amb les claus tocades
    const canvis = {};
    touchedKeys.forEach((k) => {
      canvis[k] = contingut[k];
    });
    if (Object.keys(canvis).length === 0) {
      toast.error('No has modificat cap camp.');
      return;
    }
    setPendingChanges(canvis);
  };

  const aplicarCanvis = async (descripcio, password) => {
    await api.bulkEditFitxes({
      fitxa_ids: fitxes.map((f) => f.id),
      canvis: pendingChanges,
      descripcio_canvi: descripcio,
      password,
    });
    toast.success(`Canvis aplicats a ${fitxes.length} fitxes`);
    setPendingChanges(null);
    navigate('/');
  };

  if (loading) return <p aria-busy="true">Carregant fitxes...</p>;
  if (error) return (
    <>
      <p style={{ color: 'var(--danger)' }}>{error}</p>
      <Link to="/" className="outline secondary" role="button">&larr; Tornar a la llista</Link>
    </>
  );
  if (fitxes.length === 0) return (
    <>
      <p>No s'han trobat fitxes per editar.</p>
      <Link to="/" className="outline secondary" role="button">&larr; Tornar a la llista</Link>
    </>
  );

  return (
    <>
      <div className="toolbar">
        <button className="outline secondary btn-sm" onClick={() => navigate('/')}>
          &larr; Tornar a la llista
        </button>
        <h2 style={{ margin: 0 }}>Edició massiva</h2>
      </div>

      <FitxaForm
        initialData={initialData}
        onSubmit={handleSubmit}
        isNew={false}
        bulkContext={bulkContext}
      />

      {pendingChanges && (
        <ConfirmModal
          fitxes={fitxes}
          canvis={pendingChanges}
          onConfirm={aplicarCanvis}
          onCancel={() => setPendingChanges(null)}
        />
      )}
    </>
  );
}

export default BulkEdit;
