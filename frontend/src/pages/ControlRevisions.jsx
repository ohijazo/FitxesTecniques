import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useToast } from '../components/Toast';

function StatCard({ label, value, color, onClick, active }) {
  return (
    <div
      className={`stat-card ${onClick ? 'stat-card-clickable' : ''} ${active ? 'stat-card-active' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function ControlRevisions() {
  const [dades, setDades] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandit, setExpandit] = useState(null);
  const [cerca, setCerca] = useState('');
  const [filtreEstat, setFiltreEstat] = useState('');
  const [filtreCaducada, setFiltreCaducada] = useState(false);
  const [filtreAtencio, setFiltreAtencio] = useState(false);
  const [page, setPage] = useState(1);
  const perPage = 50;
  const toast = useToast();

  useEffect(() => {
    const carregar = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/fitxes/control-revisions', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Error carregant dades');
        const data = await res.json();
        setDades(data.fitxes || data);
        setStats(data.stats || {});
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    carregar();
  }, []);

  const exportarExcel = () => {
    const token = localStorage.getItem('token');
    fetch('/api/fitxes/control-revisions/export', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Error exportant');
        return res.blob();
      })
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `Control_revisions_${new Date().toISOString().slice(0, 10)}.xlsx`;
        a.click();
        URL.revokeObjectURL(a.href);
        toast.success('Excel exportat correctament');
      })
      .catch((err) => toast.error(err.message));
  };

  // Calcular quines fitxes requereixen atenció
  const requereixAtencio = (f) => {
    return f.caducada || f.estat === 'esborrany' || f.te_errors_dist;
  };

  const dadesFiltrades = dades.filter((f) => {
    if (cerca) {
      const text = cerca.toLowerCase();
      if (!f.art_codi.toLowerCase().includes(text) &&
          !f.nom_producte.toLowerCase().includes(text) &&
          !(f.observacions || '').toLowerCase().includes(text)) return false;
    }
    if (filtreEstat && f.estat !== filtreEstat) return false;
    if (filtreCaducada && !f.caducada) return false;
    if (filtreAtencio && !requereixAtencio(f)) return false;
    return true;
  });

  const totalAtencio = dades.filter(requereixAtencio).length;

  useEffect(() => { setPage(1); }, [cerca, filtreEstat, filtreCaducada, filtreAtencio]);

  if (loading) return <p aria-busy="true">Carregant control de revisions...</p>;
  if (error) return <p style={{ color: 'var(--danger)' }}>{error}</p>;

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h2 style={{ margin: 0 }}>Control de revisions</h2>
        <button onClick={exportarExcel} className="outline">Exportar a Excel</button>
      </div>

      {/* Alerta fitxes que requereixen atenció */}
      {totalAtencio > 0 && (
        <div className="atencio-banner" onClick={() => setFiltreAtencio(!filtreAtencio)}
          role="button" tabIndex={0} style={{ cursor: 'pointer' }}>
          <strong>{totalAtencio} fitxes requereixen atenció</strong>
          <span>({stats.caducades || 0} caducades, {stats.esborranys || 0} esborranys)</span>
          <span className="badge" style={{
            background: filtreAtencio ? 'var(--danger)' : 'var(--gray-200)',
            color: filtreAtencio ? '#fff' : 'var(--gray-600)',
            marginLeft: '0.5rem'
          }}>
            {filtreAtencio ? 'Filtrant' : 'Filtrar'}
          </span>
        </div>
      )}

      {/* Estadistiques */}
      <div className="stats-grid">
        <StatCard label="Total fitxes" value={stats.total || 0} color="var(--gray-800)"
          onClick={() => { setFiltreEstat(''); setFiltreCaducada(false); setFiltreAtencio(false); }}
          active={!filtreEstat && !filtreCaducada && !filtreAtencio} />
        <StatCard label="Publicades" value={stats.publicades || 0} color="var(--success)"
          onClick={() => { setFiltreEstat(filtreEstat === 'publicada' ? '' : 'publicada'); setFiltreCaducada(false); setFiltreAtencio(false); }}
          active={filtreEstat === 'publicada'} />
        <StatCard label="En revisió" value={stats.en_revisio || 0} color="var(--warning)"
          onClick={() => { setFiltreEstat(filtreEstat === 'esborrany' ? '' : 'esborrany'); setFiltreCaducada(false); setFiltreAtencio(false); }}
          active={filtreEstat === 'esborrany'} />
        <StatCard label="Esborranys" value={stats.esborranys || 0} color="var(--gray-500)" />
        <StatCard label="Obsoletes" value={stats.obsoletes || 0} color="var(--danger)"
          onClick={() => { setFiltreEstat(filtreEstat === 'obsoleta' ? '' : 'obsoleta'); setFiltreCaducada(false); setFiltreAtencio(false); }}
          active={filtreEstat === 'obsoleta'} />
        <StatCard label="Caducades (>2 anys)" value={stats.caducades || 0}
          color={stats.caducades > 0 ? 'var(--danger)' : 'var(--success)'}
          onClick={() => { setFiltreCaducada(!filtreCaducada); setFiltreEstat(''); setFiltreAtencio(false); }}
          active={filtreCaducada} />
      </div>

      {/* Filtres */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type="search"
          placeholder="Cercar per codi, nom o observacions..."
          value={cerca}
          onChange={(e) => setCerca(e.target.value)}
          aria-label="Cercar fitxes"
          style={{ maxWidth: '300px', margin: 0 }}
        />
        <select value={filtreEstat} onChange={(e) => setFiltreEstat(e.target.value)} style={{ maxWidth: '160px', margin: 0 }}>
          <option value="">Tots els estats</option>
          <option value="publicada">Publicada</option>
          <option value="esborrany">Esborrany</option>
          <option value="obsoleta">Obsoleta</option>
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: 0, fontSize: '0.85rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={filtreCaducada} onChange={(e) => setFiltreCaducada(e.target.checked)}
            style={{ width: '16px', height: '16px', margin: 0 }} />
          Només caducades
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: 0, fontSize: '0.85rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={filtreAtencio} onChange={(e) => setFiltreAtencio(e.target.checked)}
            style={{ width: '16px', height: '16px', margin: 0 }} />
          Requereix atenció
        </label>
        <span style={{ color: 'var(--gray-500)', fontSize: '0.85rem' }}>
          {dadesFiltrades.length} fitxes
        </span>
      </div>

      {dadesFiltrades.length === 0 ? (
        <div className="empty-state">No hi ha fitxes amb els filtres seleccionats.</div>
      ) : (() => {
        const totalPages = Math.ceil(dadesFiltrades.length / perPage);
        const paginades = dadesFiltrades.slice((page - 1) * perPage, page * perPage);
        return (
        <>
        {totalPages > 1 && (
          <div className="pagination">
            <button className="outline secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
            <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>Pàgina {page} de {totalPages}</span>
            <button className="outline secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Següent</button>
          </div>
        )}
        <div className="table-wrapper">
          <table style={{ fontSize: '0.82rem', whiteSpace: 'nowrap' }}>
            <thead>
              <tr>
                <th>Codi</th>
                <th>Nom article</th>
                <th>Estat</th>
                <th>Rev.</th>
                <th>Data rev.</th>
                <th>Data compr.</th>
                <th>Client</th>
                <th>Den. jurídica</th>
                <th>Composicio</th>
                <th>Vida útil</th>
                <th>W</th>
                <th>P/L</th>
                <th>Proteïna</th>
                <th>Gluten</th>
                <th>Cendres</th>
                <th>Obs.</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {paginades.map((f) => {
                const rowClass = f.caducada ? 'row-caducada' : requereixAtencio(f) ? 'row-atencio' : '';
                return (
                <>
                  <tr key={f.id} className={rowClass}>
                    <td>
                      <Link to={`/fitxes/${f.id}`} style={{ fontWeight: 600 }}>{f.art_codi}</Link>
                    </td>
                    <td style={{ whiteSpace: 'normal', maxWidth: '200px' }}>{f.nom_producte}</td>
                    <td>
                      <span className={`badge ${f.estat}`}>{f.estat}</span>
                      {f.caducada && <span className="badge error" style={{ marginLeft: '4px', fontSize: '0.65rem' }}>CAD</span>}
                    </td>
                    <td style={{ textAlign: 'center', fontWeight: 600 }}>{f.revisio}</td>
                    <td>{f.data_revisio}</td>
                    <td>{f.data_comprovacio}</td>
                    <td style={{ textAlign: 'center' }}>{f.es_client ? 'Si' : ''}</td>
                    <td style={{ whiteSpace: 'normal', maxWidth: '130px', fontSize: '0.78rem' }}>{f.denominacio_juridica}</td>
                    <td style={{ whiteSpace: 'normal', maxWidth: '110px', fontSize: '0.78rem' }}>{f.composicio}</td>
                    <td style={{ whiteSpace: 'normal', maxWidth: '100px', fontSize: '0.78rem' }}>{f.vida_util}</td>
                    <td>{f.w || ''}</td>
                    <td>{f.pl || ''}</td>
                    <td>{f.proteina || ''}</td>
                    <td>{f.gluten || ''}</td>
                    <td>{f.cendres || ''}</td>
                    <td style={{ whiteSpace: 'normal', maxWidth: '130px', fontSize: '0.78rem', color: 'var(--gray-500)' }}>
                      {f.observacions}
                    </td>
                    <td>
                      <button className="outline secondary btn-sm" onClick={() => setExpandit(expandit === f.id ? null : f.id)}
                        style={{ fontSize: '0.72rem' }}>
                        {expandit === f.id ? 'Amagar' : 'Canvis'}
                      </button>
                    </td>
                  </tr>
                  {expandit === f.id && (
                    <tr key={`${f.id}-hist`}>
                      <td colSpan={17} style={{ background: 'var(--gray-50)', padding: '0.75rem 1rem' }}>
                        <strong style={{ color: 'var(--brand)', fontSize: '0.85rem' }}>Historial de canvis</strong>
                        {f.historial.length === 0 ? (
                          <p style={{ color: 'var(--gray-400)', margin: '0.25rem 0', fontSize: '0.82rem' }}>Sense historial.</p>
                        ) : (
                          <div style={{ marginTop: '0.25rem' }}>
                            {f.historial.map((h, i) => (
                              <div key={i} style={{ fontSize: '0.82rem', padding: '3px 0', borderBottom: '1px solid var(--gray-200)' }}>
                                <strong>Rev. {h.num_versio}</strong>
                                <span style={{ color: 'var(--gray-400)', marginLeft: '0.5rem' }}>
                                  {h.data} {h.autor && `\u00b7 ${h.autor}`}
                                </span>
                                <span style={{ marginLeft: '0.5rem', color: 'var(--gray-600)' }}>{h.descripcio}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
                );
              })}
            </tbody>
          </table>
        </div>
        </>
        );
      })()}
    </>
  );
}

export default ControlRevisions;
