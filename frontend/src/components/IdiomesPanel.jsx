import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from './Toast';

/* Estats d'una traducció (els calcula el backend). */
export const ESTATS_TRADUCCIO = {
  revisada: { text: 'Revisada', classe: 'dist-ok' },
  pendent: { text: 'Pendent de revisar', classe: 'dist-partial' },
  desactualitzada: { text: 'De la versió anterior', classe: 'dist-partial' },
  falta: { text: 'Sense traduir', classe: 'dist-pending' },
};

/* Contingut de la versió amb la traducció a sobre, per mostrar-lo.
   Mateixa regla que combinar() del backend (services/traduccio.py): les
   taules es combinen fila a fila i només se'n canvien 'parametre' i 'valor'. */
export function combinarTraduccio(contingutVersio, traduccio, camps, idioma) {
  const resultat = JSON.parse(JSON.stringify(contingutVersio || {}));
  const t = traduccio || {};
  [...camps.text, ...camps.nota].forEach((k) => { if (t[k]) resultat[k] = t[k]; });
  camps.taula.forEach((k) => {
    if (!Array.isArray(t[k]) || !Array.isArray(resultat[k])) return;
    resultat[k] = resultat[k].map((fila, i) => {
      const ft = t[k][i] || {};
      return {
        ...fila,
        ...(ft.parametre ? { parametre: ft.parametre } : {}),
        ...(ft.valor ? { valor: ft.valor } : {}),
      };
    });
  });
  resultat._idioma = idioma;
  return resultat;
}

export function BadgeTraduccio({ estat }) {
  const e = ESTATS_TRADUCCIO[estat] || ESTATS_TRADUCCIO.falta;
  return <span className={`dist-badge ${e.classe}`}>{e.text}</span>;
}

/* Obre el PDF d'un idioma en una pestanya nova (cal el token: no n'hi ha prou
   amb un enllaç). La pestanya s'obre abans del fetch perquè el navegador no la
   bloquegi com a finestra emergent. */
export function obrirPdfIdioma(fitxaId, idioma, versioId, toast) {
  const finestra = window.open('', '_blank');
  const token = localStorage.getItem('token');
  const url = `/api/fitxes/${fitxaId}/pdf/${idioma}${versioId ? `?versio_id=${versioId}` : ''}`;
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(async (res) => {
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || 'No s\'ha pogut generar el PDF');
      }
      return res.blob();
    })
    .then((blob) => {
      const objUrl = URL.createObjectURL(blob);
      if (finestra) finestra.location.href = objUrl;
      else window.location.href = objUrl;
    })
    .catch((err) => {
      if (finestra) finestra.close();
      toast.error(err.message);
    });
}

/**
 * Pestanya "Idiomes" del detall de fitxa: Qualitat marca en quins idiomes ha
 * d'estar disponible la fitxa i veu l'estat de cada traducció.
 */
export default function IdiomesPanel({ fitxaId, artCodi, potEditar }) {
  const toast = useToast();
  const [resum, setResum] = useState(null);
  const [error, setError] = useState(null);
  const [desant, setDesant] = useState(false);

  const carregar = () => {
    api.resumTraduccions(fitxaId)
      .then((r) => { setResum(r); setError(null); })
      .catch((err) => setError(err.message));
  };
  useEffect(carregar, [fitxaId]);

  if (error) return <p style={{ color: 'var(--danger)' }}>{error}</p>;
  if (!resum) return <p aria-busy="true">Carregant...</p>;

  if (resum.comercialitzat) {
    return (
      <div className="card">
        <p style={{ color: 'var(--gray-600)', margin: 0 }}>
          Les fitxes de producte comercialitzat no es tradueixen: el seu PDF és el document del proveïdor.
        </p>
      </div>
    );
  }

  const canviarMarca = async (idioma, marcat) => {
    const nous = marcat
      ? [...resum.idiomes_marcats, idioma]
      : resum.idiomes_marcats.filter((i) => i !== idioma);
    setDesant(true);
    try {
      await api.marcarIdiomes(fitxaId, nous);
      carregar();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDesant(false);
    }
  };

  const versio = resum.versio;

  return (
    <div className="card idiomes-panel">
      <p style={{ marginTop: 0, color: 'var(--gray-600)', fontSize: '0.9rem' }}>
        Marca en quins idiomes ha d'estar disponible aquesta fitxa. Cada idioma té el seu PDF
        ({artCodi}_CA.pdf, {artCodi}_EN.pdf…), a més del PDF principal {artCodi}.pdf.
        Les traduccions van lligades a la versió {versio ? <strong>{versio.num_versio}</strong> : '—'} i
        corregir-les no crea una revisió nova.
      </p>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th style={{ width: '6rem' }}>Disponible</th>
              <th>Idioma</th>
              <th>Estat (versió activa)</th>
              <th>Revisada per</th>
              <th style={{ textAlign: 'right' }}>Accions</th>
            </tr>
          </thead>
          <tbody>
            {resum.idiomes.map((it) => {
              const t = it.traduccio;
              return (
                <tr key={it.idioma} className={it.marcat ? '' : 'idioma-no-marcat'}>
                  <td style={{ textAlign: 'center' }}>
                    <input type="checkbox" checked={it.marcat} disabled={!potEditar || desant}
                      aria-label={`Disponible en ${it.nom}`}
                      onChange={(e) => canviarMarca(it.idioma, e.target.checked)} />
                  </td>
                  <td><strong>{it.nom}</strong> <span style={{ color: 'var(--gray-400)' }}>({it.idioma.toUpperCase()})</span></td>
                  <td><BadgeTraduccio estat={it.estat} /></td>
                  <td style={{ fontSize: '0.85rem', color: 'var(--gray-600)' }}>
                    {t?.revisat_by ? <>{t.revisat_by}<br />{new Date(t.revisat_at).toLocaleDateString('ca')}</> : '—'}
                  </td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    {t && (
                      <button className="outline secondary btn-sm"
                        onClick={() => obrirPdfIdioma(fitxaId, it.idioma, versio?.id, toast)}>
                        Veure PDF
                      </button>
                    )}{' '}
                    {potEditar && versio && (it.marcat || t) && (
                      <Link to={`/fitxes/${fitxaId}/traduccio/${it.idioma}`} role="button" className="outline btn-sm">
                        {t ? 'Editar traducció' : 'Traduir'}
                      </Link>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!resum.ia_disponible && (
        <p style={{ fontSize: '0.8rem', color: 'var(--gray-500)', marginBottom: 0 }}>
          La traducció automàtica a l'anglès i al portuguès no està activada al servidor: es poden escriure a mà.
        </p>
      )}
    </div>
  );
}
