import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [incloureArxivats, setIncloureArxivats] = useState(false);

  const carregar = async () => {
    setLoading(true);
    try {
      const data = await api.llistarJobs({
        per_page: 100,
        incloure_arxivats: incloureArxivats ? '1' : '0',
      });
      setJobs(data.jobs);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { carregar(); }, [incloureArxivats]);

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>Jobs massius</h2>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', margin: 0 }}>
          <input
            type="checkbox"
            checked={incloureArxivats}
            onChange={(e) => setIncloureArxivats(e.target.checked)}
            style={{ margin: 0 }}
          />
          Incloure arxivats
        </label>
      </div>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

      {loading ? (
        <p aria-busy="true">Carregant jobs...</p>
      ) : jobs.length === 0 ? (
        <div className="empty-state">
          <p>No hi ha jobs.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Tipus</th>
                <th>Estat</th>
                <th>Progrés</th>
                <th>Creat per</th>
                <th>Creat</th>
                <th>Finalitzat</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => {
                const total = j.total_items || 0;
                const fets = (j.items_ok || 0) + (j.items_error || 0);
                const pct = total > 0 ? Math.round((fets / total) * 100) : 0;
                return (
                  <tr key={j.id} style={j.arxivat ? { opacity: 0.5 } : {}}>
                    <td>#{j.id}</td>
                    <td>{j.tipus.replace(/_/g, ' ')}</td>
                    <td><span className={`job-estat ${j.estat}`}>{j.estat}</span></td>
                    <td style={{ minWidth: '140px' }}>
                      <div style={{ fontSize: '0.85rem' }}>
                        {fets} / {total} ({pct}%)
                        {j.items_error > 0 && <span style={{ color: 'var(--danger)', marginLeft: '0.5rem' }}>· {j.items_error} error</span>}
                      </div>
                    </td>
                    <td>{j.created_by || '-'}</td>
                    <td style={{ fontSize: '0.82rem', color: 'var(--gray-500)' }}>
                      {j.created_at ? new Date(j.created_at).toLocaleString('ca') : '-'}
                    </td>
                    <td style={{ fontSize: '0.82rem', color: 'var(--gray-500)' }}>
                      {j.finished_at ? new Date(j.finished_at).toLocaleString('ca') : '-'}
                    </td>
                    <td>
                      <Link to={`/jobs/${j.id}`} className="outline secondary btn-sm" role="button">Veure</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export default Jobs;
