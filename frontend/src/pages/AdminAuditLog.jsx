import { useEffect, useState } from 'react';
import { api } from '../api/client';

const ACCIO_COLOR = {
  create: 'var(--success)',
  update: 'var(--brand)',
  delete: 'var(--danger)',
};

function renderJson(obj) {
  if (obj == null) return <em style={{ color: 'var(--gray-400)' }}>—</em>;
  try {
    return (
      <pre style={{
        whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
        fontFamily: 'inherit', fontSize: '0.78rem', color: 'var(--gray-700)',
      }}>{JSON.stringify(obj, null, 2)}</pre>
    );
  } catch (_) {
    return String(obj);
  }
}

function AdminAuditLog() {
  const [entrades, setEntrades] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [entitat, setEntitat] = useState('');
  const [accio, setAccio] = useState('');
  const [usuari, setUsuari] = useState('');
  const [expandits, setExpandits] = useState(() => new Set());

  const carregar = async (p = 1) => {
    setLoading(true);
    try {
      const params = { page: p, per_page: 50 };
      if (entitat) params.entitat = entitat;
      if (accio) params.accio = accio;
      if (usuari) params.usuari = usuari;
      const data = await api.llistarAuditLog(params);
      setEntrades(data.entrades);
      setTotal(data.total);
      setPages(data.pages);
      setPage(data.page);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { carregar(1); }, [entitat, accio, usuari]);

  const toggleExpandit = (id) => {
    setExpandits((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ margin: 0 }}>Audit log</h2>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.88rem', margin: '0.2rem 0 0' }}>
            {total} entrades registrades
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <select value={entitat} onChange={(e) => setEntitat(e.target.value)} style={{ margin: 0, width: 'auto' }}>
          <option value="">Totes les entitats</option>
          <option value="desti">Destins</option>
          <option value="estat">Estats</option>
        </select>
        <select value={accio} onChange={(e) => setAccio(e.target.value)} style={{ margin: 0, width: 'auto' }}>
          <option value="">Totes les accions</option>
          <option value="create">Creació</option>
          <option value="update">Modificació</option>
          <option value="delete">Eliminació</option>
        </select>
        <input
          type="search"
          placeholder="Filtrar per usuari..."
          value={usuari}
          onChange={(e) => setUsuari(e.target.value)}
          style={{ margin: 0, width: '240px' }}
        />
      </div>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {loading ? (
        <p aria-busy="true">Carregant...</p>
      ) : entrades.length === 0 ? (
        <div className="empty-state">
          <p>Cap entrada coincideix amb el filtre.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th style={{ width: '160px' }}>Data</th>
                <th>Usuari</th>
                <th style={{ width: '100px' }}>Acció</th>
                <th style={{ width: '100px' }}>Entitat</th>
                <th style={{ width: '70px' }}>ID</th>
                <th>Canvi</th>
              </tr>
            </thead>
            <tbody>
              {entrades.map((e) => {
                const expandit = expandits.has(e.id);
                return (
                  <tr key={e.id}>
                    <td style={{ fontSize: '0.82rem', color: 'var(--gray-600)', whiteSpace: 'nowrap' }}>
                      {e.at ? new Date(e.at).toLocaleString('ca') : '-'}
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>{e.usuari || '—'}</td>
                    <td>
                      <span style={{
                        background: ACCIO_COLOR[e.accio] || 'var(--gray-400)',
                        color: '#fff', padding: '0.15rem 0.5rem', borderRadius: '3px',
                        fontSize: '0.75rem', fontWeight: 600,
                      }}>{e.accio}</span>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>{e.entitat}</td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>{e.entitat_id || '—'}</td>
                    <td style={{ fontSize: '0.82rem' }}>
                      <button type="button" className="link-button" onClick={() => toggleExpandit(e.id)}>
                        {expandit ? 'amaga detall' : 'veure detall'}
                      </button>
                      {expandit && (
                        <div style={{
                          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem',
                          marginTop: '0.5rem', padding: '0.75rem', background: 'var(--gray-50)',
                          borderRadius: 'var(--radius)',
                        }}>
                          <div>
                            <strong style={{ fontSize: '0.78rem' }}>Abans</strong>
                            {renderJson(e.abans)}
                          </div>
                          <div>
                            <strong style={{ fontSize: '0.78rem' }}>Després</strong>
                            {renderJson(e.despres)}
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', marginTop: '1rem' }}>
          <button className="outline secondary btn-sm" disabled={page <= 1} onClick={() => carregar(page - 1)}>
            ← Anterior
          </button>
          <span style={{ alignSelf: 'center', fontSize: '0.88rem', color: 'var(--gray-600)' }}>
            Pàgina {page} de {pages}
          </span>
          <button className="outline secondary btn-sm" disabled={page >= pages} onClick={() => carregar(page + 1)}>
            Següent →
          </button>
        </div>
      )}
    </>
  );
}

export default AdminAuditLog;
