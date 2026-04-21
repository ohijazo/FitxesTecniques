import { useState, useEffect } from 'react';
import { api } from '../api/client';

function AdminEliminacions() {
  const [registres, setRegistres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const carregar = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/fitxes/eliminacions', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Error carregant registres');
        const data = await res.json();
        setRegistres(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    carregar();
  }, []);

  if (loading) return <p aria-busy="true">Carregant registres d'eliminació...</p>;
  if (error) return <p style={{ color: 'var(--danger)' }}>{error}</p>;

  return (
    <>
      <h2 style={{ marginBottom: '1.25rem' }}>Registre d'eliminacions</h2>

      {registres.length === 0 ? (
        <div className="empty-state">
          <p>No s'ha eliminat cap fitxa.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Codi</th>
                <th>Producte</th>
                <th>Versions</th>
                <th>Motiu</th>
                <th>FTP</th>
                <th>Eliminat per</th>
                <th>Data</th>
              </tr>
            </thead>
            <tbody>
              {registres.map((r) => (
                <tr key={r.id}>
                  <td><code style={{ fontWeight: 600 }}>{r.art_codi}</code></td>
                  <td>{r.nom_producte}</td>
                  <td style={{ textAlign: 'center' }}>{r.num_versions} (rev. {r.ultima_versio})</td>
                  <td style={{ maxWidth: '250px', whiteSpace: 'normal', fontSize: '0.85rem' }}>{r.motiu}</td>
                  <td style={{ textAlign: 'center' }}>
                    {r.esborrat_ftp ? (
                      <span className="badge ok">Esborrat</span>
                    ) : (
                      <span className="badge" style={{ background: 'var(--gray-100)', color: 'var(--gray-500)' }}>No</span>
                    )}
                  </td>
                  <td style={{ fontSize: '0.85rem' }}>{r.eliminat_per}</td>
                  <td style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                    {r.eliminat_at ? new Date(r.eliminat_at).toLocaleString('ca') : '-'}
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

export default AdminEliminacions;
