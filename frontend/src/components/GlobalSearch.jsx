import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useEscapeKey } from './useEscapeKey';

const DEBOUNCE_MS = 250;

function GlobalSearch() {
  const [obert, setObert] = useState(false);
  const [q, setQ] = useState('');
  const [resultats, setResultats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEscapeKey(obert ? () => setObert(false) : null);

  // Hotkey: Ctrl+K / Cmd+K obre el modal
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setObert((v) => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Focus automàtic en obrir
  useEffect(() => {
    if (obert) {
      setTimeout(() => inputRef.current?.focus(), 0);
    } else {
      setQ('');
      setResultats([]);
      setHighlight(0);
    }
  }, [obert]);

  // Cerca debounced
  useEffect(() => {
    if (!obert || !q.trim()) { setResultats([]); return; }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const data = await api.llistarFitxes({ cerca: q, per_page: 10 });
        setResultats(data.fitxes || []);
        setHighlight(0);
      } catch (_) {
        setResultats([]);
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [q, obert]);

  const obrirFitxa = (f) => {
    setObert(false);
    navigate(`/fitxes/${f.id}`);
  };

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, resultats.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === 'Enter' && resultats[highlight]) {
      e.preventDefault();
      obrirFitxa(resultats[highlight]);
    }
  };

  if (!obert) return null;

  return (
    <div className="modal-overlay" onClick={() => setObert(false)} style={{ alignItems: 'flex-start', paddingTop: '8vh' }}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '560px', padding: '0', overflow: 'hidden' }}>
        <input
          ref={inputRef}
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Cercar fitxa per codi o nom..."
          aria-label="Cerca global"
          style={{
            width: '100%', border: 0, padding: '1rem 1.25rem', margin: 0,
            fontSize: '1rem', boxShadow: 'none', borderRadius: 0,
            borderBottom: '1px solid var(--gray-200)',
          }}
        />
        <div style={{ maxHeight: '50vh', overflowY: 'auto' }}>
          {loading ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--gray-500)' }} aria-busy="true">
              Cercant...
            </div>
          ) : q && resultats.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--gray-500)' }}>
              Cap fitxa coincideix amb "{q}"
            </div>
          ) : (
            resultats.map((f, i) => (
              <button
                key={f.id}
                type="button"
                onClick={() => obrirFitxa(f)}
                onMouseEnter={() => setHighlight(i)}
                style={{
                  width: '100%', display: 'block', textAlign: 'left', padding: '0.7rem 1.25rem',
                  background: i === highlight ? 'var(--brand-50)' : '#fff',
                  border: 0, borderRadius: 0, color: 'var(--gray-800)', margin: 0,
                  cursor: 'pointer', borderBottom: '1px solid var(--gray-100)',
                  boxShadow: 'none',
                }}>
                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                  <code style={{ background: 'transparent', padding: 0, color: 'var(--brand)' }}>{f.art_codi}</code>
                  {' — '}
                  {f.nom_producte}
                </div>
                {f.categoria && (
                  <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)' }}>{f.categoria}</div>
                )}
              </button>
            ))
          )}
        </div>
        <div style={{
          padding: '0.5rem 1rem', fontSize: '0.75rem', color: 'var(--gray-500)',
          background: 'var(--gray-50)', borderTop: '1px solid var(--gray-200)',
          display: 'flex', gap: '1rem',
        }}>
          <span><kbd>↑↓</kbd> per navegar</span>
          <span><kbd>Enter</kbd> per obrir</span>
          <span><kbd>Esc</kbd> per tancar</span>
        </div>
      </div>
    </div>
  );
}

export default GlobalSearch;
