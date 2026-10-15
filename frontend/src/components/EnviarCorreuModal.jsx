import { useState, useEffect, useRef, useCallback } from 'react';
import { api, missatgeError } from '../api/client';
import { useToast } from './Toast';
import { useEscapeKey } from './useEscapeKey';

const POLL_MS = 2000;
const POLL_MAX = 90; // ~3 minuts

/** Text de la llista de fitxes que substitueix {fitxes} a la plantilla. */
function llistaFitxes(fitxes) {
  return fitxes
    .filter((f) => f.enviable)
    .map((f) => `- ${f.art_codi} - ${f.nom_producte} (rev. ${f.num_versio})`)
    .join('\n');
}

/**
 * Finestra per enviar per correu els PDFs (versió activa) de les fitxes
 * seleccionades. El correu surt de la bústia Microsoft 365 de l'usuari.
 */
function EnviarCorreuModal({ fitxaIds, onClose, onEnviat }) {
  const toast = useToast();
  const [carregant, setCarregant] = useState(true);
  const [errorCarrega, setErrorCarrega] = useState(null);
  const [fitxes, setFitxes] = useState([]);
  const [info, setInfo] = useState(null);
  const [perA, setPerA] = useState('');
  const [cc, setCc] = useState('');
  const [assumpte, setAssumpte] = useState('');
  const [cos, setCos] = useState('');
  const [enviant, setEnviant] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    let cancel = false;
    Promise.all([api.plantillaEnviament(), api.prepararEnviament(fitxaIds)])
      .then(([plantilla, prep]) => {
        if (cancel) return;
        setInfo(plantilla);
        setFitxes(prep.fitxes);
        setAssumpte(plantilla.assumpte);
        setCos(plantilla.cos.replace('{fitxes}', llistaFitxes(prep.fitxes)));
      })
      .catch((err) => { if (!cancel) setErrorCarrega(missatgeError(err)); })
      .finally(() => { if (!cancel) setCarregant(false); });
    return () => { cancel = true; };
  }, [fitxaIds]);

  useEffect(() => () => clearTimeout(pollRef.current), []);

  const tancar = useCallback(() => { if (!enviant) onClose(); }, [enviant, onClose]);
  useEscapeKey(tancar);

  const enviables = fitxes.filter((f) => f.enviable);
  const noEnviables = fitxes.filter((f) => !f.enviable);
  const massaFitxes = info && enviables.length > info.max_adjunts;
  const potEnviar = !carregant && !enviant && info?.configurat && enviables.length > 0
    && !massaFitxes && perA.trim() && assumpte.trim();

  const seguir = (id, intent = 0) => {
    pollRef.current = setTimeout(async () => {
      try {
        const env = await api.detallEnviament(id);
        if (env.estat === 'ok') {
          setEnviant(false);
          toast.success(`Correu enviat a ${env.per_a}`);
          onEnviat?.(env);
          onClose();
          return;
        }
        if (env.estat === 'error') {
          setEnviant(false);
          toast.error(`No s'ha pogut enviar: ${env.missatge_error}`, 12000);
          return;
        }
      } catch { /* error puntual de xarxa: es torna a provar */ }
      if (intent >= POLL_MAX) {
        setEnviant(false);
        toast.warning("L'enviament encara està en curs. Comprova-ho més tard a l'historial de la fitxa.", 10000);
        onClose();
        return;
      }
      seguir(id, intent + 1);
    }, POLL_MS);
  };

  const enviar = async (e) => {
    e.preventDefault();
    if (!potEnviar) return;
    setEnviant(true);
    try {
      const env = await api.crearEnviament({
        fitxa_ids: enviables.map((f) => f.fitxa_id),
        per_a: perA,
        cc,
        assumpte,
        cos,
      });
      seguir(env.id);
    } catch (err) {
      setEnviant(false);
      toast.error(missatgeError(err), 10000);
    }
  };

  return (
    <div className="modal-overlay" onClick={tancar}>
      <div className="modal-content modal-correu" role="dialog" aria-modal="true"
        aria-labelledby="enviar-correu-titol" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 id="enviar-correu-titol" style={{ margin: 0 }}>Enviar per correu</h3>
          <button type="button" className="outline secondary btn-sm" onClick={tancar}
            disabled={enviant} aria-label="Tancar">&times;</button>
        </div>

        {carregant ? (
          <p aria-busy="true">Preparant l'enviament...</p>
        ) : errorCarrega ? (
          <p style={{ color: 'var(--danger)' }}>{errorCarrega}</p>
        ) : (
          <form onSubmit={enviar}>
            {!info.configurat && (
              <div className="correu-avis correu-avis-error">
                L'enviament per correu encara no està configurat al servidor. Avisa l'administrador.
              </div>
            )}

            <p className="correu-remitent">
              S'enviarà des de <strong>{info.remitent}</strong> i quedarà als teus Elements enviats.
            </p>

            <label>
              Per a
              <input type="text" value={perA} onChange={(e) => setPerA(e.target.value)}
                placeholder="client@empresa.com (diverses adreces separades per comes)"
                disabled={enviant} required autoFocus />
            </label>
            <label>
              CC <span className="correu-opcional">(opcional)</span>
              <input type="text" value={cc} onChange={(e) => setCc(e.target.value)}
                placeholder="adreces separades per comes" disabled={enviant} />
            </label>
            <label>
              Assumpte
              <input type="text" value={assumpte} onChange={(e) => setAssumpte(e.target.value)}
                disabled={enviant} required maxLength={500} />
            </label>
            <label>
              Missatge
              <textarea rows={9} value={cos} onChange={(e) => setCos(e.target.value)} disabled={enviant} />
            </label>

            <div className="correu-adjunts">
              <strong>Adjunts ({enviables.length})</strong>
              <ul>
                {enviables.map((f) => (
                  <li key={f.fitxa_id}>
                    <code>{f.nom_fitxer}</code> {f.nom_producte} <span className="correu-opcional">· rev. {f.num_versio}</span>
                  </li>
                ))}
              </ul>
              {noEnviables.length > 0 && (
                <div className="correu-avis">
                  No s'enviaran ({noEnviables.length}):{' '}
                  {noEnviables.map((f) => `${f.art_codi || f.fitxa_id} (${f.motiu})`).join(', ')}
                </div>
              )}
              {massaFitxes && (
                <div className="correu-avis correu-avis-error">
                  Màxim {info.max_adjunts} fitxes per correu. Desmarca'n alguna.
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button type="button" className="outline secondary" onClick={tancar} disabled={enviant}>
                Cancel·lar
              </button>
              <button type="submit" disabled={!potEnviar} aria-busy={enviant}>
                {enviant ? 'Enviant...' : 'Enviar'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default EnviarCorreuModal;
