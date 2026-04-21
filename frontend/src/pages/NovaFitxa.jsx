import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import FitxaForm from '../components/FitxaForm';

function NovaFitxa() {
  const navigate = useNavigate();
  const [mode, setMode] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [wordResult, setWordResult] = useState(null);

  const handleWordUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('token');
      const res = await fetch('/api/fitxes/upload-word', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error);
        return;
      }

      if (data.existent) {
        if (confirm(data.message)) {
          navigate(`/fitxes/${data.fitxa.id}/editar`, {
            state: { dadesWord: data.dades_extretes },
          });
        }
      } else {
        setWordResult(data);
        setMode('manual');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleCrear = async (formData) => {
    try {
      const fitxa = await api.crearFitxa({
        art_codi: formData.art_codi,
        nom_producte: formData.nom_producte,
        categoria: formData.categoria,
        descripcio_canvi: formData.descripcio_canvi || 'Creació inicial',
        contingut: formData.contingut,
      });

      if (confirm('Fitxa creada correctament. Vols distribuir-la ara?')) {
        navigate(`/fitxes/${fitxa.id}`, { state: { openDistribuir: true } });
      } else {
        navigate(`/fitxes/${fitxa.id}`);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  // Pantalla triar mode
  if (!mode) {
    return (
      <>
        <h2>Nova fitxa tècnica</h2>
        {error && <p style={{ color: '#dc3545' }}>{error}</p>}

        <div className="option-cards">
          <label className="option-card" htmlFor="word-upload">
            <h3>Pujar Word</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Puja un .docx existent i les dades s'extrauran automàticament.
            </p>
            <input
              id="word-upload"
              type="file"
              accept=".docx"
              onChange={handleWordUpload}
              disabled={uploading}
              style={{ display: 'none' }}
            />
            {uploading ? (
              <p aria-busy="true" style={{ fontSize: '0.85rem' }}>Processant...</p>
            ) : (
              <span style={{ color: 'var(--brand)' }}>Seleccionar fitxer</span>
            )}
          </label>

          <div className="option-card" onClick={() => setMode('manual')}>
            <h3>Crear manualment</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Crea una fitxa nova omplint el formulari pas a pas.
            </p>
            <span style={{ color: 'var(--brand)' }}>Començar</span>
          </div>
        </div>
      </>
    );
  }

  const initialData = wordResult
    ? {
        art_codi: wordResult.art_codi || '',
        nom_producte: wordResult.nom_producte || '',
        categoria: '',
        descripcio_canvi: 'Creació inicial',
        contingut: wordResult.dades_extretes || {},
      }
    : {
        art_codi: '',
        nom_producte: '',
        categoria: '',
        descripcio_canvi: 'Creació inicial',
        contingut: {},
      };

  return (
    <>
      <div className="toolbar">
        <button className="outline secondary btn-sm" onClick={() => { setMode(null); setWordResult(null); }}>
          ← Tornar
        </button>
        <h2 style={{ margin: 0 }}>Nova fitxa tècnica</h2>
      </div>
      {error && <p style={{ color: '#dc3545' }}>{error}</p>}
      {wordResult && <p style={{ color: '#28a745' }}>Dades extretes del Word correctament.</p>}

      <FitxaForm initialData={initialData} onSubmit={handleCrear} isNew={true} />
    </>
  );
}

export default NovaFitxa;
