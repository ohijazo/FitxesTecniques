import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';

const TIPUS_CAMP = ['text', 'textarea', 'number', 'date', 'select', 'taula'];

function AdminSeccions() {
  const { tipusId } = useParams();
  const [tipusInfo, setTipusInfo] = useState(null);
  const [seccions, setSeccions] = useState([]);
  const [novaSeccio, setNovaSeccio] = useState('');
  const [editantCamp, setEditantCamp] = useState(null);
  const [campForm, setCampForm] = useState({ nom: '', label: '', tipus: 'text', obligatori: false, valor_defecte: '' });
  const [seccioActiva, setSeccioActiva] = useState(null);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  const carregarSeccions = async () => {
    try {
      if (tipusId) {
        const tipus = await api.detallTipus(tipusId);
        setTipusInfo(tipus);
        setSeccions(tipus.seccions || []);
      } else {
        const data = await api.llistarSeccions();
        setSeccions(data);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => { carregarSeccions(); }, [tipusId]);

  const crearSeccio = async () => {
    if (!novaSeccio.trim()) return;
    try {
      await api.crearSeccio({ titol: novaSeccio, tipus_id: tipusId ? parseInt(tipusId) : null });
      setNovaSeccio('');
      setMsg('Secció creada');
      carregarSeccions();
    } catch (err) { setError(err.message); }
  };

  const eliminarSeccio = async (id) => {
    if (!confirm('Segur que vols eliminar aquesta secció i tots els seus camps?')) return;
    try {
      await api.eliminarSeccio(id);
      setMsg('Secció eliminada');
      if (seccioActiva === id) setSeccioActiva(null);
      carregarSeccions();
    } catch (err) { setError(err.message); }
  };

  const resetCampForm = () => {
    setCampForm({ nom: '', label: '', tipus: 'text', obligatori: false, valor_defecte: '' });
    setEditantCamp(null);
  };

  const guardarCamp = async () => {
    if (!campForm.nom || !campForm.label) {
      setError('Nom i etiqueta són obligatoris');
      return;
    }
    try {
      if (editantCamp) {
        await api.editarCamp(editantCamp, campForm);
        setMsg('Camp actualitzat');
      } else {
        await api.crearCamp(seccioActiva, campForm);
        setMsg('Camp creat');
      }
      resetCampForm();
      carregarSeccions();
    } catch (err) { setError(err.message); }
  };

  const editarCamp = (camp) => {
    setEditantCamp(camp.id);
    setCampForm({
      nom: camp.nom,
      label: camp.label,
      tipus: camp.tipus,
      obligatori: camp.obligatori,
      valor_defecte: camp.valor_defecte || '',
    });
  };

  const eliminarCamp = async (id) => {
    if (!confirm('Segur que vols eliminar aquest camp?')) return;
    try {
      await api.eliminarCamp(id);
      setMsg('Camp eliminat');
      carregarSeccions();
    } catch (err) { setError(err.message); }
  };

  const seccioSeleccionada = seccions.find((s) => s.id === seccioActiva);

  return (
    <>
      <h2>Gestió de seccions i camps</h2>
      <p style={{ color: 'var(--text-muted)' }}>Defineix les seccions i camps que apareixeran al formulari de la fitxa tècnica.</p>

      {error && <p style={{ color: '#dc3545' }}>{error}</p>}
      {msg && <p style={{ color: '#28a745' }}>{msg}</p>}

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '1.5rem', alignItems: 'start' }}>
        {/* Barra lateral de seccions */}
        <div>
          <div className="card">
            <div className="card-header">Seccions</div>
            <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '0.5rem' }}>
              <input
                placeholder="Nova secció..."
                value={novaSeccio}
                onChange={(e) => setNovaSeccio(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && crearSeccio()}
                style={{ margin: 0 }}
              />
              <button className="btn-sm" onClick={crearSeccio} style={{ whiteSpace: 'nowrap' }}>+</button>
            </div>
            {seccions.map((s) => (
              <div
                key={s.id}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '6px 8px', cursor: 'pointer', borderRadius: '4px',
                  background: seccioActiva === s.id ? 'var(--brand-light)' : 'transparent',
                }}
                onClick={() => { setSeccioActiva(s.id); resetCampForm(); setError(null); setMsg(null); }}
              >
                <span style={{ fontWeight: seccioActiva === s.id ? 600 : 400, fontSize: '0.9rem' }}>
                  {s.titol} <small style={{ color: 'var(--text-muted)' }}>({(s.camps || []).length})</small>
                </span>
                <button className="btn-remove" onClick={(e) => { e.stopPropagation(); eliminarSeccio(s.id); }}>×</button>
              </div>
            ))}
          </div>
        </div>

        {/* Contingut: camps de la secció seleccionada */}
        <div>
          {!seccioActiva ? (
            <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem' }}>
              Selecciona una secció per veure i editar els seus camps.
            </div>
          ) : (
            <>
              <div className="card">
                <div className="card-header">
                  Camps de: {seccioSeleccionada?.titol}
                </div>

                {(seccioSeleccionada?.camps || []).length === 0 ? (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Aquesta secció no té camps.</p>
                ) : (
                  <table style={{ fontSize: '0.85rem' }}>
                    <thead>
                      <tr><th>Nom</th><th>Etiqueta</th><th>Tipus</th><th>Oblig.</th><th></th></tr>
                    </thead>
                    <tbody>
                      {(seccioSeleccionada?.camps || []).map((camp) => (
                        <tr key={camp.id}>
                          <td><code>{camp.nom}</code></td>
                          <td>{camp.label}</td>
                          <td><span className="badge esborrany">{camp.tipus}</span></td>
                          <td>{camp.obligatori ? 'Sí' : '-'}</td>
                          <td>
                            <div style={{ display: 'flex', gap: '0.25rem' }}>
                              <button className="outline secondary btn-sm" onClick={() => editarCamp(camp)}>Editar</button>
                              <button className="btn-remove" onClick={() => eliminarCamp(camp.id)}>×</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Formulari afegir/editar camp */}
              <div className="card">
                <div className="card-header">{editantCamp ? 'Editar camp' : 'Afegir camp'}</div>
                <div className="grid">
                  <label>
                    Nom intern *
                    <input value={campForm.nom} onChange={(e) => setCampForm({ ...campForm, nom: e.target.value })}
                      placeholder="Ex: proteina" />
                  </label>
                  <label>
                    Etiqueta *
                    <input value={campForm.label} onChange={(e) => setCampForm({ ...campForm, label: e.target.value })}
                      placeholder="Ex: Proteïna" />
                  </label>
                </div>
                <div className="grid">
                  <label>
                    Tipus
                    <select value={campForm.tipus} onChange={(e) => setCampForm({ ...campForm, tipus: e.target.value })}>
                      {TIPUS_CAMP.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </label>
                  <label>
                    <input type="checkbox" checked={campForm.obligatori}
                      onChange={(e) => setCampForm({ ...campForm, obligatori: e.target.checked })} role="switch" />
                    Obligatori
                  </label>
                </div>
                <label>
                  Valor per defecte
                  <textarea rows={2} value={campForm.valor_defecte}
                    onChange={(e) => setCampForm({ ...campForm, valor_defecte: e.target.value })} />
                </label>
                <div className="toolbar">
                  <button type="button" onClick={guardarCamp}>
                    {editantCamp ? 'Actualitzar' : 'Afegir camp'}
                  </button>
                  {editantCamp && (
                    <button type="button" className="secondary outline" onClick={resetCampForm}>Cancel·lar</button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default AdminSeccions;
