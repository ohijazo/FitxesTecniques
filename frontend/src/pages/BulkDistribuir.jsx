import { useEffect, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

/**
 * Distribució massiva — pàgina sencera (no modal), consistent amb BulkEdit.
 *
 * Les fitxes seleccionades arriben per `location.state.fitxa_ids`.
 */
function BulkDistribuir() {
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();

  const fitxaIds = location.state?.fitxa_ids || [];

  const [destins, setDestins] = useState([]);
  const [seleccionats, setSeleccionats] = useState(new Set());
  const [fitxesInfo, setFitxesInfo] = useState([]);
  const [veureFitxes, setVeureFitxes] = useState(false);
  const [loading, setLoading] = useState(true);
  const [enviant, setEnviant] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (fitxaIds.length === 0) navigate('/', { replace: true });
  }, [fitxaIds.length, navigate]);

  useEffect(() => {
    if (fitxaIds.length === 0) return;
    let actiu = true;

    api.llistarDestins()
      .then((data) => {
        if (!actiu) return;
        const actius = (data || []).filter((d) => d.actiu);
        setDestins(actius);
        setSeleccionats(new Set(actius.map((d) => d.id)));
        setLoading(false);
      })
      .catch((e) => {
        if (!actiu) return;
        setError(e.message);
        setLoading(false);
      });

    Promise.all(
      fitxaIds.map((id) =>
        api.detallFitxa(id)
          .then((d) => ({ id, codi: d.art_codi, nom: d.nom_producte }))
          .catch(() => null)
      )
    ).then((res) => { if (actiu) setFitxesInfo(res.filter(Boolean)); });

    return () => { actiu = false; };
  }, [fitxaIds]);

  const toggleDesti = (id) => {
    setSeleccionats((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalOperacions = fitxaIds.length * seleccionats.size;
  const potSubmit = seleccionats.size > 0 && !enviant && !loading;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (seleccionats.size === 0) {
      setError('Cal seleccionar com a mínim un destí');
      return;
    }
    setEnviant(true);
    setError(null);
    try {
      const job = await api.crearJobDistribucio({
        fitxa_ids: fitxaIds,
        desti_ids: [...seleccionats],
      });
      toast.success(`Job #${job.id} creat (${job.total_items} operacions)`);
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(err.message);
      setEnviant(false);
    }
  };

  if (fitxaIds.length === 0) return null;

  return (
    <div className="bulk-edit-v2">
      <header className="bulk-edit-v2-header">
        <h2>Distribució massiva</h2>
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

      {loading ? (
        <p aria-busy="true">Carregant destins…</p>
      ) : destins.length === 0 ? (
        <div className="empty-state">
          <p style={{ color: 'var(--warning)' }}>No hi ha destins actius configurats.</p>
          <Link to="/admin/destins">Configurar destins →</Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          {/* Step 1: destins */}
          <section className="bulk-step">
            <div className="bulk-step-header">
              <span className="bulk-step-number">1</span>
              <h3>Destins on enviar la versió activa</h3>
            </div>

            <ul className="desti-checklist">
              {destins.map((d) => {
                const checked = seleccionats.has(d.id);
                return (
                  <li
                    key={d.id}
                    className={`desti-checklist-item ${checked ? 'is-checked' : ''}`}
                    onClick={() => toggleDesti(d.id)}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleDesti(d.id)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <div className="desti-checklist-info">
                      <div className="desti-checklist-nom">{d.nom}</div>
                      <div className="desti-checklist-tipus">
                        {d.tipus === 'ftp' && 'FTP'}
                        {d.tipus === 'xarxa' && 'Carpeta de xarxa'}
                        {d.tipus === 'sharepoint' && 'SharePoint Online'}
                        {d.tipus === 'sap' && 'SAP Business One'}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>

          {/* Step 2: resum + confirmació */}
          <section className="bulk-step bulk-step-final">
            <div className="bulk-step-header">
              <span className="bulk-step-number">2</span>
              <h3>Resum</h3>
            </div>

            <div className="bulk-distribuir-resum">
              <div className="bulk-resum-row">
                <strong>{fitxaIds.length}</strong>
                <span>{fitxaIds.length === 1 ? 'fitxa' : 'fitxes'}</span>
              </div>
              <div className="bulk-resum-x">×</div>
              <div className="bulk-resum-row">
                <strong>{seleccionats.size}</strong>
                <span>{seleccionats.size === 1 ? 'destí' : 'destins'}</span>
              </div>
              <div className="bulk-resum-x">=</div>
              <div className="bulk-resum-row bulk-resum-total">
                <strong>{totalOperacions}</strong>
                <span>operacions</span>
              </div>
            </div>

            <p className="bulk-edit-v2-hint" style={{ color: 'var(--gray-600)', marginTop: '0.85rem' }}>
              S'executaran en segon pla. Pots tancar el navegador i seguir el progrés més tard a la pàgina de jobs.
            </p>
          </section>

          {error && <p className="bulk-edit-v2-error">{error}</p>}
        </form>
      )}

      <div className="bulk-edit-v2-actions">
        <Link to="/" role="button" className="outline secondary">Cancel·lar</Link>
        <button type="button" onClick={handleSubmit} disabled={!potSubmit}>
          {enviant ? 'Creant…' : `Iniciar distribució (${totalOperacions})`}
        </button>
      </div>
    </div>
  );
}

export default BulkDistribuir;
