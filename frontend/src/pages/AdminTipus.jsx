import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

function AdminTipus() {
  const [tipusList, setTipusList] = useState([]);
  const [mode, setMode] = useState('llista');
  const [form, setForm] = useState({ nom: '', descripcio: '' });
  const [editant, setEditant] = useState(null);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  const carregar = async () => {
    try {
      const data = await api.llistarTipus();
      setTipusList(data);
    } catch (err) { setError(err.message); }
  };

  useEffect(() => { carregar(); }, []);

  const resetForm = () => {
    setForm({ nom: '', descripcio: '' });
    setEditant(null);
    setMode('llista');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      if (editant) {
        await api.editarTipus(editant, form);
        setMsg('Tipus actualitzat');
      } else {
        await api.crearTipus(form);
        setMsg('Tipus creat');
      }
      resetForm();
      carregar();
    } catch (err) { setError(err.message); }
  };

  const duplicar = async (t) => {
    const nom = prompt('Nom del nou tipus:', `${t.nom} (còpia)`);
    if (!nom) return;
    try {
      await api.duplicarTipus(t.id, { nom });
      setMsg(`Tipus "${nom}" creat a partir de "${t.nom}"`);
      carregar();
    } catch (err) { setError(err.message); }
  };

  const eliminar = async (t) => {
    if (!confirm(`Segur que vols eliminar "${t.nom}"? Les seccions i camps associats també s'eliminaran.`)) return;
    try {
      await api.eliminarTipus(t.id);
      setMsg('Tipus eliminat');
      carregar();
    } catch (err) { setError(err.message); }
  };

  const editar = (t) => {
    setEditant(t.id);
    setForm({ nom: t.nom, descripcio: t.descripcio || '' });
    setMode('form');
  };

  if (mode === 'form') {
    return (
      <>
        <div className="toolbar">
          <button className="outline secondary btn-sm" onClick={resetForm}>← Tornar</button>
          <h2 style={{ margin: 0 }}>{editant ? 'Editar tipus' : 'Nou tipus de fitxa'}</h2>
        </div>
        {error && <p style={{ color: '#dc3545' }}>{error}</p>}
        <div className="card">
          <form onSubmit={handleSubmit}>
            <label>
              Nom del tipus *
              <input value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })}
                required placeholder="Ex: Farina de sègol" />
            </label>
            <label>
              Descripció
              <textarea rows={2} value={form.descripcio}
                onChange={(e) => setForm({ ...form, descripcio: e.target.value })}
                placeholder="Descripció opcional del tipus de fitxa" />
            </label>
            <div className="toolbar">
              <button type="submit">{editant ? 'Actualitzar' : 'Crear tipus'}</button>
              <button type="button" className="secondary outline" onClick={resetForm}>Cancel·lar</button>
            </div>
          </form>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="toolbar">
        <h2 style={{ margin: 0 }}>Tipus de fitxa tècnica</h2>
        <button onClick={() => setMode('form')} style={{ marginLeft: 'auto' }}>+ Nou tipus</button>
      </div>

      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
        Cada tipus defineix les seccions i camps que tindrà la fitxa tècnica. Pots duplicar l'estàndard per crear variacions.
      </p>

      {error && <p style={{ color: '#dc3545' }}>{error}</p>}
      {msg && <p style={{ color: '#28a745' }}>{msg}</p>}

      {tipusList.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem' }}>
          No hi ha tipus definits.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {tipusList.map((t) => (
            <div key={t.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong style={{ fontSize: '1.05rem' }}>{t.nom}</strong>
                  <span className={`badge ${t.actiu ? 'ok' : 'error'}`} style={{ marginLeft: '0.5rem' }}>
                    {t.actiu ? 'Actiu' : 'Inactiu'}
                  </span>
                  <span style={{ marginLeft: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    {t.num_seccions} seccions · slug: <code>{t.slug}</code>
                  </span>
                </div>
                <div className="toolbar" style={{ margin: 0 }}>
                  <Link to={`/admin/tipus/${t.id}/seccions`} className="outline btn-sm" role="button">
                    Seccions i camps
                  </Link>
                  <button className="outline btn-sm" onClick={() => duplicar(t)}>Duplicar</button>
                  <button className="outline secondary btn-sm" onClick={() => editar(t)}>Editar</button>
                  <button className="outline btn-sm" style={{ color: '#dc3545', borderColor: '#dc3545' }}
                    onClick={() => eliminar(t)}>Eliminar</button>
                </div>
              </div>
              {t.descripcio && (
                <p style={{ margin: '0.5rem 0 0', fontSize: '0.88rem', color: 'var(--text-muted)' }}>{t.descripcio}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default AdminTipus;
