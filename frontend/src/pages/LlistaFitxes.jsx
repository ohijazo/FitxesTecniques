import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import BulkActionBar from '../components/BulkActionBar';

function DistBadge({ resum }) {
  if (!resum) return <span className="dist-badge dist-none" title="Sense versió activa">&mdash;</span>;
  const { ok, error, pendent } = resum;
  if (error > 0) return (
    <span className="dist-badge dist-error" title={`${error} error, ${ok} ok`}>
      <span className="dist-icon">&times;</span> {error} error
    </span>
  );
  if (pendent > 0 && ok === 0) return (
    <span className="dist-badge dist-pending" title={`${pendent} pendents`}>
      <span className="dist-icon">&#9675;</span> Pendent
    </span>
  );
  if (ok > 0 && pendent === 0) return (
    <span className="dist-badge dist-ok" title={`${ok} distribucions ok`}>
      <span className="dist-icon">&#10003;</span> Distribuït
    </span>
  );
  return (
    <span className="dist-badge dist-partial" title={`${ok} ok, ${pendent} pendents`}>
      <span className="dist-icon">&#9681;</span> Parcial
    </span>
  );
}

function LlistaFitxes({ usuari }) {
  const [fitxes, setFitxes] = useState([]);
  const [cerca, setCerca] = useState('');
  const [estat, setEstat] = useState(() => localStorage.getItem('filtre_estat') || '');
  const [sortBy, setSortBy] = useState(() => localStorage.getItem('sort_by') || 'updated_at');
  const [sortOrder, setSortOrder] = useState(() => localStorage.getItem('sort_order') || 'desc');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [seleccionats, setSeleccionats] = useState(() => new Set());
  const [estatsCatalog, setEstatsCatalog] = useState([]);
  const toast = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    api.llistarEstats().then(setEstatsCatalog).catch(() => {});
  }, []);

  const estatsByCodi = useMemo(() => {
    const m = {};
    estatsCatalog.forEach((e) => { m[e.codi] = e; });
    return m;
  }, [estatsCatalog]);

  const carregarFitxes = async (textCerca = '', filtreEstat = estat, sb = sortBy, so = sortOrder) => {
    setLoading(true);
    try {
      const params = { per_page: 200, sort_by: sb, sort_order: so };
      if (textCerca) params.cerca = textCerca;
      if (filtreEstat) params.estat = filtreEstat;
      const data = await api.llistarFitxes(params);
      setFitxes(data.fitxes);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { carregarFitxes(cerca, estat, sortBy, sortOrder); }, [estat, sortBy, sortOrder]);

  const toggleSort = (col) => {
    let nextOrder = 'asc';
    if (sortBy === col) {
      nextOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    }
    setSortBy(col);
    setSortOrder(nextOrder);
    localStorage.setItem('sort_by', col);
    localStorage.setItem('sort_order', nextOrder);
  };

  const sortIndicator = (col) => {
    if (sortBy !== col) return ' ↕';
    return sortOrder === 'asc' ? ' ▲' : ' ▼';
  };

  const handleCerca = (e) => {
    e.preventDefault();
    carregarFitxes(cerca, estat);
  };

  const handleEstat = (e) => {
    const val = e.target.value;
    setEstat(val);
    localStorage.setItem('filtre_estat', val);
  };

  const descarregarPdf = async (fitxa) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/fitxes/${fitxa.id}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Error descarregant');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `${fitxa.art_codi}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success(`PDF ${fitxa.art_codi} descarregat`);
    } catch (err) {
      toast.error(`Error descarregant PDF: ${err.message}`);
    }
  };

  // Selecció múltiple
  const idsVisibles = useMemo(() => fitxes.map((f) => f.id), [fitxes]);
  const totsSeleccionats = idsVisibles.length > 0 && idsVisibles.every((id) => seleccionats.has(id));
  const algunSeleccionat = idsVisibles.some((id) => seleccionats.has(id));

  const toggleFitxa = (id) => {
    setSeleccionats((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleTots = () => {
    setSeleccionats((prev) => {
      const next = new Set(prev);
      if (totsSeleccionats) {
        idsVisibles.forEach((id) => next.delete(id));
      } else {
        idsVisibles.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const deseleccionar = () => setSeleccionats(new Set());

  const obrirEdicioMassiva = () => {
    navigate('/fitxes/bulk-edit', { state: { fitxa_ids: [...seleccionats] } });
  };

  const obrirDistribucioMassiva = () => {
    navigate('/fitxes/bulk-distribuir', { state: { fitxa_ids: [...seleccionats] } });
  };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0 }}>Fitxes tècniques</h2>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.88rem', margin: '0.2rem 0 0' }}>
            {total} fitxes registrades
          </p>
        </div>
        <Link to="/fitxes/nova" role="button">+ Nova fitxa</Link>
      </div>

      <form onSubmit={handleCerca} style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', alignItems: 'flex-end' }}>
        <label style={{ flex: 1, margin: 0 }}>
          <input
            type="search"
            placeholder="Cercar per codi o nom..."
            value={cerca}
            onChange={(e) => setCerca(e.target.value)}
            aria-label="Cercar fitxes"
            style={{ margin: 0 }}
          />
        </label>
        <label style={{ margin: 0, width: '180px' }}>
          <select value={estat} onChange={handleEstat} style={{ margin: 0 }}>
            <option value="">Tots els estats</option>
            {estatsCatalog.map((e) => (
              <option key={e.codi} value={e.codi}>{e.nom}</option>
            ))}
          </select>
        </label>
        <button type="submit" style={{ whiteSpace: 'nowrap', marginBottom: 0 }}>Cercar</button>
      </form>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

      {loading ? (
        <p aria-busy="true">Carregant fitxes...</p>
      ) : fitxes.length === 0 ? (
        <div className="empty-state">
          <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No s'han trobat fitxes</p>
          <p>Prova a canviar els filtres o <Link to="/fitxes/nova">crea la primera fitxa</Link>.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th className="table-checkbox-col">
                  <input
                    type="checkbox"
                    checked={totsSeleccionats}
                    ref={(el) => {
                      if (el) el.indeterminate = !totsSeleccionats && algunSeleccionat;
                    }}
                    onChange={toggleTots}
                    aria-label="Selecciona tots els visibles"
                    title="Selecciona tots els visibles"
                  />
                </th>
                <th onClick={() => toggleSort('art_codi')} style={{ cursor: 'pointer', userSelect: 'none' }} title="Ordenar per codi">
                  Codi{sortIndicator('art_codi')}
                </th>
                <th onClick={() => toggleSort('nom_producte')} style={{ cursor: 'pointer', userSelect: 'none' }} title="Ordenar per producte">
                  Producte{sortIndicator('nom_producte')}
                </th>
                <th onClick={() => toggleSort('versio_activa')} style={{ cursor: 'pointer', userSelect: 'none' }} title="Ordenar per revisió">
                  Rev.{sortIndicator('versio_activa')}
                </th>
                <th onClick={() => toggleSort('estat')} style={{ cursor: 'pointer', userSelect: 'none' }} title="Ordenar per estat">
                  Estat{sortIndicator('estat')}
                </th>
                <th>Distribució</th>
                <th onClick={() => toggleSort('updated_at')} style={{ cursor: 'pointer', userSelect: 'none' }} title="Ordenar per data">
                  Actualitzat{sortIndicator('updated_at')}
                </th>
                <th style={{ textAlign: 'right' }}>Accions</th>
              </tr>
            </thead>
            <tbody>
              {fitxes.map((f) => {
                const checked = seleccionats.has(f.id);
                return (
                  <tr key={f.id} className={checked ? 'row-selected' : ''}>
                    <td className="table-checkbox-col">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleFitxa(f.id)}
                        aria-label={`Selecciona ${f.art_codi}`}
                      />
                    </td>
                    <td>
                      <Link to={`/fitxes/${f.id}`} style={{ fontWeight: 600 }}>
                        <code>{f.art_codi}</code>
                      </Link>
                    </td>
                    <td>
                      <Link to={`/fitxes/${f.id}`} style={{ color: 'var(--gray-800)' }}>
                        {f.nom_producte}
                      </Link>
                    </td>
                    <td style={{ textAlign: 'center', color: 'var(--gray-600)', fontWeight: 600 }}>
                      {f.versio_activa != null ? f.versio_activa : '-'}
                    </td>
                    <td>
                      {(() => {
                        const e = estatsByCodi[f.estat];
                        if (e) {
                          return <span className="badge" style={{ background: e.color, color: e.color_text }}>{e.nom}</span>;
                        }
                        return <span className={`badge ${f.estat}`}>{f.estat}</span>;
                      })()}
                    </td>
                    <td><DistBadge resum={f.dist_resum} /></td>
                    <td style={{ color: 'var(--gray-500)', fontSize: '0.85rem' }}>
                      {f.updated_at ? new Date(f.updated_at).toLocaleDateString('ca') : '-'}
                    </td>
                    <td>
                      <div className="quick-actions">
                        <button className="outline secondary btn-sm" onClick={() => descarregarPdf(f)} title="Descarregar PDF">
                          PDF
                        </button>
                        <Link to={`/fitxes/${f.id}`} className="outline secondary btn-sm" role="button">
                          Veure
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar
        count={seleccionats.size}
        usuariRol={usuari?.rol}
        onDistribuir={obrirDistribucioMassiva}
        onEditar={obrirEdicioMassiva}
        onDeseleccionar={deseleccionar}
      />
    </>
  );
}

export default LlistaFitxes;
