import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import BulkActionBar from '../components/BulkActionBar';

function _relatiu(iso) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return null;
  const diff = Date.now() - t;
  const dies = Math.floor(diff / (24 * 3600 * 1000));
  if (dies < 1) return 'avui';
  if (dies === 1) return 'ahir';
  if (dies < 30) return `fa ${dies} dies`;
  return new Date(iso).toLocaleDateString('ca');
}

function DistBadge({ resum, darrer }) {
  const dataLabel = _relatiu(darrer);
  const renderRelatiu = () => dataLabel ? (
    <div style={{ fontSize: '0.7rem', color: 'var(--gray-500)', marginTop: '0.15rem' }}>{dataLabel}</div>
  ) : null;
  if (!resum) return <span className="dist-badge dist-none" title="Sense versió activa">&mdash;</span>;
  const { ok, error, pendent } = resum;
  const title = darrer ? `Última distribució: ${new Date(darrer).toLocaleString('ca')}` : '';
  if (error > 0) return (
    <div title={title || `${error} error, ${ok} ok`}>
      <span className="dist-badge dist-error">
        <span className="dist-icon">&times;</span> {error} error
      </span>
      {renderRelatiu()}
    </div>
  );
  if (pendent > 0 && ok === 0) return (
    <div title={title || `${pendent} pendents`}>
      <span className="dist-badge dist-pending">
        <span className="dist-icon">&#9675;</span> Pendent
      </span>
      {renderRelatiu()}
    </div>
  );
  if (ok > 0 && pendent === 0) return (
    <div title={title || `${ok} distribucions ok`}>
      <span className="dist-badge dist-ok">
        <span className="dist-icon">&#10003;</span> Distribuït
      </span>
      {renderRelatiu()}
    </div>
  );
  return (
    <div title={title || `${ok} ok, ${pendent} pendents`}>
      <span className="dist-badge dist-partial">
        <span className="dist-icon">&#9681;</span> Parcial
      </span>
      {renderRelatiu()}
    </div>
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

  const seleccionarTotsFiltrats = async () => {
    try {
      const params = {};
      if (cerca) params.cerca = cerca;
      if (estat) params.estat = estat;
      const { ids } = await api.llistarIdsFitxes(params);
      setSeleccionats(new Set(ids));
      toast.success(`${ids.length} fitxes seleccionades`);
    } catch (err) {
      toast.error(`Error: ${err.message}`);
    }
  };

  const deseleccionar = () => setSeleccionats(new Set());

  const obrirEdicioMassiva = () => {
    navigate('/fitxes/bulk-edit', { state: { fitxa_ids: [...seleccionats] } });
  };

  const obrirDistribucioMassiva = () => {
    navigate('/fitxes/bulk-distribuir', { state: { fitxa_ids: [...seleccionats] } });
  };

  const exportarExcel = async () => {
    try {
      const params = new URLSearchParams();
      if (cerca) params.set('cerca', cerca);
      if (estat) params.set('estat', estat);
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/fitxes/export${params.toString() ? `?${params}` : ''}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Error exportant');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `Fitxes_tecniques_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success('Excel exportat');
    } catch (err) {
      toast.error(`Error: ${err.message}`);
    }
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
        <button type="button" className="outline secondary" onClick={exportarExcel}
          style={{ whiteSpace: 'nowrap', marginBottom: 0 }}
          title="Exporta el llistat filtrat a Excel">
          Exportar Excel
        </button>
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
        <>
        {totsSeleccionats && total > idsVisibles.length && seleccionats.size < total && (
          <div role="status" style={{
            background: '#e0f2fe', borderLeft: '4px solid #0284c7',
            padding: '0.6rem 1rem', borderRadius: '4px', marginBottom: '0.75rem',
            fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap',
          }}>
            <span style={{ flex: 1 }}>
              S'han seleccionat les {idsVisibles.length} fitxes d'aquesta pàgina.
            </span>
            <button type="button" className="btn-sm" onClick={seleccionarTotsFiltrats} style={{ margin: 0 }}>
              Seleccionar totes les {total} que coincideixen amb el filtre
            </button>
          </div>
        )}
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
                      {f.tipus_producte === 'comercialitzat' && (
                        <span
                          title="Producte comercialitzat (PDF pujat)"
                          style={{
                            marginLeft: '0.4rem',
                            padding: '1px 6px',
                            fontSize: '0.65rem',
                            fontWeight: 600,
                            background: 'var(--brand-50, #eef2ff)',
                            color: 'var(--brand, #4f46e5)',
                            border: '1px solid var(--brand-light, #c7d2fe)',
                            borderRadius: '3px',
                            verticalAlign: 'middle',
                          }}
                        >
                          Comercial
                        </span>
                      )}
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
                    <td><DistBadge resum={f.dist_resum} darrer={f.darrera_distribucio_at} /></td>
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
        </>
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
