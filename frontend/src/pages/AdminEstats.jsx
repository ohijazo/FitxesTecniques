import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

const COLOR_PRESETS = [
  { color: '#fef3c7', color_text: '#92400e', nom: 'Groc' },
  { color: '#d1fae5', color_text: '#065f46', nom: 'Verd' },
  { color: '#fee2e2', color_text: '#991b1b', nom: 'Vermell' },
  { color: '#e5e7eb', color_text: '#374151', nom: 'Gris' },
  { color: '#dbeafe', color_text: '#1e40af', nom: 'Blau' },
  { color: '#ede9fe', color_text: '#5b21b6', nom: 'Lila' },
  { color: '#ffedd5', color_text: '#9a3412', nom: 'Taronja' },
];

function AdminEstats() {
  const toast = useToast();
  const [estats, setEstats] = useState([]);
  const [accions, setAccions] = useState([]);
  const [mode, setMode] = useState('llista');
  const [editant, setEditant] = useState(null);
  const [form, setForm] = useState({
    codi: '', nom: '', color: '#e5e7eb', color_text: '#374151',
    accio: 'cap', ordre: 100,
  });
  const [error, setError] = useState(null);

  const carregar = async () => {
    try {
      const [e, a] = await Promise.all([
        api.llistarEstats(),
        api.llistarAccionsEstat(),
      ]);
      setEstats(e);
      setAccions(a);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => { carregar(); }, []);

  const resetForm = () => {
    setForm({ codi: '', nom: '', color: '#e5e7eb', color_text: '#374151', accio: 'cap', ordre: 100 });
    setEditant(null);
    setMode('llista');
    setError(null);
  };

  const editar = (estat) => {
    setForm({
      codi: estat.codi,
      nom: estat.nom,
      color: estat.color,
      color_text: estat.color_text,
      accio: estat.accio,
      ordre: estat.ordre,
    });
    setEditant(estat);
    setMode('form');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      if (editant) {
        const payload = {
          nom: form.nom,
          color: form.color,
          color_text: form.color_text,
          accio: form.accio,
          ordre: form.ordre,
        };
        // Només permetem canviar codi si NO és protegit
        if (!editant.protegit && form.codi !== editant.codi) {
          payload.codi = form.codi;
        }
        await api.editarEstat(editant.id, payload);
        toast.success('Estat actualitzat');
      } else {
        await api.crearEstat(form);
        toast.success('Estat creat');
      }
      resetForm();
      carregar();
    } catch (err) {
      setError(err.message);
    }
  };

  const eliminar = async (estat) => {
    if (!confirm(`Eliminar l'estat "${estat.nom}"?`)) return;
    try {
      await api.eliminarEstat(estat.id);
      toast.success('Estat eliminat');
      carregar();
    } catch (err) {
      toast.error(`Error: ${err.message}`);
    }
  };

  const aplicarPreset = (preset) => {
    setForm((prev) => ({ ...prev, color: preset.color, color_text: preset.color_text }));
  };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0 }}>Estats de fitxa</h2>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.88rem', margin: '0.2rem 0 0' }}>
            Gestiona els estats que pot tenir una fitxa i les accions associades.
          </p>
        </div>
        {mode === 'llista' && (
          <button onClick={() => setMode('form')}>+ Nou estat</button>
        )}
      </div>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

      {mode === 'llista' ? (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Ordre</th>
                <th>Codi</th>
                <th>Nom</th>
                <th>Color (preview)</th>
                <th>Acció en canviar a aquest estat</th>
                <th>Protegit</th>
                <th style={{ textAlign: 'right' }}>Accions</th>
              </tr>
            </thead>
            <tbody>
              {estats.map((e) => {
                const accio = accions.find((a) => a.codi === e.accio);
                return (
                  <tr key={e.id}>
                    <td>{e.ordre}</td>
                    <td><code>{e.codi}</code></td>
                    <td>{e.nom}</td>
                    <td>
                      <span className="badge" style={{ background: e.color, color: e.color_text }}>
                        {e.codi}
                      </span>
                    </td>
                    <td title={accio?.descripcio}>{accio?.nom || e.accio}</td>
                    <td>{e.protegit ? 'Sí' : '—'}</td>
                    <td>
                      <div className="quick-actions">
                        <button className="outline secondary btn-sm" onClick={() => editar(e)}>Editar</button>
                        {!e.protegit && (
                          <button
                            className="outline btn-sm"
                            style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}
                            onClick={() => eliminar(e)}>
                            Eliminar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="card">
          <h3 style={{ marginTop: 0 }}>{editant ? `Editar estat "${editant.codi}"` : 'Nou estat'}</h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <label>
              Codi *
              <input
                value={form.codi}
                onChange={(e) => setForm({ ...form, codi: e.target.value })}
                required
                disabled={editant?.protegit}
                placeholder="Ex: en_revisio_externa"
                pattern="[a-z][a-z0-9_]*"
                title="Lletres minúscules, números i guió baix. Ha de començar per lletra."
              />
              {editant?.protegit && (
                <small style={{ color: 'var(--gray-500)' }}>El codi dels estats protegits no es pot canviar.</small>
              )}
            </label>
            <label>
              Nom visible *
              <input
                value={form.nom}
                onChange={(e) => setForm({ ...form, nom: e.target.value })}
                required
                placeholder="Ex: En revisió externa"
              />
            </label>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <label>
              Color de fons
              <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            </label>
            <label>
              Color del text
              <input type="color" value={form.color_text} onChange={(e) => setForm({ ...form, color_text: e.target.value })} />
            </label>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <p style={{ fontSize: '0.85rem', color: 'var(--gray-600)', marginBottom: '0.3rem' }}>Presets ràpids:</p>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {COLOR_PRESETS.map((p) => (
                <button
                  type="button"
                  key={p.nom}
                  className="badge"
                  style={{ background: p.color, color: p.color_text, cursor: 'pointer', border: 'none' }}
                  onClick={() => aplicarPreset(p)}>
                  {p.nom}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <p style={{ fontSize: '0.85rem', color: 'var(--gray-600)', marginBottom: '0.3rem' }}>Preview:</p>
            <span className="badge" style={{ background: form.color, color: form.color_text }}>
              {form.nom || form.codi || 'estat'}
            </span>
          </div>

          <label>
            Acció en canviar a aquest estat
            <select value={form.accio} onChange={(e) => setForm({ ...form, accio: e.target.value })}>
              {accions.map((a) => (
                <option key={a.codi} value={a.codi}>{a.nom}</option>
              ))}
            </select>
            <small style={{ color: 'var(--gray-500)' }}>
              {accions.find((a) => a.codi === form.accio)?.descripcio}
            </small>
          </label>

          <label>
            Ordre (per al llistat)
            <input
              type="number"
              value={form.ordre}
              onChange={(e) => setForm({ ...form, ordre: parseInt(e.target.value) || 0 })}
            />
          </label>

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
            <button type="button" className="outline secondary" onClick={resetForm}>Cancel·lar</button>
            <button type="submit">{editant ? 'Guardar canvis' : 'Crear estat'}</button>
          </div>
        </form>
      )}
    </>
  );
}

export default AdminEstats;
