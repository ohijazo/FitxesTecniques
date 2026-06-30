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
          // Si hi havia imatges al Word, associar-les a la fitxa existent
          if (data.imatges_temp_token) {
            try {
              const res = await api.imatgesFromTemp(data.fitxa.id, data.imatges_temp_token);
              if (res.total > 0) {
                toast.success(`${res.total} imatge(s) del Word associades a la fitxa`);
              }
            } catch (err) {
              toast.error(`Error associant imatges: ${err.message}`);
            }
          }
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
        // Metadades de capçalera (editades al formulari, predefinides des del Word)
        rev: formData.rev || '',
        data_revisio: formData.data_revisio || '',
        data_comprovacio: formData.data_comprovacio || '',
        // Token de les imatges extretes del Word per moure-les a la fitxa
        imatges_temp_token: wordResult?.imatges_temp_token || null,
      });

      toast.success('Fitxa creada correctament');
      if (wordResult?.imatges_temp_token && wordResult?.imatges_temp_noms?.length) {
        toast.success(`${wordResult.imatges_temp_noms.length} imatge(s) del Word importades`);
      }
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

          <div className="option-card" onClick={() => setMode('pdf')}>
            <h3>Producte comercialitzat (PDF)</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Per a productes revenuts: només es puja el PDF rebut del proveïdor, sense formulari.
            </p>
            <span style={{ color: 'var(--brand)' }}>Començar</span>
          </div>
        </div>
      </>
    );
  }

  if (mode === 'pdf') {
    return (
      <NovaFitxaPdf
        onCreated={(fitxa) => { setNovaFitxaId(fitxa.id); setNovaFitxaCodi(fitxa.art_codi); }}
        onBack={() => setMode(null)}
        novaFitxaId={novaFitxaId}
        novaFitxaCodi={novaFitxaCodi}
        navigate={navigate}
      />
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

function NovaFitxaPdf({ onCreated, onBack, novaFitxaId, novaFitxaCodi, navigate }) {
  const toast = useToast();
  const [artCodi, setArtCodi] = useState('');
  const [nomProducte, setNomProducte] = useState('');
  const [categoria, setCategoria] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!artCodi.trim() || !nomProducte.trim()) {
      setError("Cal indicar el codi d'article i el nom del producte");
      return;
    }
    if (!file) {
      setError("Cal seleccionar el PDF");
      return;
    }

    setLoading(true);
    try {
      const { pdf_temp_token } = await api.uploadPdfTemp(file);
      const fitxa = await api.crearFitxa({
        art_codi: artCodi.trim(),
        nom_producte: nomProducte.trim(),
        categoria: categoria.trim(),
        descripcio_canvi: 'Pujada inicial del PDF',
        tipus_producte: 'comercialitzat',
        pdf_temp_token,
      });
      toast.success('Fitxa comercialitzada creada correctament');
      onCreated(fitxa);
    } catch (err) {
      setError(err.message);
      toast.error(`Error creant: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="toolbar">
        <button className="outline secondary btn-sm" onClick={onBack}>&larr; Tornar</button>
        <h2 style={{ margin: 0 }}>Nova fitxa de producte comercialitzat</h2>
      </div>

      <form onSubmit={handleSubmit} style={{ maxWidth: 600 }}>
        <label>
          Codi d'article *
          <input
            type="text"
            value={artCodi}
            onChange={(e) => setArtCodi(e.target.value)}
            placeholder="Ex: 60360"
            required
            disabled={loading}
          />
        </label>

        <label>
          Nom del producte *
          <input
            type="text"
            value={nomProducte}
            onChange={(e) => setNomProducte(e.target.value)}
            placeholder="Ex: PBUK PUNJABI ATTA 10 KG"
            required
            disabled={loading}
          />
        </label>

        <label>
          Categoria
          <input
            type="text"
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            placeholder="Opcional"
            disabled={loading}
          />
        </label>

        <label>
          PDF *
          <input
            type="file"
            accept=".pdf,application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
            disabled={loading}
          />
          {file && (
            <small style={{ color: 'var(--gray-500)' }}>
              {file.name} ({(file.size / 1024).toFixed(0)} KB)
            </small>
          )}
        </label>

        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        <button type="submit" disabled={loading} aria-busy={loading}>
          {loading ? 'Creant...' : 'Crear fitxa'}
        </button>
      </form>

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
