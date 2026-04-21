import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

function LlistaFitxes() {
  const [fitxes, setFitxes] = useState([]);
  const [cerca, setCerca] = useState('');
  const [estat, setEstat] = useState(() => localStorage.getItem('filtre_estat') || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);

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

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0 }}>Fitxes tècniques</h2>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.88rem', margin: '0.2rem 0 0' }}>
            {total} fitxes registrades
          </p>
        </div>
      </div>

      <form onSubmit={handleCerca} style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', alignItems: 'flex-end' }}>
        <label style={{ flex: 1, margin: 0 }}>
          <input
            type="search"
            placeholder="Cercar per codi o nom..."
            value={cerca}
            onChange={(e) => setCerca(e.target.value)}
            style={{ margin: 0 }}
          />
        </label>
        <label style={{ margin: 0, width: '180px' }}>
          <select value={estat} onChange={handleEstat} style={{ margin: 0 }}>
            <option value="">Tots els estats</option>
            <option value="publicada">Publicada</option>
            <option value="obsoleta">Obsoleta</option>
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
                <th>Categoria</th>
                <th>Estat</th>
                <th>Actualitzat</th>
                <th></th>
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
                  <td style={{ color: 'var(--gray-500)' }}>{f.categoria || '-'}</td>
                  <td><span className={`badge ${f.estat}`}>{f.estat}</span></td>
                  <td style={{ color: 'var(--gray-500)', fontSize: '0.85rem' }}>
                    {f.updated_at ? new Date(f.updated_at).toLocaleDateString('ca') : '-'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <Link to={`/fitxes/${f.id}`} className="outline secondary btn-sm" role="button">
                      Veure
                    </Link>
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
