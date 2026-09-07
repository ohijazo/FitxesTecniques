import { useState } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import BadgeVerificacio from './BadgeVerificacio';
import EnllacDesti from './EnllacDesti';

/** "5 → 4" quan difereixen; "5" quan coincideixen. */
function Comparacio({ bd, desti, diferent }) {
  const valorBd = bd === null || bd === undefined || bd === '' ? '—' : bd;
  const valorDesti = desti === null || desti === undefined || desti === '' ? '—' : desti;
  if (!diferent) return <span>{valorBd}</span>;
  return (
    <span>
      {valorBd} <span style={{ color: 'var(--gray-400)' }}>→</span>{' '}
      <strong style={{ color: 'var(--danger)' }}>{valorDesti}</strong>
    </span>
  );
}

/**
 * Comprova si el PDF de la fitxa hi és realment als destins.
 *
 * L'historial de distribucions diu "ok" quan la pujada no va fallar, però ningú
 * no torna a mirar el destí. Aquest panell sí. Només llegeix: no modifica res.
 */
function ComprovarDestinsPanel({ fitxaId, onClose }) {
  const [resultat, setResultat] = useState(null);
  const [carregant, setCarregant] = useState(false);
  const [error, setError] = useState(null);
  const toast = useToast();

  const comprovar = async (nomesDistribuides) => {
    setCarregant(true);
    setError(null);
    try {
      const r = await api.comprovarDestins(
        fitxaId, nomesDistribuides ? { nomes_distribuides: true } : {});
      setResultat(r);
      const problemes = (r.resultats || []).filter(
        (x) => x.estat_verificacio !== 'ok'
      ).length;
      if (problemes === 0 && (r.resultats || []).length > 0) {
        toast.success('Tot correcte: les fitxes hi són als destins');
      } else if (problemes > 0) {
        toast.warning(`${problemes} ${problemes === 1 ? 'destí' : 'destins'} amb incidències`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCarregant(false);
    }
  };

  return (
    <div className="card" style={{ border: '2px solid var(--brand-light)' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: '1rem',
      }}>
        <h3 style={{ margin: 0 }}>Comprovar destins</h3>
        <button className="outline secondary btn-sm" onClick={onClose}>Tancar</button>
      </div>

      <p style={{ fontSize: '0.88rem', color: 'var(--gray-500)', marginBottom: '1rem' }}>
        Es comprova cada destí en les dues direccions: on la fitxa consta
        distribuïda, que hi sigui i coincideixi; on no hi consta, que no hi
        sigui. Cada resultat porta l'enllaç al fitxer del destí, per si el vols
        obrir i revisar. Només informa: no modifica ni la fitxa ni els fitxers
        dels destins.
      </p>

      <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <button type="button" onClick={() => comprovar(false)} disabled={carregant}>
          {carregant ? 'Comprovant…' : 'Comprovar tots els destins'}
        </button>
        <button
          type="button"
          className="outline secondary"
          onClick={() => comprovar(true)}
          disabled={carregant}
        >
          Només on consta distribuïda
        </button>
      </div>

      {carregant && (
        <p aria-busy="true">
          Connectant amb els destins… pot trigar mig minut.
        </p>
      )}

      {error && <p className="bulk-edit-v2-error">{error}</p>}

      {resultat && !carregant && (
        resultat.resultats.length === 0 ? (
          <p style={{ color: 'var(--gray-500)' }}>
            {resultat.missatge || 'Cap destí a comprovar'}
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Destí</th>
                  <th>Hi ha de ser</th>
                  <th>Comprovació</th>
                  <th>Fitxer al destí</th>
                  <th>Rev.</th>
                  <th>Data revisió</th>
                  <th>Detall</th>
                </tr>
              </thead>
              <tbody>
                {resultat.resultats.map((r) => {
                  const dif = r.diferencies || [];
                  return (
                    <tr key={r.desti_id}>
                      <td>{r.desti_nom}</td>
                      <td style={{ fontSize: '0.82rem', color: 'var(--gray-600)' }}>
                        {r.esperat_al_desti ? 'Sí' : 'No'}
                      </td>
                      <td><BadgeVerificacio estat={r.estat_verificacio} /></td>
                      <td><EnllacDesti enllac={r.enllac} filename={r.filename} /></td>
                      <td>
                        <Comparacio
                          bd={r.bd?.rev}
                          desti={r.desti_valors?.rev}
                          diferent={dif.includes('rev')}
                        />
                      </td>
                      <td>
                        <Comparacio
                          bd={r.bd?.data_revisio}
                          desti={r.desti_valors?.data_revisio}
                          diferent={dif.includes('data_revisio')}
                        />
                      </td>
                      <td style={{ fontSize: '0.82rem', color: 'var(--gray-600)' }}>
                        {r.missatge}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}

export default ComprovarDestinsPanel;
