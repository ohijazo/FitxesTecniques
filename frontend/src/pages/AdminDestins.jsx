import { useState, useEffect } from 'react';
import { api } from '../api/client';

const CONFIG_FIELDS = {
  ftp: [
    { nom: 'host', label: 'Host', type: 'text', placeholder: 'ftp.grupagrienergia.com' },
    { nom: 'port', label: 'Port', type: 'number', placeholder: '21' },
    { nom: 'user', label: 'Usuari', type: 'text', placeholder: 'gpablos@farineracoromina.com' },
    { nom: 'password', label: 'Contrasenya', type: 'password' },
    { nom: 'path', label: 'Ruta destí', type: 'text', placeholder: '/ (arrel)' },
    { nom: 'tls', label: 'Usar TLS (FTPS)', type: 'checkbox' },
  ],
  xarxa: [
    { nom: 'ruta_base', label: 'Ruta carpeta de xarxa', type: 'text', placeholder: '\\\\servidor\\compartit\\fitxes' },
  ],
  sap: [
    { nom: 'endpoint', label: 'Endpoint Service Layer', type: 'text' },
    { nom: 'user', label: 'Usuari SAP', type: 'text' },
    { nom: 'password', label: 'Contrasenya SAP', type: 'password' },
  ],
};

function AdminDestins() {
  const [destins, setDestins] = useState([]);
  const [mode, setMode] = useState('llista'); // 'llista' | 'form'
  const [editant, setEditant] = useState(null);
  const [form, setForm] = useState({
    nom: '', tipus: 'ftp', configuracio: {},
    patro_nom_fitxer: '{art_codi}.pdf', actiu: true,
  });
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  const carregarDestins = async () => {
    try {
      const data = await api.llistarDestins();
      setDestins(data);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => { carregarDestins(); }, []);

  const resetForm = () => {
    setForm({ nom: '', tipus: 'ftp', configuracio: {}, patro_nom_fitxer: '{art_codi}.pdf', actiu: true });
    setEditant(null);
    setMode('llista');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setMsg(null);
    try {
      if (editant) {
        await api.editarDesti(editant, form);
        setMsg('Destí actualitzat correctament');
      } else {
        await api.crearDesti(form);
        setMsg('Destí creat correctament');
      }
      resetForm();
      carregarDestins();
    } catch (err) {
      setError(err.message);
    }
  };

  const editar = (d) => {
    setEditant(d.id);
    setForm({
      nom: d.nom,
      tipus: d.tipus,
      configuracio: d.configuracio || {},
      patro_nom_fitxer: d.patro_nom_fitxer,
      actiu: d.actiu,
    });
    setMode('form');
  };

  const eliminar = async (d) => {
    if (!confirm(`Segur que vols eliminar el destí "${d.nom}"?`)) return;
    try {
      await api.eliminarDesti(d.id);
      setMsg('Destí eliminat');
      carregarDestins();
    } catch (err) {
      setError(err.message);
    }
  };

  const updateConfig = (camp, valor) => {
    setForm({ ...form, configuracio: { ...form.configuracio, [camp]: valor } });
  };

  // Vista llista
  if (mode === 'llista') {
    return (
      <>
        <div className="toolbar">
          <h2 style={{ margin: 0 }}>Destins de distribució</h2>
          <button onClick={() => setMode('form')} style={{ marginLeft: 'auto' }}>+ Nou destí</button>
        </div>

        {error && <p style={{ color: '#dc3545' }}>{error}</p>}
        {msg && <p style={{ color: '#28a745' }}>{msg}</p>}

        {destins.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem' }}>
            No hi ha destins configurats. Crea'n un per començar a distribuir fitxes.
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {destins.map((d) => (
              <div key={d.id} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong style={{ fontSize: '1.05rem' }}>{d.nom}</strong>
                    <span className={`badge ${d.actiu ? 'ok' : 'error'}`} style={{ marginLeft: '0.5rem' }}>
                      {d.actiu ? 'Actiu' : 'Inactiu'}
                    </span>
                  </div>
                  <div className="toolbar" style={{ margin: 0 }}>
                    <button className="outline secondary btn-sm" onClick={() => editar(d)}>Editar</button>
                    <button className="outline btn-sm" style={{ color: '#dc3545', borderColor: '#dc3545' }} onClick={() => eliminar(d)}>Eliminar</button>
                  </div>
                </div>
                <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  <span><strong>Tipus:</strong> {d.tipus.toUpperCase()}</span>
                  <span style={{ marginLeft: '1.5rem' }}><strong>Patró fitxer:</strong> <code>{d.patro_nom_fitxer}</code></span>
                  {d.configuracio?.host && (
                    <span style={{ marginLeft: '1.5rem' }}><strong>Host:</strong> {d.configuracio.host}</span>
                  )}
                  {d.configuracio?.ruta_base && (
                    <span style={{ marginLeft: '1.5rem' }}><strong>Ruta:</strong> {d.configuracio.ruta_base}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </>
    );
  }

  // Vista formulari
  return (
    <>
      <div className="toolbar">
        <button className="outline secondary btn-sm" onClick={resetForm}>← Tornar</button>
        <h2 style={{ margin: 0 }}>{editant ? 'Editar destí' : 'Nou destí'}</h2>
      </div>

      {error && <p style={{ color: '#dc3545' }}>{error}</p>}

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="grid">
            <label>
              Nom del destí *
              <input value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })}
                required placeholder="Ex: FTP Producció" />
            </label>
            <label>
              Tipus *
              <select value={form.tipus} onChange={(e) => setForm({ ...form, tipus: e.target.value, configuracio: {} })}>
                <option value="ftp">FTP</option>
                <option value="xarxa">Carpeta de xarxa</option>
                <option value="sap">SAP Business One</option>
              </select>
            </label>
          </div>

          <label>
            Patró nom del fitxer
            <input value={form.patro_nom_fitxer}
              onChange={(e) => setForm({ ...form, patro_nom_fitxer: e.target.value })}
              placeholder="{art_codi}.pdf" />
            <small style={{ color: 'var(--text-muted)' }}>
              Variables disponibles: {'{art_codi}'}, {'{nom_producte}'}, {'{versio}'}, {'{data}'}
            </small>
          </label>

          <fieldset>
            <legend>Configuració {form.tipus.toUpperCase()}</legend>
            {(CONFIG_FIELDS[form.tipus] || []).map((camp) => (
              camp.type === 'checkbox' ? (
                <label key={camp.nom} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="checkbox"
                    checked={form.configuracio[camp.nom] !== false}
                    onChange={(e) => updateConfig(camp.nom, e.target.checked)}
                    role="switch"
                    style={{ width: 'auto', margin: 0 }}
                  />
                  {camp.label}
                </label>
              ) : (
                <label key={camp.nom}>
                  {camp.label}
                  <input
                    type={camp.type}
                    value={form.configuracio[camp.nom] || ''}
                    onChange={(e) => updateConfig(camp.nom, e.target.value)}
                    placeholder={camp.placeholder || ''}
                  />
                </label>
              )
            ))}
          </fieldset>

          <label>
            <input type="checkbox" checked={form.actiu}
              onChange={(e) => setForm({ ...form, actiu: e.target.checked })} role="switch" />
            Destí actiu
          </label>

          <div className="toolbar">
            <button type="submit">{editant ? 'Actualitzar destí' : 'Crear destí'}</button>
            <button type="button" className="secondary outline" onClick={resetForm}>Cancel·lar</button>
          </div>
        </form>
      </div>
    </>
  );
}

export default AdminDestins;
