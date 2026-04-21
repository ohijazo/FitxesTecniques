import { useState, useEffect } from 'react';
import { api } from '../api/client';

function AdminUsuaris() {
  const [usuaris, setUsuaris] = useState([]);
  const [form, setForm] = useState({ email: '', nom: '', password: '', rol: 'visualitzador' });
  const [editant, setEditant] = useState(null);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  const carregarUsuaris = async () => {
    try {
      const data = await api.llistarUsuaris();
      setUsuaris(data);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => { carregarUsuaris(); }, []);

  const resetForm = () => {
    setForm({ email: '', nom: '', password: '', rol: 'visualitzador' });
    setEditant(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setMsg(null);
    try {
      if (editant) {
        const data = { email: form.email, nom: form.nom, rol: form.rol };
        if (form.password) data.password = form.password;
        await api.editarUsuari(editant, data);
        setMsg('Usuari actualitzat');
      } else {
        await api.crearUsuari(form);
        setMsg('Usuari creat');
      }
      resetForm();
      carregarUsuaris();
    } catch (err) {
      setError(err.message);
    }
  };

  const editar = (u) => {
    setEditant(u.id);
    setForm({ email: u.email, nom: u.nom, password: '', rol: u.rol });
  };

  const eliminar = async (u) => {
    if (!confirm(`Segur que vols eliminar l'usuari ${u.nom}?`)) return;
    try {
      await api.eliminarUsuari(u.id);
      setMsg('Usuari eliminat');
      carregarUsuaris();
    } catch (err) {
      setError(err.message);
    }
  };

  const toggleActiu = async (u) => {
    try {
      await api.editarUsuari(u.id, { actiu: !u.actiu });
      carregarUsuaris();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <h2>Gestió d'usuaris</h2>

      {error && <p style={{ color: '#dc3545' }}>{error}</p>}
      {msg && <p style={{ color: '#28a745' }}>{msg}</p>}

      <div className="card">
        <div className="card-header">{editant ? "Editar usuari" : "Nou usuari"}</div>
        <form onSubmit={handleSubmit}>
          <div className="grid">
            <label>
              Correu electrònic *
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </label>
            <label>
              Nom *
              <input value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} required />
            </label>
          </div>
          <div className="grid">
            <label>
              Contrasenya {editant ? '(deixar buit per no canviar)' : '*'}
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required={!editant} />
            </label>
            <label>
              Rol *
              <select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}>
                <option value="admin">Administrador</option>
                <option value="editor">Editor</option>
                <option value="visualitzador">Visualitzador</option>
              </select>
            </label>
          </div>
          <div className="toolbar">
            <button type="submit">{editant ? 'Actualitzar' : 'Crear usuari'}</button>
            {editant && <button type="button" className="secondary outline" onClick={resetForm}>Cancel·lar</button>}
          </div>
        </form>
      </div>

      <table>
        <thead>
          <tr>
            <th>Nom</th>
            <th>Correu electrònic</th>
            <th>Rol</th>
            <th>Actiu</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {usuaris.map((u) => (
            <tr key={u.id}>
              <td>{u.nom}</td>
              <td>{u.email}</td>
              <td><span className="badge esborrany">{u.rol}</span></td>
              <td>
                <input type="checkbox" checked={u.actiu} onChange={() => toggleActiu(u)} role="switch" />
              </td>
              <td>
                <div style={{ display: 'flex', gap: '0.25rem' }}>
                  <button className="outline secondary btn-sm" onClick={() => editar(u)}>Editar</button>
                  <button className="outline btn-sm" style={{ color: '#dc3545', borderColor: '#dc3545' }} onClick={() => eliminar(u)}>Eliminar</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export default AdminUsuaris;
