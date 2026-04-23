import { useState, useEffect } from 'react';
import { useParams, useLocation, Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { PdfDocumentView } from '../components/FitxaForm';
import RichEditor from '../components/RichEditor';
import DOMPurify from 'dompurify';


function VerificarPanel({ fitxaId, onClose }) {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    fetch(`/api/fitxes/${fitxaId}/verificar`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.error) setError(data.error);
        else setResult(data);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [fitxaId]);

  if (loading) return <div className="card"><p aria-busy="true">Comparant dades amb el PDF original...</p></div>;
  if (error) return (
    <div className="card">
      <p style={{ color: 'var(--danger)' }}>{error}</p>
      <button className="outline secondary btn-sm" onClick={onClose}>Tancar</button>
    </div>
  );

  const ok = result.total_diferencies === 0;

  return (
    <div className="card" style={{ border: `2px solid ${ok ? 'var(--success)' : 'var(--warning)'}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0 }}>Verificació: App vs PDF original</h3>
        <button className="outline secondary btn-sm" onClick={onClose}>Tancar</button>
      </div>

      <div style={{ display: 'flex', gap: '2rem', marginBottom: '1rem', fontSize: '0.88rem' }}>
        <div>Revisió PDF: <strong>{result.pdf_rev}</strong></div>
        <div>Revisió App: <strong>{result.app_rev}</strong></div>
        <div>Camps PDF: <strong>{result.pdf_camps}</strong></div>
        <div>Camps App: <strong>{result.app_camps}</strong></div>
      </div>

      {ok ? (
        <div style={{ background: 'var(--success-bg)', color: 'var(--success)', padding: '1rem', borderRadius: 'var(--radius)', fontWeight: 600 }}>
          Les dades de l'app coincideixen amb el PDF original.
        </div>
      ) : (
        <>
          <div style={{ background: 'var(--warning-bg)', color: 'var(--warning)', padding: '0.75rem 1rem', borderRadius: 'var(--radius)', marginBottom: '1rem', fontWeight: 600 }}>
            {result.total_diferencies} diferències trobades
          </div>
          <div className="table-wrapper">
            <table style={{ fontSize: '0.82rem' }}>
              <thead>
                <tr>
                  <th>Camp</th>
                  <th>Tipus</th>
                  <th>Valor al PDF</th>
                  <th>Valor a l'App</th>
                </tr>
              </thead>
              <tbody>
                {result.diferencies.map((d, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{d.camp}{d.fila ? ` (fila ${d.fila})` : ''}</td>
                    <td><span className="badge" style={{ background: 'var(--gray-100)', color: 'var(--gray-600)' }}>{d.tipus}</span></td>
                    <td style={{ whiteSpace: 'pre-line', maxWidth: '300px', fontSize: '0.8rem', color: 'var(--success)' }}>
                      {typeof d.pdf === 'string' ? d.pdf : JSON.stringify(d.pdf)}
                    </td>
                    <td style={{ whiteSpace: 'pre-line', maxWidth: '300px', fontSize: '0.8rem', color: 'var(--danger)' }}>
                      {typeof d.app === 'string' ? d.app : JSON.stringify(d.app)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function DistribuirPanel({ fitxaId, distribucions, onDone, onClose }) {
  const [destins, setDestins] = useState([]);
  const [selected, setSelected] = useState({});
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [resultats, setResultats] = useState([]);
  const toast = useToast();

  useEffect(() => {
    api.llistarDestins().then((data) => {
      const actius = data.filter((d) => d.actiu);
      setDestins(actius);
      const sel = {};
      actius.forEach((d) => { sel[d.id] = true; });
      setSelected(sel);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const destiJaDistribuit = (destiId) => {
    return distribucions.some((d) => d.desti_id === destiId && d.estat === 'ok');
  };

  const toggle = (id) => setSelected((prev) => ({ ...prev, [id]: !prev[id] }));

  const distribuir = async () => {
    const ids = Object.entries(selected).filter(([, v]) => v).map(([k]) => parseInt(k));
    if (ids.length === 0) return;
    setSending(true);
    const res = [];
    for (const destiId of ids) {
      try {
        const r = await api.distribuirDesti(fitxaId, destiId);
        res.push({ desti: destins.find((d) => d.id === destiId)?.nom, ok: true, url: r.missatge_error });
      } catch (err) {
        res.push({ desti: destins.find((d) => d.id === destiId)?.nom, ok: false, error: err.message });
      }
    }
    setResultats(res);
    setSending(false);

    const oks = res.filter((r) => r.ok).length;
    const errors = res.filter((r) => !r.ok).length;
    if (errors > 0) {
      toast.warning(`Distribució: ${oks} ok, ${errors} errors`);
    } else {
      toast.success(`Distribuït correctament a ${oks} destins`);
    }
    onDone();
  };

  if (loading) return <p aria-busy="true">Carregant destins...</p>;

  return (
    <div className="card" style={{ border: '2px solid var(--brand-light)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0 }}>Distribuir fitxa</h3>
        <button className="outline secondary btn-sm" onClick={onClose}>Tancar</button>
      </div>

      {destins.length === 0 ? (
        <p style={{ color: 'var(--gray-500)' }}>No hi ha destins de distribució configurats. Configura'ls a Admin &gt; Destins.</p>
      ) : (
        <>
          <p style={{ fontSize: '0.88rem', color: 'var(--gray-500)', marginBottom: '1rem' }}>
            Selecciona els destins on vols distribuir la versió activa:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.25rem' }}>
            {destins.map((d) => {
              const jaOk = destiJaDistribuit(d.id);
              return (
                <label key={d.id} className="desti-check" style={{
                  display: 'flex', alignItems: 'center', gap: '0.75rem',
                  padding: '0.7rem 1rem', border: '1px solid var(--gray-200)',
                  borderRadius: 'var(--radius)', cursor: 'pointer', margin: 0,
                  background: selected[d.id] ? 'var(--brand-50)' : '#fff',
                  borderColor: selected[d.id] ? 'var(--brand)' : 'var(--gray-200)',
                }}>
                  <input
                    type="checkbox"
                    checked={selected[d.id] || false}
                    onChange={() => toggle(d.id)}
                    style={{ width: '18px', height: '18px', margin: 0, accentColor: 'var(--brand)' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{d.nom}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>
                      Tipus: {d.tipus.toUpperCase()} &middot; Patro: {d.patro_nom_fitxer}
                    </div>
                  </div>
                  {jaOk && (
                    <span className="badge ok" style={{ fontSize: '0.72rem' }}>Ja distribuït</span>
                  )}
                </label>
              );
            })}
          </div>

          {resultats.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              {resultats.map((r, i) => (
                <div key={i} style={{
                  padding: '0.4rem 0.75rem', fontSize: '0.85rem', borderRadius: '4px', marginBottom: '4px',
                  background: r.ok ? 'var(--success-bg)' : 'var(--danger-bg)',
                  color: r.ok ? 'var(--success)' : 'var(--danger)',
                }}>
                  {r.desti}: {r.ok ? (
                    <>Distribuït {r.url && <a href={r.url} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>{r.url}</a>}</>
                  ) : r.error}
                </div>
              ))}
            </div>
          )}

          <button onClick={distribuir} disabled={sending || !Object.values(selected).some(Boolean)} aria-busy={sending}>
            {sending ? 'Distribuint...' : 'Distribuir als destins seleccionats'}
          </button>
        </>
      )}
    </div>
  );
}

const ESTAT_VERSIO_LABELS = {
  esborrany: { label: 'Esborrany', cls: 'esborrany' },
  en_revisio: { label: 'En revisió', cls: 'pendent' },
  aprovada: { label: 'Aprovada', cls: 'ok' },
  publicada: { label: 'Publicada', cls: 'ok' },
};

function DiffView({ fitxaId, v1Id, v2Id, onClose }) {
  const [loading, setLoading] = useState(true);
  const [diff, setDiff] = useState(null);

  useEffect(() => {
    api.diffVersions(fitxaId, v1Id, v2Id)
      .then(setDiff)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [fitxaId, v1Id, v2Id]);

  if (loading) return <p aria-busy="true">Comparant versions...</p>;
  if (!diff) return <p style={{ color: 'var(--danger)' }}>Error comparant versions.</p>;

  return (
    <div className="card" style={{ border: '2px solid var(--brand-light)', marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0 }}>
          Canvis entre Rev. {diff.v1.num} i Rev. {diff.v2.num}
        </h3>
        <button className="outline secondary btn-sm" onClick={onClose}>Tancar</button>
      </div>
      <div style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginBottom: '1rem' }}>
        <span>Rev. {diff.v1.num} ({diff.v1.autor}) &rarr; Rev. {diff.v2.num} ({diff.v2.autor})</span>
        <span style={{ marginLeft: '1rem' }}>{diff.total_canvis} canvis</span>
      </div>

      {diff.total_canvis === 0 ? (
        <div style={{ background: 'var(--success-bg)', color: 'var(--success)', padding: '1rem', borderRadius: 'var(--radius)' }}>
          Cap diferència trobada entre les dues versions.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {diff.canvis.map((c, i) => (
            <div key={i} className="diff-item">
              <div className="diff-camp">{c.camp}</div>
              {c.tipus === 'afegit' && (
                <div className="diff-added">+ {c.nou}</div>
              )}
              {c.tipus === 'eliminat' && (
                <div className="diff-removed">- {c.antic}</div>
              )}
              {c.tipus === 'modificat' && (
                <>
                  <div className="diff-removed">- {c.antic}</div>
                  <div className="diff-added">+ {c.nou}</div>
                </>
              )}
              {c.tipus === 'taula' && (
                <table style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                  <tbody>
                    {c.files.map((f, fi) => {
                      if (f.tipus === 'igual') return null;
                      return (
                        <tr key={fi}>
                          <td style={{ width: '60px', fontWeight: 600, color: 'var(--gray-500)' }}>Fila {fi + 1}</td>
                          {f.tipus === 'afegit' && (
                            <td className="diff-added">+ {f.valor?.parametre}: {f.valor?.valor}</td>
                          )}
                          {f.tipus === 'eliminat' && (
                            <td className="diff-removed">- {f.valor?.parametre}: {f.valor?.valor}</td>
                          )}
                          {f.tipus === 'modificat' && (
                            <td>
                              <div className="diff-removed">- {f.antic?.parametre}: {f.antic?.valor}</div>
                              <div className="diff-added">+ {f.nou?.parametre}: {f.nou?.valor}</div>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EsborrarVersioModal({ fitxa, versio, fitxaId, onDone, onClose }) {
  const [motiu, setMotiu] = useState('');
  const [password, setPassword] = useState('');
  const [destins, setDestins] = useState([]);
  const [selectedDestins, setSelectedDestins] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const toast = useToast();

  useEffect(() => {
    api.llistarDestins().then((data) => {
      const actius = data.filter((d) => d.actiu);
      setDestins(actius);
    }).catch(() => {});
  }, []);

  const toggleDesti = (id) => setSelectedDestins((prev) => ({ ...prev, [id]: !prev[id] }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!motiu.trim()) { setError('Cal indicar un motiu'); return; }
    if (!password) { setError('Cal la contrasenya'); return; }

    const esborrar_destins = Object.entries(selectedDestins)
      .filter(([, v]) => v).map(([k]) => parseInt(k));

    setLoading(true);
    setError(null);
    try {
      const result = await api.esborrarUltimaVersio(fitxaId, { motiu, password, esborrar_destins });
      toast.success(result.message);
      onDone();
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, color: 'var(--danger)' }}>Esborrar versió {versio.num_versio}</h3>
          <button className="outline secondary btn-sm" onClick={onClose}>&times;</button>
        </div>

        <div style={{ background: 'var(--danger-bg)', padding: '0.75rem 1rem', borderRadius: 'var(--radius)', marginBottom: '1rem', fontSize: '0.88rem' }}>
          Estàs a punt d'esborrar la <strong>Rev. {versio.num_versio}</strong> de la fitxa <strong>{fitxa.art_codi}</strong>.
          S'activarà la versió anterior. Aquesta acció és irreversible.
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            Motiu *
            <textarea value={motiu} onChange={(e) => setMotiu(e.target.value)}
              required placeholder="Ex: Error en les dades, versió duplicada..."
              rows={2} />
          </label>

          {destins.length > 0 && (
            <fieldset style={{ marginBottom: '1rem' }}>
              <legend style={{ fontSize: '0.85rem', fontWeight: 600 }}>Esborrar també dels destins:</legend>
              {destins.map((d) => (
                <label key={d.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', margin: '0.3rem 0' }}>
                  <input type="checkbox" checked={selectedDestins[d.id] || false}
                    onChange={() => toggleDesti(d.id)} style={{ width: 'auto', margin: 0 }} />
                  {d.nom} <span style={{ color: 'var(--gray-400)', fontSize: '0.8rem' }}>({d.tipus.toUpperCase()})</span>
                </label>
              ))}
            </fieldset>
          )}

          <label>
            Confirma amb la teva contrasenya *
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              required placeholder="Contrasenya" autoComplete="current-password" />
          </label>

          {error && <p style={{ color: 'var(--danger)', fontSize: '0.88rem', marginBottom: '0.5rem' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="outline secondary" onClick={onClose}>Cancel·lar</button>
            <button type="submit" disabled={loading} aria-busy={loading}
              style={{ background: 'var(--danger)', borderColor: 'var(--danger)' }}>
              {loading ? 'Esborrant...' : 'Confirmar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function VersionsSection({ fitxa, fitxaId, onPublicar, onVistaPrevia, onRefresh }) {
  const [diffPair, setDiffPair] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const versions = fitxa.versions || [];

  const mostrarDiff = (v, i) => {
    if (i < versions.length - 1) {
      setDiffPair({ v1Id: versions[i + 1].id, v2Id: v.id });
    }
  };

  if (versions.length === 0) {
    return <p style={{ color: 'var(--gray-500)' }}>Cap versió.</p>;
  }

  return (
    <>
      {versions.length > 1 && (
        <div style={{ marginBottom: '1rem' }}>
          <button className="outline" style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}
            onClick={() => setShowDeleteModal(true)}>
            Esborrar última versió (Rev. {versions[0].num_versio})
          </button>
        </div>
      )}

      {showDeleteModal && (
        <EsborrarVersioModal
          fitxa={fitxa} versio={versions[0]} fitxaId={fitxaId}
          onDone={async () => { await onRefresh(); setShowDeleteModal(false); }}
          onClose={() => setShowDeleteModal(false)}
        />
      )}

      {diffPair && (
        <DiffView fitxaId={fitxaId} v1Id={diffPair.v1Id} v2Id={diffPair.v2Id}
          onClose={() => setDiffPair(null)} />
      )}

      <div className="version-timeline">
        {versions.map((v, i) => {
          const hasPrev = i < versions.length - 1;

          return (
            <div key={v.id} className={`version-item ${v.activa ? 'active' : ''}`}>
              <div className="version-dot" />
              <div className="version-content">
                <div className="version-header">
                  <span className="version-num">Rev. {v.num_versio}</span>
                  {v.activa && <span className="badge ok">Activa</span>}
                </div>
                <div className="version-desc">{v.descripcio_canvi}</div>
                <div className="version-meta">
                  <span>{v.created_at ? new Date(v.created_at).toLocaleDateString('ca') : '-'}</span>
                  {v.created_by && <span>per {v.created_by}</span>}
                </div>
                <div className="version-actions">
                  {hasPrev && (
                    <button className="outline btn-sm" onClick={() => mostrarDiff(v, i)}>
                      Veure canvis
                    </button>
                  )}
                  <button className="outline btn-sm" onClick={() => onVistaPrevia(v.id)}>
                    Veure PDF
                  </button>
                  {!v.activa && (
                    <button className="outline secondary btn-sm" onClick={() => onPublicar(v.id)}>
                      Restaurar
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function DuplicarModal({ fitxaId, fitxaArtCodi, fitxaNom, onClose }) {
  const [artCodi, setArtCodi] = useState('');
  const [nomProducte, setNomProducte] = useState(fitxaNom || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const toast = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!artCodi.trim()) { setError("Cal indicar el nou codi d'article"); return; }
    setLoading(true);
    setError(null);
    try {
      const nova = await api.duplicarFitxa(fitxaId, { art_codi: artCodi.trim(), nom_producte: nomProducte });
      toast.success(`Fitxa duplicada: ${artCodi}`);
      onClose();
      setTimeout(() => navigate(`/fitxes/${nova.id}`), 100);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, color: 'var(--brand)' }}>Duplicar fitxa</h3>
          <button className="outline secondary btn-sm" onClick={onClose}>&times;</button>
        </div>

        <div style={{ background: 'var(--brand-50)', padding: '0.75rem 1rem', borderRadius: 'var(--radius)', marginBottom: '1rem', fontSize: '0.88rem' }}>
          Es crearà una còpia de <strong>{fitxaArtCodi} - {fitxaNom}</strong> amb un nou codi d'article.
          No es copiaran les versions ni les distribucions.
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            Nou codi d'article *
            <input type="text" value={artCodi} onChange={(e) => setArtCodi(e.target.value)}
              required placeholder="Ex: 99999" autoFocus />
          </label>
          <label>
            Nom del producte
            <input type="text" value={nomProducte} onChange={(e) => setNomProducte(e.target.value)}
              placeholder="Nom del producte" />
          </label>

          {error && <p style={{ color: 'var(--danger)', fontSize: '0.88rem', marginBottom: '0.5rem' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="outline secondary" onClick={onClose}>Cancel·lar</button>
            <button type="submit" disabled={loading} aria-busy={loading}>
              {loading ? 'Duplicant...' : 'Duplicar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EliminarModal({ fitxa, onDone, onClose, onRefresh }) {
  const [motiu, setMotiu] = useState('');
  const [password, setPassword] = useState('');
  const [accio, setAccio] = useState('inactivar'); // 'inactivar' | 'eliminar'
  const [destins, setDestins] = useState([]);
  const [selectedDestins, setSelectedDestins] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const toast = useToast();

  useEffect(() => {
    api.llistarDestins().then((data) => {
      const actius = data.filter((d) => d.actiu);
      setDestins(actius);
      const sel = {};
      actius.forEach((d) => { sel[d.id] = true; });
      setSelectedDestins(sel);
    }).catch(() => {});
  }, []);

  const toggleDesti = (id) => setSelectedDestins((prev) => ({ ...prev, [id]: !prev[id] }));

  const handleEliminar = async (e) => {
    e.preventDefault();
    if (!motiu.trim()) { setError('Cal indicar un motiu'); return; }
    if (!password) { setError('Cal la contrasenya'); return; }

    const esborrar_destins = Object.entries(selectedDestins)
      .filter(([, v]) => v).map(([k]) => parseInt(k));

    setLoading(true);
    setError(null);
    try {
      await api.eliminarFitxa(fitxa.id, {
        motiu, password, esborrar_destins,
        nomes_inactivar: accio === 'inactivar',
      });
      if (accio === 'inactivar') {
        toast.success(`Fitxa ${fitxa.art_codi} marcada com a inactiva`);
        onRefresh();
        onClose();
      } else {
        toast.success(`Fitxa ${fitxa.art_codi} eliminada`);
        onDone();
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, color: 'var(--danger)' }}>Eliminar fitxa</h3>
          <button className="outline secondary btn-sm" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleEliminar}>
          {/* Tipus d'acció */}
          <fieldset style={{ marginBottom: '1rem' }}>
            <legend style={{ fontSize: '0.85rem', fontWeight: 600 }}>Què vols fer?</legend>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', cursor: 'pointer', margin: '0.4rem 0' }}>
              <input type="radio" name="accio" checked={accio === 'inactivar'} onChange={() => setAccio('inactivar')}
                style={{ width: 'auto', margin: '4px 0 0 0' }} />
              <div>
                <strong>Inactivar</strong>
                <div style={{ fontSize: '0.82rem', color: 'var(--gray-500)' }}>
                  La fitxa es manté a l'aplicació amb estat "inactiva" però s'esborra dels destins seleccionats.
                </div>
              </div>
            </label>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', cursor: 'pointer', margin: '0.4rem 0' }}>
              <input type="radio" name="accio" checked={accio === 'eliminar'} onChange={() => setAccio('eliminar')}
                style={{ width: 'auto', margin: '4px 0 0 0' }} />
              <div>
                <strong style={{ color: 'var(--danger)' }}>Eliminar definitivament</strong>
                <div style={{ fontSize: '0.82rem', color: 'var(--gray-500)' }}>
                  La fitxa, versions i distribucions s'esborren completament. Irreversible.
                </div>
              </div>
            </label>
          </fieldset>

          <label>
            Motiu *
            <textarea value={motiu} onChange={(e) => setMotiu(e.target.value)}
              required placeholder="Ex: Fitxa duplicada, producte descatalogat..."
              rows={2} />
          </label>

          {destins.length > 0 && (
            <fieldset style={{ marginBottom: '1rem' }}>
              <legend style={{ fontSize: '0.85rem', fontWeight: 600 }}>Esborrar dels destins:</legend>
              {destins.map((d) => (
                <label key={d.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', margin: '0.3rem 0' }}>
                  <input type="checkbox" checked={selectedDestins[d.id] || false}
                    onChange={() => toggleDesti(d.id)} style={{ width: 'auto', margin: 0 }} />
                  {d.nom} <span style={{ color: 'var(--gray-400)', fontSize: '0.8rem' }}>({d.tipus.toUpperCase()})</span>
                </label>
              ))}
            </fieldset>
          )}

          <label>
            Confirma amb la teva contrasenya *
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              required placeholder="Contrasenya" autoComplete="current-password" />
          </label>

          {error && <p style={{ color: 'var(--danger)', fontSize: '0.88rem', marginBottom: '0.5rem' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="outline secondary" onClick={onClose}>Cancel·lar</button>
            <button type="submit" disabled={loading} aria-busy={loading}
              style={accio === 'eliminar' ? { background: 'var(--danger)', borderColor: 'var(--danger)' } : {}}>
              {loading ? 'Processant...' : accio === 'inactivar' ? 'Inactivar fitxa' : 'Eliminar definitivament'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DetallFitxa() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();
  const usuari = JSON.parse(localStorage.getItem('usuari') || '{}');
  const [fitxa, setFitxa] = useState(null);
  const [distribucions, setDistribucions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const openDist = location.state?.openDistribuir || false;
  const [section, setSection] = useState(openDist ? 'distribucions' : 'contingut');
  const [showDistribuir, setShowDistribuir] = useState(openDist);
  const [verif, setVerif] = useState(null);
  const [showVerifDetails, setShowVerifDetails] = useState(false);

  const carregarDades = async () => {
    try {
      const [f, d] = await Promise.all([
        api.detallFitxa(id),
        api.llistarDistribucions(id),
      ]);
      setFitxa(f);
      setDistribucions(d);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const verificarAuto = () => {
    const token = localStorage.getItem('token');
    fetch(`/api/fitxes/${id}/verificar`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.error) {
          setVerif({ ok: null, error: data.error });
        } else {
          setVerif({
            ok: data.total_diferencies === 0,
            diffs: data.total_diferencies,
            data: data,
          });
        }
      })
      .catch(() => setVerif({ ok: null, error: 'Error de connexió' }));
  };

  useEffect(() => { carregarDades(); }, [id]);
  useEffect(() => { if (id) verificarAuto(); }, [id]);

  const publicarVersio = async (vid) => {
    try {
      await api.publicarVersio(id, vid);
      toast.success('Versió publicada correctament');
      carregarDades();
    } catch (err) {
      toast.error(`Error publicant: ${err.message}`);
    }
  };

  const guardarObservacions = async (html) => {
    try {
      await api.actualitzarObservacions(id, html);
      toast.success('Observacions guardades');
      carregarDades();
      setEditingObs(false);
    } catch (err) {
      toast.error(`Error: ${err.message}`);
    }
  };

  const obrirDistribuir = () => {
    setShowDistribuir(true);
    setSection('distribucions');
  };

  const [showEliminar, setShowEliminar] = useState(false);
  const [showDuplicar, setShowDuplicar] = useState(false);
  const [editingObs, setEditingObs] = useState(false);
  const [obsText, setObsText] = useState('');

  const descarregarPdf = (versioId) => {
    const token = localStorage.getItem('token');
    const url = versioId
      ? `/api/fitxes/${id}/pdf?versio_id=${versioId}`
      : `/api/fitxes/${id}/pdf`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error('Error descarregant el PDF');
        return res.blob();
      })
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${fitxa.art_codi}.pdf`;
        a.click();
        URL.revokeObjectURL(a.href);
        toast.success('PDF descarregat');
      })
      .catch((err) => toast.error(`Error: ${err.message}`));
  };

  const vistaPrevia = (versioId) => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
    setPdfLoading(true);
    setSection('pdf');
    const token = localStorage.getItem('token');
    const url = versioId
      ? `/api/fitxes/${id}/pdf?versio_id=${versioId}`
      : `/api/fitxes/${id}/pdf`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error('Error carregant el PDF');
        return res.blob();
      })
      .then((blob) => {
        setPdfUrl(URL.createObjectURL(blob));
      })
      .catch((err) => toast.error(`Error: ${err.message}`))
      .finally(() => setPdfLoading(false));
  };

  const tancarPrevia = () => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
    setSection('contingut');
  };

  if (loading) return <p aria-busy="true">Carregant...</p>;
  if (error) return <p style={{ color: 'var(--danger)' }}>{error}</p>;
  if (!fitxa) return null;

  const versioActiva = fitxa.versions?.find((v) => v.activa);
  const contingut = versioActiva?.contingut || fitxa.versions?.[0]?.contingut;

  return (
    <>
      {/* Capsalera */}
      <div className="detail-header">
        <div>
          <h2 style={{ margin: 0 }}>{fitxa.nom_producte}</h2>
          <div className="detail-meta">
            <code className="detail-code">{fitxa.art_codi}</code>
            <span className={`badge ${fitxa.estat}`}>{fitxa.estat}</span>
            {fitxa.es_client && <span className="badge" style={{ background: '#e3f2fd', color: '#1565c0' }}>Client</span>}
            {versioActiva && <span style={{ color: 'var(--gray-500)' }}>Rev. {versioActiva.num_versio}</span>}
            {verif && verif.ok === true && (
              <span className="verif-ok" title="Les dades coincideixen amb el PDF del FTP">Verificat</span>
            )}
            {verif && verif.ok === false && (
              <span className="verif-warn" title={`${verif.diffs} diferències amb el PDF del FTP`}
                onClick={() => setShowVerifDetails(!showVerifDetails)} style={{ cursor: 'pointer' }}>
                {verif.diffs} dif.
              </span>
            )}
          </div>
        </div>
        <div className="detail-actions">
          <Link to={`/fitxes/${id}/editar`} role="button" className="outline">
            Editar / Nova versió
          </Link>
          <button onClick={() => vistaPrevia()} className="outline">
            Vista prèvia PDF
          </button>
          <button onClick={() => descarregarPdf()} className="outline secondary">
            Descarregar PDF
          </button>
          {versioActiva && (
            <button onClick={obrirDistribuir}>
              Distribuir
            </button>
          )}
          <button className="outline secondary" onClick={() => setShowDuplicar(true)}>
            Duplicar
          </button>
          {usuari.rol === 'admin' && (
            <button className="outline" style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}
              onClick={() => setShowEliminar(true)}>
              Eliminar
            </button>
          )}
        </div>
      </div>

      {/* Vista prèvia PDF */}
      {pdfLoading && <p aria-busy="true">Carregant vista prèvia...</p>}

      {pdfUrl && (
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <strong>Vista prèvia del PDF</strong>
            <button className="outline secondary btn-sm" onClick={tancarPrevia}>Tancar</button>
          </div>
          <iframe
            src={pdfUrl}
            className="pdf-preview"
            title="Vista prèvia PDF"
          />
        </div>
      )}

      {/* Seccions principals */}
      {!pdfUrl && (
        <>
          <div className="detail-sections">
            <button type="button" className={section === 'contingut' ? 'active' : ''} onClick={() => setSection('contingut')}>
              Contingut
            </button>
            <button type="button" className={section === 'observacions' ? 'active' : ''} onClick={() => setSection('observacions')}>
              Observacions
            </button>
            <button type="button" className={section === 'versions' ? 'active' : ''} onClick={() => setSection('versions')}>
              Versions ({fitxa.versions?.length || 0})
            </button>
            <button type="button" className={section === 'distribucions' ? 'active' : ''} onClick={() => setSection('distribucions')}>
              Distribucions ({distribucions.length})
            </button>
          </div>

          {section === 'contingut' && (
            <>
              {showVerifDetails && verif?.data && (
                <VerificarPanel fitxaId={id} onClose={() => setShowVerifDetails(false)} />
              )}
              <PdfDocumentView contingut={contingut} versio={versioActiva} />
            </>
          )}

          {section === 'observacions' && (
            <div className="card">
              {editingObs ? (
                <>
                  <RichEditor value={obsText} onChange={setObsText} />
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                    <button onClick={() => guardarObservacions(obsText)}>Guardar</button>
                    <button className="outline secondary" onClick={() => setEditingObs(false)}>Cancel·lar</button>
                  </div>
                </>
              ) : (
                <>
                  {fitxa.observacions ? (
                    <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(fitxa.observacions) }}
                      style={{ fontSize: '0.92rem', lineHeight: 1.6, color: 'var(--gray-700)' }} />
                  ) : (
                    <p style={{ color: 'var(--gray-400)', fontStyle: 'italic' }}>Sense observacions.</p>
                  )}
                  <button className="outline btn-sm" style={{ marginTop: '0.75rem' }}
                    onClick={() => { setObsText(fitxa.observacions || ''); setEditingObs(true); }}>
                    Editar observacions
                  </button>
                </>
              )}
            </div>
          )}

          {section === 'versions' && (
            <VersionsSection fitxa={fitxa} fitxaId={id}
              onPublicar={publicarVersio} onVistaPrevia={vistaPrevia}
              onRefresh={carregarDades} setMsg={() => {}} />
          )}

          {section === 'distribucions' && (
            <>
              {showDistribuir && versioActiva && (
                <DistribuirPanel
                  fitxaId={id}
                  distribucions={distribucions}
                  onDone={carregarDades}
                  onClose={() => setShowDistribuir(false)}
                />
              )}

              {!showDistribuir && versioActiva && (
                <div style={{ marginBottom: '1rem' }}>
                  <button onClick={() => setShowDistribuir(true)} className="outline">
                    Distribuir a nous destins
                  </button>
                </div>
              )}

              <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Historial de distribucions</h3>
              {distribucions.length === 0 ? (
                <p style={{ color: 'var(--gray-500)' }}>Cap distribució registrada.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Desti</th>
                      <th>Rev.</th>
                      <th>Estat</th>
                      <th>Data</th>
                      <th>Usuari</th>
                      <th>Detall</th>
                    </tr>
                  </thead>
                  <tbody>
                    {distribucions.map((d) => (
                      <tr key={d.id}>
                        <td style={{ fontWeight: 500 }}>{d.desti}</td>
                        <td style={{ textAlign: 'center', fontWeight: 600 }}>{d.num_versio != null ? d.num_versio : '-'}</td>
                        <td><span className={`badge ${d.estat}`}>{d.estat}</span></td>
                        <td style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                          {d.executat_at ? new Date(d.executat_at).toLocaleString('ca') : 'Pendent'}
                        </td>
                        <td style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>{d.executat_by || '-'}</td>
                        <td style={{ fontSize: '0.85rem' }}>
                          {d.estat === 'ok' && d.missatge_error && d.missatge_error.startsWith('http') ? (
                            <a href={d.missatge_error} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--brand)' }}>
                              {d.missatge_error}
                            </a>
                          ) : d.estat === 'error' ? (
                            <span style={{ color: 'var(--danger)' }}>{d.missatge_error || ''}</span>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </>
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <Link to="/" className="outline secondary" role="button">
          &larr; Tornar a la llista
        </Link>
      </div>

      {showEliminar && (
        <EliminarModal
          fitxa={fitxa}
          onDone={() => navigate('/')}
          onRefresh={carregarDades}
          onClose={() => setShowEliminar(false)}
        />
      )}

      {showDuplicar && (
        <DuplicarModal
          fitxaId={fitxa.id}
          fitxaArtCodi={fitxa.art_codi}
          fitxaNom={fitxa.nom_producte}
          onClose={() => setShowDuplicar(false)}
        />
      )}
    </>
  );
}

export default DetallFitxa;
