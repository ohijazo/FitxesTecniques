import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

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

function LlistaFitxes() {
  const [fitxes, setFitxes] = useState([]);
  const [cerca, setCerca] = useState('');
  const [estat, setEstat] = useState(() => localStorage.getItem('filtre_estat') || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const toast = useToast();

  const carregarFitxes = async (textCerca = '', filtreEstat = estat) => {
    setLoading(true);
    try {
      const params = { per_page: 50 };
      if (textCerca) params.cerca = textCerca;
      if (filtreEstat) params.estat = filtreEstat;
      const data = await api.llistarFitxes(params);
      setFitxes(data.fitxes);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { carregarFitxes(cerca, estat); }, [estat]);

  const handleCerca = (e) => {
    e.preventDefault();
    carregarFitxes(cerca, estat);
  };

  const handleEstat = (e) => {
    const val = e.target.value;
    setEstat(val);
    localStorage.setItem('filtre_estat', val);
  };

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


  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0 }}>Fitxes tècniques</h2>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.88rem', margin: '0.2rem 0 0' }}>
            {total} fitxes registrades
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
          <select value={estat} onChange={handleEstat} style={{ margin: 0 }}>
            <option value="">Tots els estats</option>
            <option value="publicada">Publicada</option>
            <option value="obsoleta">Obsoleta</option>
            <option value="inactiva">Inactiva</option>
          </select>
        </label>
        <button type="submit" style={{ whiteSpace: 'nowrap', marginBottom: 0 }}>Cercar</button>
      </form>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

      {loading ? (
        <p aria-busy="true">Carregant fitxes...</p>
      ) : fitxes.length === 0 ? (
        <div className="empty-state">
          <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No s'han trobat fitxes</p>
          <p>Prova a canviar els filtres o <Link to="/fitxes/nova">crea la primera fitxa</Link>.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Codi</th>
                <th>Producte</th>
                <th>Rev.</th>
                <th>Estat</th>
                <th>Distribució</th>
                <th>Actualitzat</th>
                <th style={{ textAlign: 'right' }}>Accions</th>
              </tr>
            </thead>
            <tbody>
              {fitxes.map((f) => (
                <tr key={f.id}>
                  <td>
                    <Link to={`/fitxes/${f.id}`} style={{ fontWeight: 600 }}>
                      <code>{f.art_codi}</code>
                    </Link>
                  </td>
                  <td>
                    <Link to={`/fitxes/${f.id}`} style={{ color: 'var(--gray-800)' }}>
                      {f.nom_producte}
                    </Link>
                  </td>
                  <td style={{ textAlign: 'center', color: 'var(--gray-600)', fontWeight: 600 }}>
                    {f.versio_activa != null ? f.versio_activa : '-'}
                  </td>
                  <td><span className={`badge ${f.estat}`}>{f.estat}</span></td>
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
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export default LlistaFitxes;
