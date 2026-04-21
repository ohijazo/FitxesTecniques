import { useState } from 'react';

function DistribuirModal({ titol, missatge, onDistribuir, onNoDistribuir, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, color: 'var(--success)' }}>{titol}</h3>
          <button className="outline secondary btn-sm" onClick={onClose}>&times;</button>
        </div>

        <div style={{ background: 'var(--success-bg)', padding: '0.75rem 1rem', borderRadius: 'var(--radius)', marginBottom: '1.25rem', fontSize: '0.92rem', color: 'var(--success)' }}>
          <strong>{missatge}</strong>
        </div>

        <p style={{ fontSize: '0.92rem', color: 'var(--gray-700)', marginBottom: '1.25rem' }}>
          Vols distribuir-la ara als destins configurats?
        </p>

        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button className="outline secondary" onClick={onNoDistribuir}>
            No, més tard
          </button>
          <button onClick={onDistribuir}>
            Sí, distribuir ara
          </button>
        </div>
      </div>
    </div>
  );
}

export default DistribuirModal;
