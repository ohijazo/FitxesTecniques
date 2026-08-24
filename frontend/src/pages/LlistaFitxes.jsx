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

// Mateixa mida de pàgina que ControlRevisions, per coherència.
const PER_PAGE = 50;

/**
 * Capçalera de taula ordenable. Abans era un <th onClick>: no era focusable,
 * no tenia rol i no comunicava per quina columna s'ordenava, de manera que
 * ordenar la taula principal era impossible amb teclat.
 */
function ThOrdenable({ col, etiqueta, children, sortBy, sortOrder, onSort, indicador }) {
  const ariaSort = sortBy !== col ? 'none' : (sortOrder === 'asc' ? 'ascending' : 'descending');
  return (
    <th aria-sort={ariaSort} style={{ padding: 0 }}>
      <button type="button" className="th-sort" onClick={() => onSort(col)}
        title={`Ordenar per ${etiqueta}`}>
        {children}{indicador}
      </button>
    </th>
  );
}

function LlistaFitxes({ usuari }) {
  const [fitxes, setFitxes] = useState([]);
  const [cerca, setCerca] = useState('');
  const [cercaAplicada, setCercaAplicada] = useState('');
  const [estat, setEstat] = useState(() => localStorage.getItem('filtre_estat') || '');
  const [sortBy, setSortBy] = useState(() => localStorage.getItem('sort_by') || 'updated_at');
  const [sortOrder, setSortOrder] = useState(() => localStorage.getItem('sort_order') || 'desc');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [pagines, setPagines] = useState(1);
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

  const carregarFitxes = async (textCerca = '', filtreEstat = estat, sb = sortBy, so = sortOrder, pag = pagina) => {
    setLoading(true);
    try {
      const params = { page: pag, per_page: PER_PAGE, sort_by: sb, sort_order: so };
      if (textCerca) params.cerca = textCerca;
      if (filtreEstat) params.estat = filtreEstat;
      const data = await api.llistarFitxes(params);
      setFitxes(data.fitxes);
      setTotal(data.total);
      setPagines(data.pages || 1);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { carregarFitxes(cerca, estat, sortBy, sortOrder, pagina); }, [estat, sortBy, sortOrder, pagina]);


  // La selecció es refereix a files concretes: si canvia el que es veu (cerca,
  // filtre o pàgina) deixa de correspondre, i d'aquí es passa directament a
  // una edició o distribució massiva. Per això es neteja.
  const canviarVista = (fn) => { setSeleccionats(new Set()); fn(); };

  const toggleSort = (col) => {
    let nextOrder = 'asc';
    if (sortBy === col) {
      nextOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    }
    setSortBy(col);
    setSortOrder(nextOrder);
    setPagina(1);
    localStorage.setItem('sort_by', col);
    localStorage.setItem('sort_order', nextOrder);
  };

  const sortIndicator = (col) => {
    if (sortBy !== col) return ' ↕';
    return sortOrder === 'asc' ? ' ▲' : ' ▼';
  };


  const handleCerca = (e) => {
    e.preventDefault();
    canviarVista(() => {
      setCercaAplicada(cerca);
      setPagina(1);
      carregarFitxes(cerca, estat, sortBy, sortOrder, 1);
    });
  };

  const handleEstat = (e) => {
    const val = e.target.value;
    canviarVista(() => {
      setEstat(val);
      setPagina(1);
      localStorage.setItem('filtre_estat', val);
    });
  };

  const hiHaFiltres = Boolean(cercaAplicada || estat);

  const esborrarFiltres = () => canviarVista(() => {
    setCerca('');
    setCercaAplicada('');
    setEstat('');
    setPagina(1);
    localStorage.setItem('filtre_estat', '');
    carregarFitxes('', '', sortBy, sortOrder, 1);
  });

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
            {hiHaFiltres
              ? `${total} ${total === 1 ? 'fitxa trobada' : 'fitxes trobades'}`
              : `${total} ${total === 1 ? 'fitxa registrada' : 'fitxes registrades'}`}
            {pagines > 1 && ` · pàgina ${pagina} de ${pagines}`}
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
          <select value={estat} onChange={handleEstat} aria-label="Filtrar per estat" style={{ margin: 0 }}>
            <option value="">Tots els estats</option>
            {estatsCatalog.map((e) => (
              <option key={e.codi} value={e.codi}>{e.nom}</option>
            ))}
          </select>
        </label>
        <button type="submit" style={{ whiteSpace: 'nowrap', marginBottom: 0 }}>Cercar</button>
        {hiHaFiltres && (
          <button type="button" className="outline secondary" onClick={esborrarFiltres}
            style={{ whiteSpace: 'nowrap', marginBottom: 0 }}>Esborrar filtres</button>
        )}
      </form>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

      {loading ? (
        <p aria-busy="true">Carregant fitxes...</p>
      ) : fitxes.length === 0 ? (
        <div className="empty-state">
          {hiHaFiltres ? (
            <>
              <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Cap fitxa coincideix amb la cerca</p>
              <p>
                {cercaAplicada && <>No hi ha cap fitxa que contingui <strong>{cercaAplicada}</strong>
                  {estat ? ' amb aquest estat' : ''}. </>}
                {!cercaAplicada && <>No hi ha cap fitxa amb aquest estat. </>}
                <button type="button" className="link-button" onClick={esborrarFiltres}>Esborrar els filtres</button>
              </p>
            </>
          ) : (
            <>
              <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Encara no hi ha cap fitxa</p>
              <p>Comença per <Link to="/fitxes/nova">crear la primera fitxa</Link>.</p>
            </>
          )}
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
                <ThOrdenable col="art_codi" etiqueta="codi" sortBy={sortBy} sortOrder={sortOrder} onSort={toggleSort} indicador={sortIndicator('art_codi')}>Codi</ThOrdenable>
                <ThOrdenable col="nom_producte" etiqueta="producte" sortBy={sortBy} sortOrder={sortOrder} onSort={toggleSort} indicador={sortIndicator('nom_producte')}>Producte</ThOrdenable>
                <ThOrdenable col="versio_activa" etiqueta="revisió" sortBy={sortBy} sortOrder={sortOrder} onSort={toggleSort} indicador={sortIndicator('versio_activa')}>Rev.</ThOrdenable>
                <ThOrdenable col="estat" etiqueta="estat" sortBy={sortBy} sortOrder={sortOrder} onSort={toggleSort} indicador={sortIndicator('estat')}>Estat</ThOrdenable>
                <th>Distribució</th>
                <ThOrdenable col="updated_at" etiqueta="data" sortBy={sortBy} sortOrder={sortOrder} onSort={toggleSort} indicador={sortIndicator('updated_at')}>Actualitzat</ThOrdenable>
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
                      {f.tipus_producte === 'comercialitzat' && (
                        <span className="badge" style={{ marginLeft: '0.5rem', background: '#e0f2fe', color: '#075985', fontSize: '0.7rem', padding: '0.1rem 0.4rem' }} title="Producte comercialitzat (PDF pujat del proveïdor)">
                          Comercial
                        </span>
                      )}
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

      {!loading && pagines > 1 && (
        <div className="pagination">
          <button type="button" className="outline secondary btn-sm"
            disabled={pagina <= 1} onClick={() => canviarVista(() => setPagina(pagina - 1))}>Anterior</button>
          <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
            Pàgina {pagina} de {pagines}
          </span>
          <button type="button" className="outline secondary btn-sm"
            disabled={pagina >= pagines} onClick={() => canviarVista(() => setPagina(pagina + 1))}>Següent</button>
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
