import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import FitxaForm from '../components/FitxaForm';
import DistribuirModal from '../components/DistribuirModal';

function NovaFitxa() {
  const navigate = useNavigate();
  const toast = useToast();
  const [mode, setMode] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [wordResult, setWordResult] = useState(null);
  const [novaFitxaId, setNovaFitxaId] = useState(null);
  const [novaFitxaCodi, setNovaFitxaCodi] = useState('');

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
            state: { dadesWord: {
              ...data.dades_extretes,
              rev: data.rev || '',
              data_revisio: data.data_revisio || '',
              data_comprovacio: data.data_comprovacio || '',
            }},
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

      toast.success('Fitxa creada correctament');
      setNovaFitxaId(fitxa.id);
      setNovaFitxaCodi(fitxa.art_codi);
    } catch (err) {
      setError(err.message);
      toast.error(`Error creant: ${err.message}`);
    }
  };

  // Pantalla triar mode
  if (!mode) {
    return (
      <>
        <h2>Nova fitxa tècnica</h2>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        <div className="option-cards">
          <label className="option-card" htmlFor="word-upload">
            <h3>Pujar Word</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Puja un .docx existent i les dades s'extrauran automaticament.
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
        contingut: {
          ...(wordResult.dades_extretes || {}),
          rev: wordResult.rev || '',
          data_revisio: wordResult.data_revisio || '',
          data_comprovacio: wordResult.data_comprovacio || '',
        },
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
          &larr; Tornar
        </button>
        <h2 style={{ margin: 0 }}>Nova fitxa tècnica</h2>
      </div>
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {wordResult && <p style={{ color: 'var(--success)' }}>Dades extretes del Word correctament.</p>}

      <FitxaForm initialData={initialData} onSubmit={handleCrear} isNew={true} />

      {novaFitxaId && (
        <DistribuirModal
          titol="Fitxa creada"
          missatge={`La fitxa ${novaFitxaCodi} s'ha creat correctament.`}
          onDistribuir={() => navigate(`/fitxes/${novaFitxaId}`, { state: { openDistribuir: true } })}
          onNoDistribuir={() => navigate(`/fitxes/${novaFitxaId}`)}
          onClose={() => navigate(`/fitxes/${novaFitxaId}`)}
        />
      )}
    </>
  );
}

export default NovaFitxa;
