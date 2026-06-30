import { useState } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import { useEscapeKey } from './useEscapeKey';

function RetirarDestiModal({ fitxaId, fitxaArtCodi, desti, onDone, onClose }) {
  useEscapeKey(onClose);
  const [motiu, setMotiu] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const toast = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!motiu.trim()) { setError('Cal indicar un motiu'); return; }
    if (!password) { setError('Cal la contrasenya'); return; }

    setLoading(true);
    setError(null);
    try {
      const res = await api.retirarDesti(fitxaId, desti.id, { motiu, password });
      toast.success(res.missatge || `Retirat de ${desti.nom}`);
      onDone();
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, color: 'var(--danger)' }}>Retirar de {desti.nom}</h3>
          <button className="outline secondary btn-sm" onClick={onClose}>&times;</button>
        </div>

        <div style={{ background: 'var(--danger-bg)', padding: '0.75rem 1rem', borderRadius: 'var(--radius)', marginBottom: '1rem', fontSize: '0.88rem' }}>
          S'esborrarà el PDF de la fitxa <strong>{fitxaArtCodi}</strong> del destí <strong>{desti.nom}</strong> ({desti.tipus.toUpperCase()}).
          La fitxa i la versió activa es mantenen intactes — només es retira d'aquest destí.
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            Motiu *
            <textarea value={motiu} onChange={(e) => setMotiu(e.target.value)}
              required placeholder="Ex: Distribuït per error a aquest destí, ja no es necessita aquí..."
              rows={2} />
          </label>

          <label>
            Confirma amb la teva contrasenya *
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              required placeholder="Contrasenya" autoComplete="current-password" />
          </label>

          {error && <p style={{ color: 'var(--danger)', fontSize: '0.88rem', marginBottom: '0.5rem' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="outline secondary" onClick={onClose}>Cancel·lar</button>
            <button type="submit" disabled={loading} aria-busy={loading}
              style={{ background: 'var(--danger)', borderColor: 'var(--danger)' }}>
              {loading ? 'Retirant...' : 'Retirar definitivament'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RetirarDestiModal;
