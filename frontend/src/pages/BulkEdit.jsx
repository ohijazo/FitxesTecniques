import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import FitxaForm from '../components/FitxaForm';
import { useEscapeKey } from '../components/useEscapeKey';

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
  const [modeCamps, setModeCamps] = useState('crear');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  useEscapeKey(loading ? null : onCancel);

  // Per a cada camp tocat, llista de fitxes que NO el tenien (es crearia)
  const novetatsPerCamp = useMemo(() => {
    const res = {};
    Object.keys(canvis).forEach((camp) => {
      const sense = fitxes.filter((f) => {
        const c = f.versions?.find((v) => v.activa)?.contingut || {};
        return !(camp in c);
      });
      if (sense.length > 0) res[camp] = sense;
    });
    return res;
  }, [fitxes, canvis]);

  const hiHaNovetats = Object.keys(novetatsPerCamp).length > 0;

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
      await onConfirm(descripcio.trim(), password, modeCamps);
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

        {hiHaNovetats && (
          <div style={{
            background: '#fef3c7', borderLeft: '4px solid #f59e0b',
            padding: '0.75rem 1rem', borderRadius: '4px', marginBottom: '1rem',
            fontSize: '0.85rem',
          }}>
            <strong>&#9888; Aquests camps no existeixen a totes les fitxes:</strong>
            <ul style={{ marginTop: '0.4rem', marginBottom: '0.6rem' }}>
              {Object.entries(novetatsPerCamp).map(([camp, fs]) => (
                <li key={camp}>
                  <code>{camp}</code>: es crearia a {fs.length} fitxa(es) que no el tenien
                  {' '}({fs.slice(0, 5).map((f) => f.art_codi).join(', ')}{fs.length > 5 ? `, +${fs.length - 5} més` : ''})
                </li>
              ))}
            </ul>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem', margin: '0.3rem 0', cursor: 'pointer' }}>
              <input type="radio" name="modeCamps" checked={modeCamps === 'crear'}
                onChange={() => setModeCamps('crear')}
                style={{ width: 'auto', margin: '4px 0 0 0' }} />
              <span>
                <strong>Aplicar a totes</strong> &mdash; es crearà el camp a les fitxes que no el tenien.
              </span>
            </label>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem', margin: '0.3rem 0', cursor: 'pointer' }}>
              <input type="radio" name="modeCamps" checked={modeCamps === 'saltar'}
                onChange={() => setModeCamps('saltar')}
                style={{ width: 'auto', margin: '4px 0 0 0' }} />
              <span>
                <strong>Saltar les fitxes que no el tenien</strong> &mdash; només s'aplica a fitxes que ja tenien el camp. Les que no el tenien NO es modifiquen.
              </span>
            </label>
          </div>
        )}

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

  const aplicarCanvis = async (descripcio, password, modeCamps) => {
    const res = await api.bulkEditFitxes({
      fitxa_ids: fitxes.map((f) => f.id),
      canvis: pendingChanges,
      descripcio_canvi: descripcio,
      password,
      mode_camps_nous: modeCamps || 'crear',
    });
    const okCount = (res?.ok || []).length;
    const errCount = (res?.errors || []).length;
    if (errCount === 0) {
      toast.success(`Canvis aplicats a ${okCount} fitxes`);
    } else {
      toast.success(`Aplicat a ${okCount} fitxes; ${errCount} saltades o amb error`);
    }
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
