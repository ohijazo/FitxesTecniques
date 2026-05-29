import { useEffect, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { DEFAULT_SECTIONS } from '../components/FitxaForm';

/**
 * Edició massiva — layout vertical, una sola columna centrada.
 * El protagonisme visual va per "camp a modificar" i "nou valor", no per
 * la llista de fitxes (que és context col·lapsable).
 *
 * Les fitxes seleccionades arriben per `location.state.fitxa_ids`.
 */

const CAMPS_PROHIBITS = new Set(['art_codi', 'codi_referencia']);

function labelCatala(label) {
  if (!label) return '';
  const parts = label.split('/');
  if (parts.length >= 2) return parts[parts.length - 1].trim();
  return label.trim();
}

function llistaCampsPerSeccio(sections) {
  return sections.map((sec) => ({
    seccioLabel: labelCatala(sec.label),
    items: (sec.items || [])
      .filter((it) => it.type !== 'table' && !CAMPS_PROHIBITS.has(it.key))
      .map((it) => ({
        nom: it.key,
        label: labelCatala(it.label),
        tipus: it.type || 'text',
      })),
  })).filter((g) => g.items.length > 0);
}

function strip(s) {
  if (!s) return '';
  return String(s).replace(/<[^>]+>/g, '').trim();
}

function BulkEdit() {
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();

  const fitxaIds = location.state?.fitxa_ids || [];
  const [seccionsCamps] = useState(() => llistaCampsPerSeccio(DEFAULT_SECTIONS));

  const [canvis, setCanvis] = useState([{ camp_nom: '', valor: '', mode_nou: false, label_nou: '', seccio_nou: '' }]);
  const [descripcioCanvi, setDescripcioCanvi] = useState('');
  const [password, setPassword] = useState('');
  const [accepto, setAccepto] = useState(false);
  const [enviant, setEnviant] = useState(false);
  const [error, setError] = useState(null);
  const [fitxesInfo, setFitxesInfo] = useState([]);
  const [veureFitxes, setVeureFitxes] = useState(false);

  // Si no hi ha selecció, tornar al llistat
  useEffect(() => {
    if (fitxaIds.length === 0) navigate('/', { replace: true });
  }, [fitxaIds.length, navigate]);

  // Carregar info de les fitxes (per llista + preview de valors actuals)
  useEffect(() => {
    if (fitxaIds.length === 0) return;
    Promise.all(
      fitxaIds.map((id) =>
        api.detallFitxa(id)
          .then((d) => {
            const activa = (d.versions || []).find((v) => v.activa);
            return {
              id,
              codi: d.art_codi,
              nom: d.nom_producte,
              contingut: activa ? activa.contingut || {} : {},
            };
          })
          .catch(() => null)
      )
    ).then((res) => setFitxesInfo(res.filter(Boolean)));
  }, [fitxaIds]);

  const afegirCanvi = () => setCanvis((c) => [...c, { camp_nom: '', valor: '', mode_nou: false, label_nou: '', seccio_nou: '' }]);
  const eliminarCanvi = (i) => setCanvis((c) => c.filter((_, idx) => idx !== i));
  const actualitzarCanvi = (i, field, val) => {
    setCanvis((c) => c.map((x, idx) => idx === i ? { ...x, [field]: val } : x));
  };

  // Activar mode "crear camp nou" en aquesta entrada
  const activarModeNou = (i) => {
    setCanvis((c) => c.map((x, idx) => idx === i ? { ...x, mode_nou: true, camp_nom: '', label_nou: '', seccio_nou: '' } : x));
  };
  // Tornar a mode "selecciona d'un existent"
  const cancellarModeNou = (i) => {
    setCanvis((c) => c.map((x, idx) => idx === i ? { ...x, mode_nou: false, camp_nom: '', label_nou: '', seccio_nou: '' } : x));
  };

  // Valida que un identificador de camp nou és vàlid (snake_case, no col·lideix amb prohibits)
  const validarKeyNova = (key) => {
    if (!key) return 'Cal escriure un identificador';
    if (!/^[a-z][a-z0-9_]{1,49}$/.test(key)) {
      return 'Només minúscules, números i guions baixos (començant per lletra, max 50 caràcters)';
    }
    if (CAMPS_PROHIBITS.has(key)) return 'Aquest identificador no es pot fer servir (immutable)';
    // Si col·lideix amb un camp ja existent, redirigir a fer servir aquell
    for (const sec of seccionsCamps) {
      if (sec.items.some((it) => it.nom === key)) {
        return `Ja existeix un camp "${key}". Selecciona'l del desplegable enlloc de crear-lo.`;
      }
    }
    return null;
  };

  // Un canvi és vàlid si: té camp_nom + (no està en mode_nou OR la key és vàlida + té secció)
  const canvisValids = canvis.filter((c) => {
    if (!c.camp_nom) return false;
    if (c.mode_nou) {
      if (validarKeyNova(c.camp_nom)) return false;
      if (!c.seccio_nou) return false;
    }
    return true;
  });
  const objCanvis = Object.fromEntries(canvisValids.map((c) => [c.camp_nom, c.valor]));
  const numCamps = Object.keys(objCanvis).length;
  const descripcioOk = descripcioCanvi.trim().length >= 10;
  const potSubmit = numCamps > 0 && descripcioOk && password && accepto && !enviant;

  const findCamp = (nom) => {
    for (const sec of seccionsCamps) {
      const c = sec.items.find((it) => it.nom === nom);
      if (c) return { camp: c, seccio: sec.seccioLabel };
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!potSubmit) {
      if (numCamps === 0) setError('Cal seleccionar com a mínim un camp');
      else if (!descripcioOk) setError('La descripció ha de tenir com a mínim 10 caràcters');
      else if (!password) setError('Cal introduir la teva contrasenya');
      else if (!accepto) setError('Cal marcar la casella de confirmació');
      return;
    }
    setEnviant(true);
    try {
      const resum = await api.bulkEditFitxes({
        fitxa_ids: fitxaIds,
        canvis: objCanvis,
        descripcio_canvi: descripcioCanvi.trim(),
        password,
      });
      if (resum.errors && resum.errors.length > 0) {
        toast.error(`Edició feta: ${resum.ok.length} ok, ${resum.errors.length} amb error`);
      } else {
        toast.success(`Edició massiva feta: ${resum.ok.length} fitxes actualitzades`);
      }
      navigate('/');
    } catch (err) {
      setError(err.message);
      setEnviant(false);
    }
  };

  if (fitxaIds.length === 0) return null;

  return (
    <div className="bulk-edit-v2">
      {/* Capçalera */}
      <header className="bulk-edit-v2-header">
        <h2>Edició massiva</h2>
        <p className="bulk-edit-v2-subtitle">
          <strong>{fitxaIds.length}</strong>{' '}
          {fitxaIds.length === 1 ? 'fitxa seleccionada' : 'fitxes seleccionades'}
          {' · '}
          <button
            type="button"
            className="link-button"
            onClick={() => setVeureFitxes((v) => !v)}
          >
            {veureFitxes ? 'amagar llistat' : 'veure llistat'}
          </button>
        </p>

        {veureFitxes && (
          <div className="bulk-edit-v2-chips">
            {fitxesInfo.length === 0 ? (
              <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }} aria-busy="true">
                Carregant…
              </span>
            ) : (
              fitxesInfo.map((f) => (
                <span key={f.id} className="bulk-chip" title={f.nom}>
                  <code>{f.codi}</code> — {f.nom}
                </span>
              ))
            )}
          </div>
        )}
      </header>

      <form onSubmit={handleSubmit} className="bulk-edit-v2-form">
        {canvis.map((c, i) => {
          const info = !c.mode_nou && c.camp_nom ? findCamp(c.camp_nom) : null;
          const keyError = c.mode_nou ? validarKeyNova(c.camp_nom) : null;
          const campLlest = c.mode_nou
            ? !!c.camp_nom && !keyError && !!c.seccio_nou
            : !!info;
          // Recull valors actuals d'aquest camp a cada fitxa (només per camps existents)
          const valorsActuals = info
            ? fitxesInfo.map((f) => ({
                codi: f.codi,
                valor: strip(f.contingut[c.camp_nom]),
              }))
            : [];
          const valorsUnics = new Set(valorsActuals.map((v) => v.valor));

          return (
            <section key={i} className="bulk-step">
              <div className="bulk-step-header">
                <span className="bulk-step-number">{i + 1}</span>
                <h3>
                  {canvis.length === 1 ? 'Camp a modificar' : `Canvi ${i + 1}`}
                </h3>
                {canvis.length > 1 && (
                  <button
                    type="button"
                    className="link-button danger"
                    onClick={() => eliminarCanvi(i)}
                    disabled={enviant}
                  >
                    eliminar
                  </button>
                )}
              </div>

              {/* Selector: dropdown o inputs si mode_nou */}
              {!c.mode_nou ? (
                <>
                  <select
                    value={c.camp_nom}
                    onChange={(e) => {
                      if (e.target.value === '__NEW__') activarModeNou(i);
                      else actualitzarCanvi(i, 'camp_nom', e.target.value);
                    }}
                    disabled={enviant}
                    className="bulk-field-select"
                  >
                    <option value="">— Selecciona un camp —</option>
                    {seccionsCamps.map((sec) => (
                      <optgroup key={sec.seccioLabel} label={sec.seccioLabel}>
                        {sec.items.map((cd) => (
                          <option key={cd.nom} value={cd.nom}>{cd.label}</option>
                        ))}
                      </optgroup>
                    ))}
                    <option value="__NEW__">+ Crear un camp nou…</option>
                  </select>
                </>
              ) : (
                <div className="bulk-camp-nou">
                  <div className="bulk-camp-nou-header">
                    <strong>Crear un camp nou</strong>
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => cancellarModeNou(i)}
                      disabled={enviant}
                    >
                      cancel·lar i triar un existent
                    </button>
                  </div>

                  {/* 1. Secció (on anirà el camp) */}
                  <label>
                    <span className="bulk-label">
                      1. A quina secció de la fitxa va aquest camp?
                    </span>
                    <select
                      value={c.seccio_nou}
                      onChange={(e) => actualitzarCanvi(i, 'seccio_nou', e.target.value)}
                      disabled={enviant}
                    >
                      <option value="">— Selecciona una secció —</option>
                      {seccionsCamps.map((sec) => (
                        <option key={sec.seccioLabel} value={sec.seccioLabel}>{sec.seccioLabel}</option>
                      ))}
                    </select>
                  </label>

                  {/* 2. Etiqueta visible (nom amigable) */}
                  <label>
                    <span className="bulk-label">
                      2. Nom del camp <small>(com es veurà a la fitxa)</small>
                    </span>
                    <input
                      type="text"
                      value={c.label_nou}
                      onChange={(e) => actualitzarCanvi(i, 'label_nou', e.target.value)}
                      placeholder="Ex: Data de caducitat un cop obert"
                      disabled={enviant || !c.seccio_nou}
                    />
                  </label>

                  {/* 3. Identificador intern (snake_case) */}
                  <label>
                    <span className="bulk-label">
                      3. Identificador intern
                      <small> (snake_case, sense espais; ex: <code>data_caducitat_obert</code>)</small>
                    </span>
                    <input
                      type="text"
                      value={c.camp_nom}
                      onChange={(e) => actualitzarCanvi(i, 'camp_nom', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                      placeholder="data_caducitat_obert"
                      disabled={enviant || !c.seccio_nou}
                    />
                  </label>
                  {c.camp_nom && keyError && (
                    <p className="bulk-edit-v2-error" style={{ marginTop: 0 }}>{keyError}</p>
                  )}

                  {c.seccio_nou && c.camp_nom && !keyError && (
                    <div className="bulk-camp-nou-resum">
                      Es crearà <code>{c.label_nou || c.camp_nom}</code> a la secció{' '}
                      <strong>{c.seccio_nou}</strong> (clau interna <code>{c.camp_nom}</code>).
                    </div>
                  )}

                  <div className="bulk-edit-v2-warning-soft">
                    <strong>Avís:</strong> el valor s'afegirà al JSON de les <strong>{fitxaIds.length} fitxes seleccionades</strong>.
                    Perquè el camp aparegui també al <strong>formulari d'edició estàndard</strong> i al PDF, caldrà
                    actualitzar la configuració global (<em>Configuració → Camps</em>) per registrar-lo a la secció triada.
                  </div>
                </div>
              )}

              {info && (
                <>
                  {/* Preview de valors actuals (només per camps existents) */}
                  <details className="bulk-edit-v2-preview">
                    <summary>
                      Veure valors actuals a les fitxes
                      {valorsUnics.size > 1 && (
                        <span className="bulk-tag-warning">
                          {valorsUnics.size} valors diferents
                        </span>
                      )}
                    </summary>
                    <div className="bulk-edit-v2-preview-content">
                      <table>
                        <thead>
                          <tr>
                            <th style={{ width: '90px' }}>Codi</th>
                            <th>Valor actual</th>
                          </tr>
                        </thead>
                        <tbody>
                          {valorsActuals.map((v, idx) => (
                            <tr key={idx}>
                              <td><code>{v.codi}</code></td>
                              <td className="bulk-preview-cell">
                                {v.valor || <em style={{ color: 'var(--gray-500)' }}>(buit)</em>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                </>
              )}

              {campLlest && (
                <>
                  {/* Step 2: nou valor */}
                  <div className="bulk-step-header" style={{ marginTop: '1.5rem' }}>
                    <span className="bulk-step-number">{i + 1}b</span>
                    <h3>Nou valor</h3>
                  </div>
                  <textarea
                    value={c.valor}
                    onChange={(e) => actualitzarCanvi(i, 'valor', e.target.value)}
                    placeholder={info
                      ? `Escriu el nou text per a "${info.camp.label}"`
                      : `Escriu el nou text per a "${c.label_nou || c.camp_nom}"`}
                    rows={10}
                    disabled={enviant}
                    className="bulk-value-textarea"
                  />
                  <p className="bulk-edit-v2-hint">
                    ⚠ S'aplica com a text pla. Si alguna fitxa tenia format ric (negretes, colors), aquest format es perdrà.
                  </p>
                </>
              )}
            </section>
          );
        })}

        {/* Acció secundària: afegir més camps */}
        <div className="bulk-edit-v2-add-wrapper">
          <button
            type="button"
            className="bulk-edit-v2-add"
            onClick={afegirCanvi}
            disabled={enviant}
          >
            <span className="bulk-edit-v2-add-icon">+</span>
            Afegir un altre camp a modificar
          </button>
          <p className="bulk-edit-v2-add-hint">
            Si en aquesta mateixa operació vols canviar més camps a les mateixes fitxes
          </p>
        </div>

        {/* Step 3: confirmació */}
        <section className="bulk-step bulk-step-final">
          <div className="bulk-step-header">
            <span className="bulk-step-number">{canvis.length + 1}</span>
            <h3>Confirmació</h3>
          </div>

          <label>
            <span className="bulk-label">Descripció del canvi <small>(quedarà a l'historial)</small></span>
            <textarea
              value={descripcioCanvi}
              onChange={(e) => setDescripcioCanvi(e.target.value)}
              placeholder="Ex: Actualització normativa RD 999/2026"
              rows={2}
              disabled={enviant}
              required
              minLength={10}
            />
          </label>

          <label>
            <span className="bulk-label">La teva contrasenya</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Per confirmar l'acció"
              disabled={enviant}
              required
              autoComplete="current-password"
            />
          </label>

          <label className={`bulk-confirm-check ${accepto ? 'is-checked' : ''}`}>
            <input
              type="checkbox"
              checked={accepto}
              onChange={(e) => setAccepto(e.target.checked)}
              disabled={enviant}
            />
            <span>
              Entenc que es crearan <strong>{fitxaIds.length} noves versions publicades</strong> i que <strong>no es pot desfer</strong>.
            </span>
          </label>
        </section>

        {error && <p className="bulk-edit-v2-error">{error}</p>}
      </form>

      {/* Footer sticky amb les accions */}
      <div className="bulk-edit-v2-actions">
        <Link to="/" role="button" className="outline secondary">
          Cancel·lar
        </Link>
        <button type="button" onClick={handleSubmit} disabled={!potSubmit}>
          {enviant ? 'Aplicant…' : `Aplicar a ${fitxaIds.length} ${fitxaIds.length === 1 ? 'fitxa' : 'fitxes'}`}
        </button>
      </div>
    </div>
  );
}

export default BulkEdit;
