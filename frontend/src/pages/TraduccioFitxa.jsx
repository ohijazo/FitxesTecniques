import { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import DOMPurify from 'dompurify';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import RichEditor from '../components/RichEditor';
import { DEFAULT_SECTIONS } from '../components/FitxaForm';
import { BadgeTraduccio, obrirPdfIdioma, obrirPdf } from '../components/IdiomesPanel';

/* Etiqueta de cada camp, a partir de les seccions del formulari */
const ETIQUETES = Object.fromEntries(
  DEFAULT_SECTIONS.flatMap((s) => s.items.map((it) => [it.key, it.label])),
);
const ORDRE = DEFAULT_SECTIONS.flatMap((s) => s.items.map((it) => it.key));

const ORIGENS = {
  separat: 'separada del bilingüe',
  ia: 'traduïda amb IA',
  manual: 'escrita a mà',
  copiada: 'de la versió anterior',
  automatica: 'actualitzada automàticament',
};

/* El text importat del Word és pla amb salts de línia; l'editor treballa amb
   paràgrafs HTML. Sense això els salts es perdrien en obrir l'editor. */
function aParagrafs(text) {
  if (!text) return '';
  if (/<(p|ul|ol)\b/i.test(text)) return text;
  return text.split('\n').filter((l) => l.trim()).map((l) => `<p>${l}</p>`).join('');
}

function htmlOriginal(text) {
  if (!text) return '';
  const html = /<(p|ul|ol|br)\b/i.test(text) ? text : String(text).replace(/\n/g, '<br>');
  return DOMPurify.sanitize(html);
}

const ACCIONS = {
  desada: 'Desada',
  revisada: 'Revisada',
  automatica: 'Actualitzada automàticament',
  inicial: 'Còpia inicial',
};

/* Historial de la traducció d'un idioma (totes les versions de la fitxa):
   cada còpia es pot obrir en PDF tal com era, i s'hi veu on s'ha enviat. */
function HistorialTraduccio({ fitxaId, idioma, refrescar }) {
  const toast = useToast();
  const [obert, setObert] = useState(false);
  const [registres, setRegistres] = useState(null);

  useEffect(() => {
    if (!obert) return;
    api.historialTraduccio(fitxaId, idioma).then(setRegistres).catch((err) => toast.error(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [obert, fitxaId, idioma, refrescar]);

  return (
    <section className="trad-camp trad-historial">
      <h4>
        <button type="button" className="outline secondary btn-sm" onClick={() => setObert(!obert)}
          aria-expanded={obert}>
          {obert ? '▾' : '▸'} Historial de la traducció
        </button>
      </h4>
      {obert && (registres === null ? <p aria-busy="true">Carregant...</p>
        : registres.length === 0 ? <p style={{ color: 'var(--gray-500)', margin: 0 }}>Encara no hi ha cap canvi registrat.</p>
          : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr><th>Data</th><th>Rev.</th><th>Acció</th><th>Usuari</th><th>Enviada</th><th></th></tr>
                </thead>
                <tbody>
                  {registres.map((h) => (
                    <tr key={h.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>{new Date(h.created_at).toLocaleString('ca')}</td>
                      <td style={{ textAlign: 'center' }}>{h.num_versio}</td>
                      <td>
                        {ACCIONS[h.accio] || h.accio}
                        {h.camps_canviats?.length > 0 && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>
                            {h.camps_canviats.length} camps canviats a l'original
                          </div>
                        )}
                      </td>
                      <td style={{ fontSize: '0.85rem' }}>{h.created_by || '—'}</td>
                      <td style={{ fontSize: '0.8rem' }}>
                        {h.enviat.length === 0 ? '—' : h.enviat.map((e, i) => (
                          <div key={i}>
                            {e.tipus === 'correu' ? 'Correu a ' : ''}{e.desti}
                            {e.data && <span style={{ color: 'var(--gray-500)' }}> · {new Date(e.data).toLocaleDateString('ca')}</span>}
                          </div>
                        ))}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button type="button" className="outline btn-sm" style={{ margin: 0 }}
                          onClick={() => obrirPdf(`/api/fitxes/${fitxaId}/traduccions/historial/${h.id}/pdf`, toast)}>
                          Veure PDF
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
    </section>
  );
}

function TraduccioFitxa() {
  const { id, idioma } = useParams();
  const toast = useToast();
  const [dades, setDades] = useState(null);       // resposta de llegirTraduccio
  const [fitxa, setFitxa] = useState(null);
  const [error, setError] = useState(null);
  const [contingut, setContingut] = useState({});
  const [origen, setOrigen] = useState('manual');
  const [dubtosos, setDubtosos] = useState([]);
  const [canviats, setCanviats] = useState([]);
  const [avisBase, setAvisBase] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [ocupat, setOcupat] = useState(null);     // 'proposta' | 'desar' | 'revisar'
  const [confirmarProposta, setConfirmarProposta] = useState(null);

  const carregar = async () => {
    try {
      const [f, resum] = await Promise.all([api.detallFitxa(id), api.resumTraduccions(id)]);
      setFitxa(f);
      if (!resum.versio) throw new Error('Aquesta fitxa no té cap versió');
      const d = await api.llegirTraduccio(id, resum.versio.id, idioma);
      setDades(d);
      if (d.traduccio) {
        setContingut(d.traduccio.contingut || {});
        setOrigen(d.traduccio.origen || 'manual');
        setCanviats(d.traduccio.camps_canviats || []);
        setAvisBase(null);
      } else if (d.base) {
        setContingut(d.base.contingut || {});
        setOrigen('copiada');
        setCanviats(d.base.camps_canviats || []);
        setAvisBase(d.base.des_de_versio);
      }
      setDubtosos([]);
      setDirty(false);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };
  useEffect(() => { carregar(); }, [id, idioma]);

  useEffect(() => {
    const handler = (e) => { if (dirty) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  // Camps a mostrar: els traduïbles que tenen contingut a l'original, en l'ordre del formulari
  const camps = useMemo(() => {
    if (!dades) return [];
    const { text, nota, taula } = dades.camps_traduibles;
    const original = dades.original || {};
    const llista = [];
    const ordenats = [...ORDRE.filter((k) => text.includes(k) || taula.includes(k)),
      ...text.filter((k) => !ORDRE.includes(k))];
    for (const k of ordenats) {
      if (taula.includes(k)) {
        if (Array.isArray(original[k]) && original[k].length) llista.push({ key: k, tipus: 'taula' });
        const n = `${k}_note`;
        if (nota.includes(n) && original[n]) llista.push({ key: n, tipus: 'text', nota: k });
      } else if (original[k]) {
        llista.push({ key: k, tipus: 'text' });
      }
    }
    return llista;
  }, [dades]);

  if (error) return <p style={{ color: 'var(--danger)' }}>{error}</p>;
  if (!dades || !fitxa) return <p aria-busy="true">Carregant...</p>;

  const versio = dades.versio;
  const estat = dades.traduccio ? dades.traduccio.estat : (dades.base ? 'desactualitzada' : 'falta');
  // Original bilingüe: el català i el castellà es separen. Original en un sol
  // idioma: aquest idioma es copia tal qual i la resta es tradueixen.
  const idiomaOriginal = dades.idioma_original || 'bilingue';
  const potSeparar = (idioma === 'ca' || idioma === 'es') && (idiomaOriginal === 'bilingue' || idiomaOriginal === idioma);
  const textSeparar = idiomaOriginal === 'bilingue' ? 'Proposar des del bilingüe' : "Copiar de l'original";
  const origenIA = idiomaOriginal === 'ca' ? 'del català' : 'del castellà';
  const original = dades.original || {};

  const setCamp = (k, v) => { setContingut((c) => ({ ...c, [k]: v })); setDirty(true); };
  const setFila = (k, i, camp, v) => {
    setContingut((c) => {
      const files = [...(c[k] || (original[k] || []).map(() => ({})))];
      while (files.length < (original[k] || []).length) files.push({});
      files[i] = { ...(files[i] || {}), [camp]: v };
      return { ...c, [k]: files };
    });
    setDirty(true);
  };

  const demanarProposta = async (metode) => {
    setConfirmarProposta(null);
    setOcupat('proposta');
    try {
      const r = await api.propostaTraduccio(id, versio.id, idioma, metode);
      setContingut(r.proposta || {});
      setOrigen(r.origen);
      setDubtosos(r.dubtosos || []);
      setCanviats([]);
      setAvisBase(null);
      setDirty(true);
      toast.success(r.dubtosos?.length
        ? `Proposta preparada. Revisa especialment els ${r.dubtosos.length} camps marcats.`
        : 'Proposta preparada. Revisa-la i desa-la.');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setOcupat(null);
    }
  };

  const proposta = (metode) => {
    const teText = Object.values(contingut).some((v) => (Array.isArray(v) ? v.length : v));
    if (teText) setConfirmarProposta(metode);
    else demanarProposta(metode);
  };

  const desar = async () => {
    setOcupat('desar');
    try {
      await api.desarTraduccio(id, versio.id, idioma, { contingut, origen, camps_canviats: canviats });
      toast.success('Traducció desada. Queda pendent de revisar.');
      await carregar();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setOcupat(null);
    }
  };

  const revisar = async () => {
    setOcupat('revisar');
    try {
      await api.revisarTraduccio(id, versio.id, idioma);
      toast.success('Traducció marcada com a revisada');
      await carregar();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setOcupat(null);
    }
  };

  const marca = (k) => {
    if (dubtosos.includes(k)) return { classe: 'trad-dubtos', text: 'Separació dubtosa: revisa-la' };
    if (canviats.includes(k)) return { classe: 'trad-canviat', text: "L'original ha canviat des de la traducció" };
    return null;
  };

  return (
    <div className="traduccio-page">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <Link to={`/fitxes/${id}`}>&larr; {fitxa.art_codi} · {fitxa.nom_producte}</Link>
          <h2 style={{ margin: '0.25rem 0' }}>Traducció: {dades.nom_idioma}</h2>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', fontSize: '0.9rem', color: 'var(--gray-600)' }}>
            <span>Versió {versio.num_versio}</span>
            <BadgeTraduccio estat={estat} />
            {dades.traduccio && <span>· {ORIGENS[dades.traduccio.origen] || ''}</span>}
            {dades.traduccio?.revisat_by && <span>· revisada per {dades.traduccio.revisat_by}</span>}
            {dirty && <span style={{ color: 'var(--warning)' }}>· canvis sense desar</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {potSeparar && (
            <button className="outline" disabled={!!ocupat} onClick={() => proposta('separar')}>
              {textSeparar}
            </button>
          )}
          {!potSeparar && (
            <button className="outline" disabled={!!ocupat || !dades.ia_disponible}
              title={dades.ia_disponible ? `Traducció automàtica a partir ${origenIA}` : 'La traducció automàtica no està activada al servidor'}
              aria-busy={ocupat === 'proposta' ? 'true' : undefined}
              onClick={() => proposta('ia')}>
              {ocupat === 'proposta' ? 'Traduint…' : 'Traduir amb IA'}
            </button>
          )}
          {dades.traduccio && !dirty && (
            <button className="outline secondary" onClick={() => obrirPdfIdioma(id, idioma, versio.id, toast)}>
              Veure PDF
            </button>
          )}
          <button disabled={!!ocupat || !dirty} onClick={desar} aria-busy={ocupat === 'desar' ? 'true' : undefined}>
            Desar
          </button>
          {dades.traduccio && dades.traduccio.estat !== 'revisada' && !dirty && (
            <button className="outline" disabled={!!ocupat} onClick={revisar}>
              Marcar com a revisada
            </button>
          )}
        </div>
      </div>

      {avisBase != null && (
        <div className="card trad-avis">
          Aquesta versió encara no té traducció. Es mostra la de la <strong>versió {avisBase}</strong> com a punt
          de partida{canviats.length ? <>; els camps marcats en taronja han canviat a l'original</> : ''}.
          Revisa-la i desa-la.
        </div>
      )}
      {!dades.traduccio && !dades.base && !dirty && (
        <div className="card trad-avis">
          Encara no hi ha traducció. {potSeparar
            ? <>Prem <strong>{textSeparar}</strong> per partir del text actual de la fitxa.</>
            : dades.ia_disponible
              ? <>Prem <strong>Traduir amb IA</strong> per obtenir una proposta a partir {origenIA}.</>
              : <>Escriu la traducció de cada camp.</>}
        </div>
      )}

      <div className="trad-grid trad-grid-capcalera">
        <div>Original (versió {versio.num_versio})</div>
        <div>{dades.nom_idioma}</div>
      </div>

      {camps.map(({ key, tipus, nota }) => {
        const m = marca(nota || key);
        const etiqueta = nota ? `${ETIQUETES[nota] || nota} — peu de taula` : (ETIQUETES[key] || key);
        if (tipus === 'taula') {
          const filesOrig = original[key] || [];
          const filesTrad = contingut[key] || [];
          return (
            <section key={key} className={`trad-camp ${m ? m.classe : ''}`}>
              <h4>{etiqueta}{m && <span className="trad-marca">{m.text}</span>}</h4>
              <table className="trad-taula">
                <thead>
                  <tr><th>Paràmetre original</th><th>Valor original</th><th>Paràmetre</th><th>Valor (buit = igual que l'original)</th></tr>
                </thead>
                <tbody>
                  {filesOrig.map((f, i) => (
                    <tr key={i}>
                      <td dangerouslySetInnerHTML={{ __html: htmlOriginal(f?.parametre) }} />
                      <td dangerouslySetInnerHTML={{ __html: htmlOriginal(f?.valor) }} />
                      <td><input type="text" value={filesTrad[i]?.parametre || ''} aria-label={`Paràmetre ${i + 1}`}
                        onChange={(e) => setFila(key, i, 'parametre', e.target.value)} /></td>
                      <td><input type="text" value={filesTrad[i]?.valor || ''} placeholder={f?.valor || ''} aria-label={`Valor ${i + 1}`}
                        onChange={(e) => setFila(key, i, 'valor', e.target.value)} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          );
        }
        return (
          <section key={key} className={`trad-camp ${m ? m.classe : ''}`}>
            <h4>{etiqueta}{m && <span className="trad-marca">{m.text}</span>}</h4>
            <div className="trad-grid">
              <div className="trad-original" dangerouslySetInnerHTML={{ __html: htmlOriginal(original[key]) }} />
              <RichEditor value={aParagrafs(contingut[key])} onChange={(v) => setCamp(key, v)} />
            </div>
          </section>
        );
      })}

      <HistorialTraduccio fitxaId={id} idioma={idioma} refrescar={dades.traduccio?.updated_at + (dades.traduccio?.revisat_at || '')} />

      <ConfirmDialog
        obert={!!confirmarProposta}
        titol="Substituir la traducció?"
        textConfirmar="Substituir"
        onConfirmar={() => demanarProposta(confirmarProposta)}
        onCancelar={() => setConfirmarProposta(null)}
      >
        La proposta automàtica substituirà el que hi ha ara a l'editor. No es desa fins que premis Desar.
      </ConfirmDialog>
    </div>
  );
}

export default TraduccioFitxa;
