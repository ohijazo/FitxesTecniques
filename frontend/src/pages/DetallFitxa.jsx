import { useState, useEffect } from 'react';
import { useParams, useLocation, Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import { PdfDocumentView, definirEtiquetesIdioma } from '../components/FitxaForm';
import RichEditor from '../components/RichEditor';
import { useEscapeKey } from '../components/useEscapeKey';
import RetirarDestiModal from '../components/RetirarDestiModal';
import ComprovarDestinsPanel from '../components/ComprovarDestinsPanel';
import BadgeVerificacio from '../components/BadgeVerificacio';
import IdiomesPanel, { combinarTraduccio } from '../components/IdiomesPanel';
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

/* Nom del fitxer al destí. Mateixa regla que _generar_nom_fitxer i
   _nom_amb_idioma del backend (routes/distribucions.py). Només per mostrar-lo:
   el nom real el decideix sempre el servidor. */
function nomFitxerDesti(patro, artCodi, nomProducte, numVersio, idioma) {
  let nom = (patro || '{art_codi}.pdf')
    .replaceAll('{art_codi}', artCodi || '')
    .replaceAll('{nom_producte}', nomProducte || '')
    .replaceAll('{versio}', String(numVersio ?? 0))
    .replaceAll('{data}', new Date().toISOString().slice(0, 10).replaceAll('-', ''));
  nom = nom.replace(/[\\/:*?"<>|#%&]/g, '_').replace(/[\u0000-\u001f]/g, '').trim().replace(/\.+$/, '').trim();
  if (!nom) nom = `${artCodi}.pdf`;
  if (!idioma) return nom;
  const punt = nom.lastIndexOf('.');
  return punt > 0
    ? `${nom.slice(0, punt)}_${idioma.toUpperCase()}${nom.slice(punt)}`
    : `${nom}_${idioma.toUpperCase()}.pdf`;
}

function DistribuirPanel({ fitxaId, fitxaArtCodi, nomProducte, numVersio, distribucions, onDone, onClose }) {
  const [destins, setDestins] = useState([]);
  // Només es distribueixen PDFs d'un sol idioma (el principal bilingüe ja no).
  // Idiomes de la fitxa (marcats o amb traducció) i selecció manual per destí:
  // {destiId: {ca: true, en: false...}}. Per defecte, cap.
  const [idiomes, setIdiomes] = useState([]);
  const [selIdiomes, setSelIdiomes] = useState({});
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [resultats, setResultats] = useState([]);
  const [retirarDesti, setRetirarDesti] = useState(null);
  const toast = useToast();

  // Una fitxa està "actualment al destí" si l'última distribució per a aquell
  // destí va ser 'ok' (no 'retirat' o 'error' posterior).
  const esJaDistribuit = (destiId, dists, idioma = null) => {
    // Nomes 'ok' i 'retirat' canvien si el fitxer hi es: un 'error' es una
    // pujada fallida, i el fitxer anterior hi segueix sent.
    // idioma null = PDF principal: no s'ha de barrejar amb els fitxers d'idioma.
    const perDesti = dists
      .filter((d) => d.desti_id === destiId && d.executat_at
                     && (d.idioma || null) === idioma
                     && (d.estat === 'ok' || d.estat === 'retirat'))
      .sort((a, b) => new Date(b.executat_at) - new Date(a.executat_at));
    return perDesti.length > 0 && perDesti[0].estat === 'ok';
  };
  // PDF principal bilingüe que va quedar al destí d'abans (ja no es distribueix)
  const bilingueAlDesti = (destiId) => esJaDistribuit(destiId, distribucions);

  useEffect(() => {
    api.llistarDestins().then((data) => {
      setDestins(data.filter((d) => d.actiu));
      setLoading(false);
    }).catch(() => setLoading(false));
    api.resumTraduccions(fitxaId)
      .then((r) => setIdiomes(r.idiomes.filter((i) => i.marcat || i.estat !== 'falta')))
      .catch(() => setIdiomes([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const revisats = idiomes.filter((i) => i.estat === 'revisada');
  const marcarTotsRevisats = () => {
    const sel = {};
    destins.forEach((d) => { sel[d.id] = Object.fromEntries(revisats.map((i) => [i.idioma, true])); });
    setSelIdiomes(sel);
  };
  const toggleIdioma = (destiId, idioma) => setSelIdiomes((prev) => ({
    ...prev, [destiId]: { ...(prev[destiId] || {}), [idioma]: !prev[destiId]?.[idioma] },
  }));

  // Parells [destiId, idioma] a enviar
  const enviaments = () => {
    const parells = [];
    destins.forEach((d) => {
      idiomes.forEach((i) => { if (selIdiomes[d.id]?.[i.idioma]) parells.push([d.id, i.idioma]); });
    });
    return parells;
  };

  const distribuir = async () => {
    const parells = enviaments();
    if (parells.length === 0) return;
    setSending(true);
    const res = [];
    for (const [destiId, idioma] of parells) {
      const nom = `${destins.find((d) => d.id === destiId)?.nom} (${idioma.toUpperCase()})`;
      try {
        const r = await api.distribuirDesti(fitxaId, destiId, idioma);
        res.push({ desti: nom, ok: r.estat === 'ok', url: r.missatge_error, error: r.missatge_error });
      } catch (err) {
        res.push({ desti: nom, ok: false, error: err.message });
      }
    }
    setResultats(res);
    setSending(false);

    const oks = res.filter((r) => r.ok).length;
    const errors = res.filter((r) => !r.ok).length;
    if (errors > 0) {
      toast.warning(`Distribució: ${oks} ok, ${errors} errors`);
    } else {
      toast.success(`Distribuïts correctament ${oks} fitxers`);
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
        <div className="empty-state">
          <p style={{ marginBottom: '0.5rem' }}>Encara no hi ha cap destí de distribució</p>
          <p>Un destí és el lloc on es publica el PDF de la fitxa (FTP, carpeta de xarxa...).{' '}
            <Link to="/admin/destins">Configurar destins &rarr;</Link>
          </p>
        </div>
      ) : (
        <>
          <p style={{ fontSize: '0.88rem', color: 'var(--gray-500)', marginBottom: '1rem' }}>
            Es distribueixen <strong>només PDFs d'un sol idioma</strong>, amb el codi d'idioma al final del
            nom (p.ex. {fitxaArtCodi}_CA.pdf). Marca a cada destí els idiomes que vols enviar. Només es
            poden distribuir les traduccions revisades. Un idioma amb ✓ ja és al destí; passa el ratolí per
            sobre per veure el nom exacte del fitxer.
          </p>
          {idiomes.length === 0 ? (
            <div className="correu-avis" style={{ marginBottom: '1rem' }}>
              Aquesta fitxa no té cap idioma. Marca'ls a la pestanya <strong>Idiomes</strong>.
            </div>
          ) : revisats.length === 0 ? (
            <div className="correu-avis" style={{ marginBottom: '1rem' }}>
              Cap traducció d'aquesta fitxa està revisada encara: revisa-les a la pestanya <strong>Idiomes</strong>.
            </div>
          ) : (
            <button type="button" className="outline btn-sm" style={{ marginBottom: '0.75rem' }}
              onClick={marcarTotsRevisats}>
              Marcar tots els idiomes revisats a tots els destins
            </button>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.25rem' }}>
            {destins.map((d) => {
              const jaBilingue = bilingueAlDesti(d.id);
              const algunMarcat = idiomes.some((i) => selIdiomes[d.id]?.[i.idioma]);
              return (
                <div key={d.id} className="desti-check" style={{
                  display: 'flex', alignItems: 'center', gap: '0.75rem',
                  padding: '0.7rem 1rem', border: '1px solid var(--gray-200)',
                  borderRadius: 'var(--radius)', margin: 0,
                  background: algunMarcat ? 'var(--brand-50)' : '#fff',
                  borderColor: algunMarcat ? 'var(--brand)' : 'var(--gray-200)',
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      {d.nom}
                      {jaBilingue && (
                        <span className="badge" style={{ fontSize: '0.72rem', background: 'var(--gray-100)', color: 'var(--gray-600)' }}
                          title={`Al destí hi ha el PDF bilingüe antic (${nomFitxerDesti(d.patro_nom_fitxer, fitxaArtCodi, nomProducte, numVersio)}), que ja no s'actualitza`}>
                          Hi ha el PDF bilingüe antic
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }} title={`Patró: ${d.patro_nom_fitxer}`}>
                      {d.tipus.toUpperCase()} &middot; Fitxers: <code>{nomFitxerDesti(d.patro_nom_fitxer, fitxaArtCodi, nomProducte, numVersio, 'xx')}</code>
                    </div>
                  </div>
                  {idiomes.length > 0 && (
                    <div className="desti-idiomes" onClick={(e) => e.stopPropagation()}>
                      <span className="desti-idiomes-titol">Idiomes:</span>
                      {idiomes.map((i) => {
                        const revisada = i.estat === 'revisada';
                        const jaIdioma = esJaDistribuit(d.id, distribucions, i.idioma);
                        const nom = nomFitxerDesti(d.patro_nom_fitxer, fitxaArtCodi, nomProducte, numVersio, i.idioma);
                        const titol = !revisada
                          ? `${i.nom}: la traducció no està revisada`
                          : `${nom}${jaIdioma ? ' · ja distribuït' : ' · encara no distribuït'}`;
                        return (
                          <label key={i.idioma} title={titol}
                            className={`desti-idioma ${revisada ? '' : 'desactivat'} ${jaIdioma ? 'ja-distribuit' : ''}`}>
                            <input type="checkbox" disabled={!revisada}
                              aria-label={`PDF en ${i.nom} a ${d.nom} (${nom})`}
                              checked={!!selIdiomes[d.id]?.[i.idioma]}
                              onChange={() => toggleIdioma(d.id, i.idioma)} />
                            {i.idioma.toUpperCase()}{jaIdioma && ' ✓'}
                          </label>
                        );
                      })}
                    </div>
                  )}
                  {jaBilingue && (
                    <button
                      type="button"
                      className="outline btn-sm"
                      onClick={() => setRetirarDesti(d)}
                      style={{ margin: 0, color: 'var(--danger)', borderColor: 'var(--danger)', fontSize: '0.78rem' }}
                      title={`Retirar el PDF bilingüe antic de ${d.nom}`}
                    >
                      Retirar bilingüe
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {retirarDesti && (
            <RetirarDestiModal
              fitxaId={fitxaId}
              fitxaArtCodi={fitxaArtCodi}
              desti={retirarDesti}
              onDone={() => { setRetirarDesti(null); onDone(); }}
              onClose={() => setRetirarDesti(null)}
            />
          )}

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

          <button onClick={distribuir} disabled={sending || enviaments().length === 0} aria-busy={sending}>
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
  useEscapeKey(onClose);
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
  const [compareV1, setCompareV1] = useState('');
  const [compareV2, setCompareV2] = useState('');
  const versions = fitxa.versions || [];

  const mostrarDiff = (v, i) => {
    if (i < versions.length - 1) {
      setDiffPair({ v1Id: versions[i + 1].id, v2Id: v.id });
    }
  };

  const compararLliure = () => {
    if (!compareV1 || !compareV2 || compareV1 === compareV2) return;
    setDiffPair({ v1Id: parseInt(compareV1), v2Id: parseInt(compareV2) });
  };

  if (versions.length === 0) {
    return (
      <div className="empty-state">
        <p style={{ marginBottom: '0.5rem' }}>Aquesta fitxa encara no té cap versió</p>
        <p>Les versions es creen en desar canvis des de l'editor.</p>
      </div>
    );
  }

  return (
    <>
      {versions.length > 1 && (
        <div style={{
          marginBottom: '1rem', display: 'flex', gap: '0.75rem',
          alignItems: 'center', flexWrap: 'wrap',
        }}>
          <div style={{
            display: 'flex', gap: '0.4rem', alignItems: 'center',
            background: 'var(--brand-50)', padding: '0.5rem 0.75rem',
            borderRadius: 'var(--radius)', border: '1px solid var(--brand-light)',
          }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Comparar:</span>
            <select value={compareV1} onChange={(e) => setCompareV1(e.target.value)}
              style={{ margin: 0, width: 'auto', minWidth: '90px', padding: '0.3rem 0.5rem' }}>
              <option value="">— Rev. —</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>Rev. {v.num_versio}</option>
              ))}
            </select>
            <span>amb</span>
            <select value={compareV2} onChange={(e) => setCompareV2(e.target.value)}
              style={{ margin: 0, width: 'auto', minWidth: '90px', padding: '0.3rem 0.5rem' }}>
              <option value="">— Rev. —</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>Rev. {v.num_versio}</option>
              ))}
            </select>
            <button type="button" className="btn-sm" onClick={compararLliure}
              disabled={!compareV1 || !compareV2 || compareV1 === compareV2}
              style={{ margin: 0 }}>
              Comparar
            </button>
          </div>
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
  useEscapeKey(onClose);
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
  useEscapeKey(onClose);
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

function EsborrarDestinsModal({ fitxa, estat, distribucions, onDone, onClose }) {
  useEscapeKey(onClose);
  const [destins, setDestins] = useState([]);
  const [selectedDestins, setSelectedDestins] = useState({});
  const [motiu, setMotiu] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const toast = useToast();

  useEffect(() => {
    api.llistarDestins().then((data) => {
      // Filtrar destins amb distribució 'ok' per aquesta fitxa
      const destinsAmbOk = data.filter((d) =>
        distribucions.some((dist) => dist.desti_id === d.id && dist.estat === 'ok')
      );
      setDestins(destinsAmbOk);
      const sel = {};
      destinsAmbOk.forEach((d) => { sel[d.id] = true; });
      setSelectedDestins(sel);
    }).catch(() => {});
  }, [distribucions]);

  const toggleDesti = (id) =>
    setSelectedDestins((prev) => ({ ...prev, [id]: !prev[id] }));

  const confirmar = async (e) => {
    e.preventDefault();
    const ids = Object.entries(selectedDestins)
      .filter(([, v]) => v).map(([k]) => parseInt(k));
    setLoading(true);
    setError(null);
    try {
      await api.canviarEstatFitxa(fitxa.id, {
        estat: estat.codi,
        esborrar_destins: ids,
        motiu,
      });
      toast.success(`Fitxa ${fitxa.art_codi} marcada com a "${estat.nom}"`);
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
          <h3 style={{ margin: 0 }}>Canviar estat a "{estat.nom}"</h3>
          <button className="outline secondary btn-sm" onClick={onClose}>&times;</button>
        </div>

        <p style={{ fontSize: '0.88rem', color: 'var(--gray-600)' }}>
          La fitxa <strong>{fitxa.art_codi}</strong> passarà a l'estat <strong>{estat.nom}</strong>.
          {destins.length > 0 && ' També pots esborrar el PDF dels destins on s\'havia distribuït.'}
        </p>

        <form onSubmit={confirmar}>
          <label>
            Motiu (opcional)
            <input type="text" value={motiu} onChange={(e) => setMotiu(e.target.value)}
              placeholder="Ex: producte descatalogat" />
          </label>

          {destins.length > 0 ? (
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
          ) : (
            <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
              No hi ha distribucions correctes per esborrar.
            </p>
          )}

          {error && <p style={{ color: 'var(--danger)', fontSize: '0.88rem', marginBottom: '0.5rem' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="outline secondary" onClick={onClose}>Cancel·lar</button>
            <button type="submit" disabled={loading} aria-busy={loading}>
              {loading ? 'Processant...' : 'Inactivar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


/* Botons "Veure en:" (Original + idiomes amb traducció). Els comparteixen la
   pestanya Contingut i la vista prèvia del PDF. */
function SelectorIdioma({ idiomes, vista, onChange }) {
  if (!idiomes.length) return null;
  return (
    <div className="contingut-idiomes" role="group" aria-label="Idioma">
      <span>Veure en:</span>
      <button type="button" className={`outline ${vista === 'original' ? 'active' : ''}`}
        aria-pressed={vista === 'original'} onClick={() => onChange('original')}>
        Original
      </button>
      {idiomes.map((i) => (
        <button key={i.idioma} type="button" className={`outline ${vista === i.idioma ? 'active' : ''}`}
          aria-pressed={vista === i.idioma} onClick={() => onChange(i.idioma)}
          title={i.estat === 'revisada' ? i.nom : `${i.nom} (pendent de revisar)`}>
          {i.nom}{i.estat !== 'revisada' && ' *'}
        </button>
      ))}
    </div>
  );
}

/* Pestanya Contingut: mostra la versió en l'idioma triat (vegeu idiomaVista a
   DetallFitxa: per defecte el català si té traducció; si no, l'original). */
function ContingutIdioma({ fitxaId, contingut, versio, idiomes, vista, setVista }) {
  const [traduit, setTraduit] = useState(null); // {idioma, contingut, estat}
  const [carregant, setCarregant] = useState(false);

  useEffect(() => {
    if (!vista || vista === 'original' || !versio) { setTraduit(null); return; }
    let cancel = false;
    setCarregant(true);
    api.llegirTraduccio(fitxaId, versio.id, vista)
      .then((d) => {
        if (cancel) return;
        if (!d.traduccio) { setVista('original'); return; }
        setTraduit({
          idioma: vista,
          estat: d.traduccio.estat,
          contingut: combinarTraduccio(d.original, d.traduccio.contingut, d.camps_traduibles, vista),
        });
      })
      .catch(() => { if (!cancel) setVista('original'); })
      .finally(() => { if (!cancel) setCarregant(false); });
    return () => { cancel = true; };
  }, [vista, fitxaId, versio?.id]);

  // Mentre arriba la traducció no es mostra l'original, per no fer pampallugues
  const esperant = vista !== 'original' && traduit?.idioma !== vista;
  const mostrat = vista !== 'original' && !esperant ? traduit.contingut : contingut;

  return (
    <>
      <SelectorIdioma idiomes={idiomes} vista={vista} onChange={setVista} />
      {vista !== 'original' && traduit?.estat && traduit.estat !== 'revisada' && (
        <div className="correu-avis" style={{ marginBottom: '0.75rem' }}>
          Aquesta traducció està pendent de revisar.
        </div>
      )}
      {carregant || esperant ? <p aria-busy="true">Carregant traducció...</p>
        : <PdfDocumentView contingut={mostrat} versio={versio} />}
    </>
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
  const [enviaments, setEnviaments] = useState([]);
  const [destins, setDestins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  // Idioma en què es mostren el contingut i la vista prèvia del PDF:
  // null = encara decidint; 'original' (bilingüe) | 'ca' | 'es' | 'en' | 'pt'
  const [idiomesTrad, setIdiomesTrad] = useState([]);
  const [idiomaVista, setIdiomaVista] = useState(null);
  const [etiquetesCarregades, setEtiquetesCarregades] = useState(false);
  const [pdfIdioma, setPdfIdioma] = useState(null);   // idioma de la vista prèvia oberta (null = versió antiga)
  const openDist = location.state?.openDistribuir || false;
  const [section, setSection] = useState(openDist ? 'distribucions' : 'contingut');
  const [showDistribuir, setShowDistribuir] = useState(openDist);
  const [showComprovar, setShowComprovar] = useState(false);
  // Resultat de la comprovacio puntual per fila d'historial: {desti_id: resultat}
  const [comprovacions, setComprovacions] = useState({});
  const [comprovantDesti, setComprovantDesti] = useState(null);
  const [verif, setVerif] = useState(null);
  const [showVerifDetails, setShowVerifDetails] = useState(false);
  const [retirarModalDist, setRetirarModalDist] = useState(null);
  const [substituirPdfOpen, setSubstituirPdfOpen] = useState(false);
  const [convertirComercialitzatOpen, setConvertirComercialitzatOpen] = useState(false);

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

  // Títols per idioma (els mateixos del PDF) per a la vista web en anglès/portuguès
  useEffect(() => {
    api.etiquetesIdioma()
      .then((e) => definirEtiquetesIdioma(e))
      .catch(() => {})           // sense diccionari, en/pt surten bilingües
      .finally(() => setEtiquetesCarregades(true));
  }, []);

  // Idiomes amb traducció de la versió activa. Per defecte es mostra el català.
  const versioActivaId = fitxa?.versions?.find((v) => v.activa)?.id;
  useEffect(() => {
    if (!fitxa) return undefined;
    let cancel = false;
    api.resumTraduccions(id)
      .then((r) => {
        if (cancel) return;
        const amb = r.comercialitzat ? [] : r.idiomes.filter((i) => i.traduccio);
        setIdiomesTrad(amb);
        setIdiomaVista((actual) => (actual && (actual === 'original' || amb.some((i) => i.idioma === actual))
          ? actual
          : (amb.some((i) => i.idioma === 'ca') ? 'ca' : 'original')));
      })
      .catch(() => { if (!cancel) setIdiomaVista('original'); });
    return () => { cancel = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, versioActivaId, !!fitxa]);
  useEffect(() => { api.llistarEnviaments(id).then(setEnviaments).catch(() => {}); }, [id]);
  useEffect(() => { if (id) verificarAuto(); }, [id]);
  useEffect(() => { api.llistarDestins().then(setDestins).catch(() => {}); }, []);

  // Helper: retorna true si aquesta distribucio és l'última 'ok' vigent per al seu desti_id.
  // Si sí, es pot retirar. Si hi ha una distribucio posterior (ok, error o retirat), no.
  const esUltimaOkPerDesti = (dist) => {
    if (!dist || dist.desti_id == null || dist.estat !== 'ok') return false;
    // Nomes compten 'ok' i 'retirat': un 'error' posterior vol dir que va
    // fallar una pujada, no que el fitxer s'hagi tret del desti.
    // Cada idioma és un fitxer diferent: es compara només amb el mateix idioma.
    const perDesti = distribucions
      .filter((d) => d.desti_id === dist.desti_id && d.executat_at
                     && (d.idioma || null) === (dist.idioma || null)
                     && (d.estat === 'ok' || d.estat === 'retirat'))
      .sort((a, b) => new Date(b.executat_at) - new Date(a.executat_at));
    return perDesti.length > 0 && perDesti[0].id === dist.id;
  };

  // Comprova un sol desti des de l'historial. Nomes llegeix: no toca la BD
  // ni el fitxer del desti.
  const comprovarUnDesti = async (destiId, idioma = null) => {
    const clau = `${destiId}|${idioma || ''}`;
    setComprovantDesti(clau);
    try {
      const r = await api.comprovarDesti(id, destiId, idioma);
      setComprovacions((prev) => ({ ...prev, [clau]: r }));
      if (r.estat_verificacio === 'ok') toast.success(r.missatge);
      else toast.warning(r.missatge);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setComprovantDesti(null);
    }
  };

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
  const [estatAConfirmar, setEstatAConfirmar] = useState(null);
  const [estatPendent, setEstatPendent] = useState(null);
  const [canvianEstat, setCanvianEstat] = useState(false);
  const [estatsCatalog, setEstatsCatalog] = useState([]);
  const [editingObs, setEditingObs] = useState(false);
  const [obsText, setObsText] = useState('');

  useEffect(() => {
    api.llistarEstats().then(setEstatsCatalog).catch(() => {});
  }, []);

  const estatActualObj = estatsCatalog.find((e) => e.codi === fitxa?.estat);

  const canviarEstat = async (nouCodi) => {
    if (!fitxa || nouCodi === fitxa.estat) return;
    const estat = estatsCatalog.find((e) => e.codi === nouCodi);
    if (!estat) return;

    // Si l'estat té acció d'esborrat i hi ha distribucions ok, obrir modal
    if (estat.accio === 'esborrar_destins') {
      const teOk = distribucions.some((d) => d.estat === 'ok');
      if (teOk) {
        setEstatAConfirmar(estat);
        return;
      }
    }

    // La resta de canvis s'aplicaven a l'instant des del select, sense desfer:
    // amb la roda del ratolí sobre el desplegable es podia canviar l'estat
    // d'una fitxa publicada sense adonar-se'n.
    setEstatPendent(estat);
  };

  const aplicarCanviEstat = async () => {
    const estat = estatPendent;
    if (!estat) return;
    setEstatPendent(null);
    const nouCodi = estat.codi;
    setCanvianEstat(true);
    try {
      await api.canviarEstatFitxa(fitxa.id, { estat: nouCodi });
      toast.success(`Estat canviat a ${estat.nom}`);
      carregarDades();
    } catch (err) {
      toast.error(`Error: ${err.message}`);
    } finally {
      setCanvianEstat(false);
    }
  };

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

  // versioId: vista prèvia d'una versió antiga (pestanya Versions), sempre l'original.
  // Sense versioId: la versió activa en l'idioma triat (idiomaVista).
  const vistaPrevia = (versioId, idioma) => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
    setPdfLoading(true);
    setSection('pdf');
    const token = localStorage.getItem('token');
    const idiomaPdf = versioId ? null : (idioma || idiomaVista || 'original');
    setPdfIdioma(idiomaPdf);
    const url = versioId
      ? `/api/fitxes/${id}/pdf?versio_id=${versioId}`
      : (idiomaPdf !== 'original'
        ? `/api/fitxes/${id}/pdf/${idiomaPdf}`
        : `/api/fitxes/${id}/pdf`);
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
            {(usuari.rol === 'admin' || usuari.rol === 'editor') ? (
              <select
                value={fitxa.estat}
                onChange={(e) => canviarEstat(e.target.value)}
                disabled={canvianEstat || estatsCatalog.length === 0}
                title="Canviar estat de la fitxa"
                className="badge"
                style={estatActualObj
                  ? { margin: 0, padding: '0.1rem 0.4rem', fontSize: '0.8rem', height: 'auto', width: 'auto', background: estatActualObj.color, color: estatActualObj.color_text }
                  : { margin: 0, padding: '0.1rem 0.4rem', fontSize: '0.8rem', height: 'auto', width: 'auto' }}
              >
                {estatsCatalog.map((e) => (
                  <option
                    key={e.codi}
                    value={e.codi}
                    disabled={usuari.rol !== 'admin' && e.accio !== 'cap'}
                  >
                    {e.nom}
                  </option>
                ))}
              </select>
            ) : (
              estatActualObj
                ? <span className="badge" style={{ background: estatActualObj.color, color: estatActualObj.color_text }}>{estatActualObj.nom}</span>
                : <span className={`badge ${fitxa.estat}`}>{fitxa.estat}</span>
            )}
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
          {(usuari.rol === 'admin' || usuari.rol === 'editor') && (fitxa.tipus_producte || 'elaborat') !== 'comercialitzat' && (
            <Link to={`/fitxes/${id}/editar`} role="button" className="outline">
              Editar / Nova versió
            </Link>
          )}
          {(usuari.rol === 'admin' || usuari.rol === 'editor') && (fitxa.tipus_producte || 'elaborat') === 'elaborat' && (
            <button className="outline" onClick={() => setConvertirComercialitzatOpen(true)}
              title="Convertir aquesta fitxa a producte comercialitzat pujant un PDF">
              Convertir a comercialitzat
            </button>
          )}
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
          {(usuari.rol === 'admin' || usuari.rol === 'editor') && (
            <button className="outline secondary" onClick={() => setShowDuplicar(true)}>
              Duplicar
            </button>
          )}
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', gap: '1rem', flexWrap: 'wrap' }}>
            <strong>Vista prèvia del PDF</strong>
            {pdfIdioma && (
              <SelectorIdioma idiomes={idiomesTrad} vista={pdfIdioma}
                onChange={(v) => { setIdiomaVista(v); vistaPrevia(undefined, v); }} />
            )}
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
            <button type="button" className={section === 'correus' ? 'active' : ''} onClick={() => setSection('correus')}>
              Correus ({enviaments.length})
            </button>
            <button type="button" className={section === 'idiomes' ? 'active' : ''} onClick={() => setSection('idiomes')}>
              Idiomes{fitxa.idiomes?.length ? ` (${fitxa.idiomes.length})` : ''}
            </button>
          </div>

          {section === 'contingut' && (
            <>
              {showVerifDetails && verif?.data && (
                <VerificarPanel fitxaId={id} onClose={() => setShowVerifDetails(false)} />
              )}
              {(fitxa.tipus_producte || 'elaborat') === 'comercialitzat' ? (
                <div className="card">
                  <p style={{ color: 'var(--gray-600)' }}>
                    <strong>Fitxa de producte comercialitzat.</strong> No té contingut estructurat editable —
                    el PDF s'ha pujat directament del proveïdor.
                  </p>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
                    <button className="outline" onClick={() => vistaPrevia()}>Veure PDF actual</button>
                    <button className="outline secondary" onClick={() => descarregarPdf()}>Descarregar PDF</button>
                    {(usuari.rol === 'admin' || usuari.rol === 'editor') && (
                      <button onClick={() => setSubstituirPdfOpen(true)}>Substituir per nou PDF</button>
                    )}
                  </div>
                </div>
              ) : (
                idiomaVista === null || !etiquetesCarregades ? <p aria-busy="true">Carregant...</p> : (
                  <ContingutIdioma fitxaId={id} contingut={contingut} versio={versioActiva}
                    idiomes={idiomesTrad} vista={idiomaVista} setVista={setIdiomaVista} />
                )
              )}
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
                  fitxaArtCodi={fitxa.art_codi}
                  nomProducte={fitxa.nom_producte}
                  numVersio={versioActiva?.num_versio}
                  distribucions={distribucions}
                  onDone={carregarDades}
                  onClose={() => setShowDistribuir(false)}
                />
              )}

              {showComprovar && versioActiva && (
                <ComprovarDestinsPanel
                  fitxaId={id}
                  onClose={() => setShowComprovar(false)}
                />
              )}

              {!showDistribuir && !showComprovar && versioActiva && (
                <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <button onClick={() => setShowDistribuir(true)} className="outline">
                    Distribuir a nous destins
                  </button>
                  <button onClick={() => setShowComprovar(true)} className="outline secondary">
                    Comprovar destins
                  </button>
                </div>
              )}

              <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Historial de distribucions</h3>
              {distribucions.length === 0 ? (
                <div className="empty-state">
                  <p style={{ marginBottom: '0.5rem' }}>Aquesta fitxa no s'ha distribuït mai</p>
                  <p>Quan es distribueixi, aquí hi quedarà el registre de cada enviament,
                    amb el destí, la revisió i el resultat.</p>
                </div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Desti</th>
                      <th>Fitxer</th>
                      <th>Rev.</th>
                      <th>Estat</th>
                      <th>Data</th>
                      <th>Usuari</th>
                      <th>Detall</th>
                      {(usuari.rol === 'admin' || usuari.rol === 'editor' || usuari.rol === 'distribuidor') && (
                        <th style={{ textAlign: 'right' }}>Accions</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {distribucions.map((d) => (
                      <tr key={d.id}>
                        <td style={{ fontWeight: 500 }}>{d.desti}</td>
                        <td>{d.idioma
                          ? <span className="idioma-tag">{d.idioma.toUpperCase()}</span>
                          : <span style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>Principal</span>}</td>
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
                        {(usuari.rol === 'admin' || usuari.rol === 'editor' || usuari.rol === 'distribuidor') && (
                          <td style={{ textAlign: 'right' }}>
                            {esUltimaOkPerDesti(d) && (
                              <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                                {comprovacions[`${d.desti_id}|${d.idioma || ''}`] && (
                                  <span title={comprovacions[`${d.desti_id}|${d.idioma || ''}`].missatge}>
                                    <BadgeVerificacio estat={comprovacions[`${d.desti_id}|${d.idioma || ''}`].estat_verificacio} />
                                  </span>
                                )}
                                <button
                                  type="button"
                                  className="outline btn-sm"
                                  disabled={comprovantDesti === `${d.desti_id}|${d.idioma || ''}`}
                                  onClick={() => comprovarUnDesti(d.desti_id, d.idioma)}
                                  style={{ margin: 0, fontSize: '0.78rem' }}
                                  title={`Comprovar si el PDF hi és realment a ${d.desti}`}
                                >
                                  {comprovantDesti === `${d.desti_id}|${d.idioma || ''}` ? 'Comprovant…' : 'Comprovar'}
                                </button>
                                <button
                                  type="button"
                                  className="outline btn-sm"
                                  onClick={() => setRetirarModalDist(d)}
                                  style={{ margin: 0, color: 'var(--danger)', borderColor: 'var(--danger)', fontSize: '0.78rem' }}
                                  title={`Retirar el PDF de ${d.desti}`}
                                >
                                  Retirar
                                </button>
                              </div>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}

          {section === 'idiomes' && (
            <IdiomesPanel fitxaId={id} artCodi={fitxa.art_codi} potEditar={usuari.rol === 'admin' || usuari.rol === 'editor'} />
          )}

          {section === 'correus' && (
            enviaments.length === 0 ? (
              <p style={{ color: 'var(--gray-500)' }}>Aquesta fitxa encara no s'ha enviat mai per correu.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Enviat per</th>
                      <th>Destinataris</th>
                      <th>Assumpte</th>
                      <th>Rev.</th>
                      <th>Estat</th>
                    </tr>
                  </thead>
                  <tbody>
                    {enviaments.map((e) => {
                      const item = e.items.find((i) => String(i.fitxa_id) === String(id));
                      const idiomesItem = e.items.filter((i) => String(i.fitxa_id) === String(id) && i.idioma);
                      return (
                        <tr key={e.id}>
                          <td style={{ whiteSpace: 'nowrap' }}>{new Date(e.created_at).toLocaleString('ca')}</td>
                          <td>{e.created_by}</td>
                          <td>{e.per_a}{e.cc && <div style={{ color: 'var(--gray-500)', fontSize: '0.8rem' }}>CC: {e.cc}</div>}</td>
                          <td>{e.assumpte}{new Set(e.items.map((i) => i.fitxa_id)).size > 1 && <div style={{ color: 'var(--gray-500)', fontSize: '0.8rem' }}>{new Set(e.items.map((i) => i.fitxa_id)).size} fitxes adjuntes</div>}</td>
                          <td style={{ textAlign: 'center' }}>
                            {item?.num_versio ?? '-'}
                            {idiomesItem.map((i) => <span key={i.id} className="idioma-tag">{i.idioma.toUpperCase()}</span>)}
                          </td>
                          <td>
                            <span className={`dist-badge ${e.estat === 'ok' ? 'dist-ok' : e.estat === 'error' ? 'dist-error' : 'dist-pending'}`}
                              title={e.missatge_error || ''}>
                              {e.estat === 'ok' ? 'Enviat' : e.estat === 'error' ? 'Error' : 'Pendent'}
                            </span>
                            {e.estat === 'error' && e.missatge_error && (
                              <div style={{ color: 'var(--danger)', fontSize: '0.8rem' }}>{e.missatge_error}</div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
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

      <ConfirmDialog
        obert={Boolean(estatPendent)}
        titol="Canviar l'estat de la fitxa"
        textConfirmar={`Canviar a ${estatPendent?.nom || ''}`}
        ocupat={canvianEstat}
        onConfirmar={aplicarCanviEstat}
        onCancelar={() => setEstatPendent(null)}
      >
        <p style={{ margin: 0 }}>
          La fitxa <strong>{fitxa?.art_codi}</strong> passarà de{' '}
          <strong>{estatActualObj?.nom || fitxa?.estat}</strong> a{' '}
          <strong>{estatPendent?.nom}</strong>.
        </p>
      </ConfirmDialog>

      {estatAConfirmar && (
        <EsborrarDestinsModal
          fitxa={fitxa}
          estat={estatAConfirmar}
          distribucions={distribucions}
          onDone={() => { setEstatAConfirmar(null); carregarDades(); }}
          onClose={() => setEstatAConfirmar(null)}
        />
      )}

      {retirarModalDist && (() => {
        const desti = destins.find((x) => x.id === retirarModalDist.desti_id) || {
          id: retirarModalDist.desti_id,
          nom: retirarModalDist.desti,
          tipus: '',
        };
        return (
          <RetirarDestiModal
            fitxaId={id}
            fitxaArtCodi={fitxa.art_codi}
            desti={desti}
            idioma={retirarModalDist.idioma}
            onDone={() => { setRetirarModalDist(null); carregarDades(); }}
            onClose={() => setRetirarModalDist(null)}
          />
        );
      })()}

      {substituirPdfOpen && (
        <PujarPdfModal
          title="Substituir per nou PDF"
          intro={<>Es crearà una nova versió de <strong>{fitxa.art_codi}</strong> amb el PDF pujat. La versió anterior es manté intacta a l'historial.</>}
          submitLabel="Crear nova versió"
          submitLoadingLabel="Pujant..."
          successMessage={`Nova versió de ${fitxa.art_codi} creada amb el PDF pujat`}
          onSubmit={(file, descripcio) => api.crearVersioPdf(id, file, descripcio)}
          onDone={() => { setSubstituirPdfOpen(false); carregarDades(); }}
          onClose={() => setSubstituirPdfOpen(false)}
        />
      )}

      {convertirComercialitzatOpen && (
        <PujarPdfModal
          title="Convertir a producte comercialitzat"
          intro={<>Es convertirà <strong>{fitxa.art_codi}</strong> ({fitxa.nom_producte}) a producte comercialitzat. Es crearà una nova versió amb el PDF que pugis i les versions anteriors elaborades es preservaran a l'historial.</>}
          submitLabel="Convertir"
          submitLoadingLabel="Convertint..."
          successMessage={`Fitxa ${fitxa.art_codi} convertida a comercialitzada`}
          onSubmit={(file, descripcio) => api.convertirAComercialitzat(id, file, descripcio)}
          onDone={() => { setConvertirComercialitzatOpen(false); carregarDades(); }}
          onClose={() => setConvertirComercialitzatOpen(false)}
        />
      )}
    </>
  );
}

function PujarPdfModal({ title, intro, submitLabel, submitLoadingLabel, successMessage, onSubmit, onDone, onClose }) {
  useEscapeKey(onClose);
  const [file, setFile] = useState(null);
  const [descripcio, setDescripcio] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const toast = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) { setError('Cal seleccionar un fitxer PDF'); return; }
    if (!descripcio.trim()) { setError('Cal indicar la descripció del canvi'); return; }
    setLoading(true);
    setError(null);
    try {
      await onSubmit(file, descripcio.trim());
      if (successMessage) toast.success(successMessage);
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
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button className="outline secondary btn-sm" onClick={onClose}>&times;</button>
        </div>

        {intro && (
          <p style={{ fontSize: '0.88rem', color: 'var(--gray-600)', marginBottom: '1rem' }}>{intro}</p>
        )}

        <form onSubmit={handleSubmit}>
          <label>
            Fitxer PDF *
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
            />
          </label>

          <label>
            Descripció del canvi *
            <textarea
              value={descripcio}
              onChange={(e) => setDescripcio(e.target.value)}
              required
              placeholder="Ex: Actualització rebuda del proveïdor el 20/07/2026"
              rows={3}
            />
          </label>

          {error && <p style={{ color: 'var(--danger)', fontSize: '0.88rem', marginBottom: '0.5rem' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="outline secondary" onClick={onClose}>Cancel·lar</button>
            <button type="submit" disabled={loading} aria-busy={loading}>
              {loading ? (submitLoadingLabel || 'Pujant...') : (submitLabel || 'Confirmar')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default DetallFitxa;
