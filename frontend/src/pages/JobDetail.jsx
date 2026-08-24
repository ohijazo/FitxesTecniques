import { useEffect, useRef, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

const ESTATS_TERMINALS = new Set(['acabat', 'interromput', 'error']);
const REFRESH_MS = 3000;

function EstatBadge({ estat }) {
  return <span className={`job-estat ${estat}`}>{estat}</span>;
}

function ItemEstatBadge({ estat }) {
  const colors = {
    pendent: 'var(--gray-500)',
    processant: 'var(--brand)',
    ok: 'var(--success)',
    error: 'var(--danger)',
    omes: 'var(--gray-400)',
  };
  return (
    <span style={{ color: colors[estat] || 'var(--gray-600)', fontWeight: 600, fontSize: '0.85rem' }}>
      {estat}
    </span>
  );
}

function JobDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [job, setJob] = useState(null);
  const [items, setItems] = useState([]);
  const [filterEstat, setFilterEstat] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reprenent, setReprenent] = useState(false);
  const intervalRef = useRef(null);

  const carregar = async (silenciosos = false) => {
    try {
      const [j, it] = await Promise.all([
        api.detallJob(id),
        api.itemsJob(id, filterEstat ? { estat: filterEstat, per_page: 500 } : { per_page: 500 }),
      ]);
      setJob(j);
      setItems(it.items);
      setError(null);
      if (!silenciosos) setLoading(false);
    } catch (e) {
      setError(e.message);
      if (!silenciosos) setLoading(false);
    }
  };

  useEffect(() => { carregar(); }, [id, filterEstat]);

  // Polling només mentre no terminal
  useEffect(() => {
    if (!job) return;
    if (ESTATS_TERMINALS.has(job.estat)) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(() => carregar(true), REFRESH_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [job?.estat, id, filterEstat]);

  const reprendre = async () => {
    setReprenent(true);
    try {
      const j = await api.reprendreJob(id);
      setJob(j);
      toast.success('Job reprès');
      carregar();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setReprenent(false);
    }
  };

  const arxivar = async () => {
    if (!confirm('Arxivar aquest job? No s\'esborra, només es treu del llistat principal.')) return;
    try {
      await api.arxivarJob(id);
      toast.success('Job arxivat');
      navigate('/jobs');
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (loading) return <p aria-busy="true">Carregant job...</p>;
  if (error) return <p style={{ color: 'var(--danger)' }}>Error: {error}</p>;
  if (!job) return <p>Job no trobat</p>;

  const total = job.total_items || 0;
  const fets = (job.items_ok || 0) + (job.items_error || 0);
  const pct = total > 0 ? Math.round((fets / total) * 100) : 0;
  const fillClass = job.items_error > 0
    ? (job.items_ok > 0 ? 'partial-error' : 'has-error')
    : '';

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ margin: 0 }}>Job #{job.id}</h2>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.88rem', margin: '0.2rem 0 0' }}>
            {job.tipus.replace(/_/g, ' ')} — creat per {job.created_by || '?'} el {new Date(job.created_at).toLocaleString('ca')}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <EstatBadge estat={job.estat} />
          {job.estat === 'interromput' && (
            <button onClick={reprendre} disabled={reprenent}>
              {reprenent ? 'Reprenent...' : 'Reprendre'}
            </button>
          )}
          {ESTATS_TERMINALS.has(job.estat) && !job.arxivat && (
            <button className="outline secondary" onClick={arxivar}>Arxivar</button>
          )}
        </div>
      </div>

      <div style={{ background: 'var(--gray-50)', border: '1px solid var(--gray-200)', borderRadius: 'var(--radius-lg)', padding: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Total</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{total}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Ok</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>{job.items_ok || 0}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Error</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--danger)' }}>{job.items_error || 0}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Pendents</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--gray-700)' }}>{job.items_pendents || 0}</div>
          </div>
        </div>

        <div className="progress-bar" aria-label={`Progrés: ${pct}%`}>
          <div className={`progress-bar-fill ${fillClass}`} style={{ width: `${pct}%` }} />
          <div className="progress-bar-label">{fets} / {total} ({pct}%)</div>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Items</h3>
        <select value={filterEstat} onChange={(e) => setFilterEstat(e.target.value)} style={{ margin: 0, width: '160px' }}>
          <option value="">Tots</option>
          <option value="pendent">Pendents</option>
          <option value="processant">Processant</option>
          <option value="ok">Ok</option>
          <option value="error">Error</option>
          <option value="omes">Omesos</option>
        </select>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Fitxa</th>
              <th>Destí</th>
              <th>Estat</th>
              <th>Intents</th>
              <th>Executat</th>
              <th>Missatge</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: 'var(--gray-500)', padding: '1rem' }}>
                  Sense items {filterEstat ? `en estat "${filterEstat}"` : ''}
                </td>
              </tr>
            ) : items.map((it) => (
              <tr key={it.id}>
                <td>
                  {it.fitxa_id ? (
                    <Link to={`/fitxes/${it.fitxa_id}`}>
                      <code>{it.fitxa_codi}</code>
                    </Link>
                  ) : '-'}
                  {it.fitxa_nom && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)' }}>{it.fitxa_nom}</div>
                  )}
                </td>
                <td>{it.desti_nom || '-'}</td>
                <td><ItemEstatBadge estat={it.estat} /></td>
                <td style={{ textAlign: 'center' }}>{it.intent_count || 0}</td>
                <td style={{ fontSize: '0.82rem', color: 'var(--gray-500)' }}>
                  {it.executat_at ? new Date(it.executat_at).toLocaleString('ca') : '-'}
                </td>
                <td style={{ fontSize: '0.82rem', maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis' }}
                    title={it.missatge_error || ''}>
                  {it.missatge_error || ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default JobDetail;
