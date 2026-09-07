import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';

const TIPUS_LABEL = {
  ftp: 'FTP',
  sftp: 'SFTP',
  xarxa: 'Carpeta de xarxa',
  sharepoint: 'SharePoint Online',
  sap: 'SAP Business One',
};

// Els destins de tipus 'sap' no es poden comprovar (no hi ha descàrrega).
const COMPROVABLE = ['ftp', 'sftp', 'xarxa', 'sharepoint'];

/**
 * Comprovació de destins — auditoria massiva.
 *
 * L'estat "ok" de l'historial de distribucions només vol dir que la pujada no
 * va fallar. Aquesta pàgina llança un job que torna a llegir el PDF de cada
 * destí per veure si realment hi és i si la revisió coincideix amb la BD.
 * Només informa: no modifica ni la base de dades ni els destins.
 */
function ComprovacioDestins() {
  const navigate = useNavigate();
  const toast = useToast();

  const [destins, setDestins] = useState([]);
  const [seleccionats, setSeleccionats] = useState(new Set());
  const [nomesDistribuides, setNomesDistribuides] = useState(false);
  const [jobsPrevis, setJobsPrevis] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enviant, setEnviant] = useState(false);
  const [confirmant, setConfirmant] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let actiu = true;

    api.llistarDestins()
      .then((data) => {
        if (!actiu) return;
        const comprovables = (data || [])
          .filter((d) => d.actiu && COMPROVABLE.includes(d.tipus));
        setDestins(comprovables);
        setSeleccionats(new Set(comprovables.map((d) => d.id)));
        setLoading(false);
      })
      .catch((e) => {
        if (!actiu) return;
        setError(e.message);
        setLoading(false);
      });

    api.llistarJobs({ tipus: 'verificacio_massiva', per_page: 5 })
      .then((r) => { if (actiu) setJobsPrevis(r.jobs || []); })
      .catch(() => {});

    return () => { actiu = false; };
  }, []);

  const toggleDesti = (id) => {
    setSeleccionats((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const potSubmit = seleccionats.size > 0 && !enviant && !loading;

  const demanarConfirmacio = () => {
    if (seleccionats.size === 0) {
      setError('Cal seleccionar com a mínim un destí');
      return;
    }
    setError(null);
    setConfirmant(true);
  };

  const iniciar = async () => {
    setConfirmant(false);
    setEnviant(true);
    setError(null);
    try {
      const job = await api.crearJobVerificacio({
        desti_ids: [...seleccionats],
        nomes_distribuides: nomesDistribuides,
      });
      toast.success(`Comprovació #${job.id} iniciada (${job.total_items} comprovacions)`);
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(err.message);
      setEnviant(false);
    }
  };

  return (
    <div className="bulk-edit-v2">
      <header className="bulk-edit-v2-header">
        <h2>Comprovació de destins</h2>
        <p className="bulk-edit-v2-subtitle">
          Comprova si l'estat real dels destins coincideix amb el que diu
          l'aplicació: que les fitxes hi siguin on han de ser-hi, i que{' '}
          <strong>no hi siguin</strong> on no toca.
        </p>
        <p className="bulk-edit-v2-hint" style={{ color: 'var(--gray-600)' }}>
          Aquesta comprovació només informa: no modifica cap fitxa, cap historial
          de distribucions ni cap fitxer dels destins.
        </p>
      </header>

      {loading ? (
        <p aria-busy="true">Carregant destins…</p>
      ) : destins.length === 0 ? (
        <div className="empty-state">
          <p style={{ color: 'var(--warning)' }}>
            No hi ha destins actius que es puguin comprovar.
          </p>
          <Link to="/admin/destins">Configurar destins →</Link>
        </div>
      ) : (
        <>
          {/* Step 1: destins */}
          <section className="bulk-step">
            <div className="bulk-step-header">
              <span className="bulk-step-number">1</span>
              <h3>Destins a comprovar</h3>
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
                        {TIPUS_LABEL[d.tipus] || d.tipus}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>

          {/* Step 2: abast */}
          <section className="bulk-step">
            <div className="bulk-step-header">
              <span className="bulk-step-number">2</span>
              <h3>Quines fitxes</h3>
            </div>

            <label style={{ display: 'flex', gap: '0.7rem', alignItems: 'flex-start' }}>
              <input
                type="radio"
                name="abast"
                checked={!nomesDistribuides}
                onChange={() => setNomesDistribuides(false)}
                style={{ marginTop: '0.25rem' }}
              />
              <span>
                <strong>Totes les fitxes, en les dues direccions</strong> (recomanat)
                <br />
                <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                  Per cada fitxa comprova tots els destins seleccionats: on
                  consta distribuïda ha de ser-hi, i on no hi consta no hi ha de
                  ser. És l'única manera de trobar els PDF <strong>sobrants</strong>,
                  els que van quedar en un destí d'on s'havien de retirar.
                </span>
              </span>
            </label>

            <label style={{ display: 'flex', gap: '0.7rem', alignItems: 'flex-start', marginTop: '0.9rem' }}>
              <input
                type="radio"
                name="abast"
                checked={nomesDistribuides}
                onChange={() => setNomesDistribuides(true)}
                style={{ marginTop: '0.25rem' }}
              />
              <span>
                <strong>Només on consta distribuïda</strong>
                <br />
                <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                  Molt més ràpid, però no detecta els sobrants: només mira que
                  hi siguin allà on l'historial diu que hi són.
                </span>
              </span>
            </label>
          </section>

          <section className="bulk-step bulk-step-final">
            <div className="bulk-step-header">
              <span className="bulk-step-number">3</span>
              <h3>Executar</h3>
            </div>
            <p className="bulk-edit-v2-hint" style={{ color: 'var(--gray-600)' }}>
              La comprovació s'executa en segon pla i pot trigar força estona.
              Comprovar un destí on la fitxa no hi ha de ser és barat (el
              servidor respon que no existeix sense transferir res); només es
              descarrega el PDF quan realment hi ha alguna cosa. Pots tancar el
              navegador i seguir el progrés des de Jobs massius. Les
              distribucions tenen prioritat sobre les comprovacions a la cua.
            </p>
          </section>

          {error && <p className="bulk-edit-v2-error">{error}</p>}
        </>
      )}

      <div className="bulk-edit-v2-actions">
        <Link to="/" role="button" className="outline secondary">Cancel·lar</Link>
        <button type="button" onClick={demanarConfirmacio} disabled={!potSubmit}>
          {enviant ? 'Iniciant…' : 'Iniciar comprovació'}
        </button>
      </div>

      {jobsPrevis.length > 0 && (
        <section className="card" style={{ marginTop: '1.5rem' }}>
          <h3 style={{ marginTop: 0, fontSize: '1rem' }}>Comprovacions anteriors</h3>
          <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
            {jobsPrevis.map((j) => (
              <li key={j.id} style={{ marginBottom: '0.3rem' }}>
                <Link to={`/jobs/${j.id}`}>Comprovació #{j.id}</Link>{' '}
                <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                  — {j.estat} · {j.total_items} comprovacions
                  {j.created_at ? ` · ${new Date(j.created_at).toLocaleString('ca-ES')}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <ConfirmDialog
        obert={confirmant}
        titol="Iniciar la comprovació de destins"
        textConfirmar="Iniciar comprovació"
        ocupat={enviant}
        onConfirmar={iniciar}
        onCancelar={() => setConfirmant(false)}
      >
        <p style={{ margin: '0 0 0.5rem' }}>
          Es comprovaran{' '}
          <strong>{seleccionats.size} {seleccionats.size === 1 ? 'destí' : 'destins'}</strong>
          {nomesDistribuides
            ? ' només per a les fitxes que hi consten distribuïdes.'
            : ' per a totes les fitxes amb versió publicada, en les dues direccions.'}
        </p>
        <p style={{ margin: 0 }}>
          Es descarregarà un PDF per cada comprovació, de manera que pot trigar
          hores. No es modificarà res: només es genera l'informe.
        </p>
      </ConfirmDialog>
    </div>
  );
}

export default ComprovacioDestins;
