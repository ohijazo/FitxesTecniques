import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import FitxaForm from '../components/FitxaForm';
import DistribuirModal from '../components/DistribuirModal';

/* Claus de certificacio a partir d'una llista d'URLs d'imatge.
   Mateixa convencio que CertImageEditor (components/FitxaForm.jsx):
   certificacio_img, certificacio_img_2, certificacio_img_3... */
function clausCertificacio(urls) {
  if (!urls || !urls.length) return {};
  return Object.fromEntries(
    urls.map((url, i) => [i === 0 ? 'certificacio_img' : `certificacio_img_${i + 1}`, url]),
  );
}

function NovaFitxa() {
  const navigate = useNavigate();
  const toast = useToast();
  const [mode, setMode] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [wordResult, setWordResult] = useState(null);
  const [wordExistent, setWordExistent] = useState(null);
  const [novaFitxaId, setNovaFitxaId] = useState(null);
  const [novaFitxaCodi, setNovaFitxaCodi] = useState('');

  // Estat per al mode 'pdf' (fitxa comercialitzada)
  const [pdfForm, setPdfForm] = useState({ art_codi: '', nom_producte: '', categoria: '', file: null });
  const [creatingPdf, setCreatingPdf] = useState(false);
  const [conflicte, setConflicte] = useState(null); // { existent: {id, nom, tipus_producte}, file }

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
        setWordExistent(data);
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

  /** Confirmat que la fitxa ja existeix: crear-hi una versió nova des del Word. */
  const continuarAmbFitxaExistent = async () => {
    const data = wordExistent;
    setWordExistent(null);
    if (!data) return;

    // Si hi havia imatges al Word, associar-les a la fitxa existent
    const imatgesCert = {};
    if (data.imatges_temp_token) {
      try {
        const res = await api.imatgesFromTemp(data.fitxa.id, data.imatges_temp_token);
        if (res.total > 0) {
          // Referenciar-les al contingut (mateixa convencio que CertImageEditor):
          // sense aixo la imatge queda al disc pero no es veu enlloc.
          Object.assign(imatgesCert, clausCertificacio(res.imatges.map((im) => im.url)));
          toast.success(`${res.total} imatge(s) del Word associades a la fitxa`);
        }
      } catch (err) {
        toast.error(`Error associant imatges: ${err.message}`);
      }
    }
    navigate(`/fitxes/${data.fitxa.id}/editar`, {
      state: { dadesWord: {
        ...data.dades_extretes,
        ...imatgesCert,
        rev: data.rev || '',
        data_revisio: data.data_revisio || '',
        data_comprovacio: data.data_comprovacio || '',
      }},
    });
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

  const handleCrearComercialitzat = async (e) => {
    e.preventDefault();
    if (!pdfForm.art_codi.trim() || !pdfForm.nom_producte.trim() || !pdfForm.file) {
      setError('Cal indicar codi, nom del producte i el PDF.');
      return;
    }
    setCreatingPdf(true);
    setError(null);
    try {
      const { pdf_temp_token } = await api.uploadPdfTemp(pdfForm.file);
      const fitxa = await api.crearFitxa({
        art_codi: pdfForm.art_codi.trim(),
        nom_producte: pdfForm.nom_producte.trim(),
        categoria: pdfForm.categoria.trim(),
        tipus_producte: 'comercialitzat',
        pdf_temp_token,
        contingut: {},
      });
      toast.success('Fitxa comercialitzada creada correctament');
      setNovaFitxaId(fitxa.id);
      setNovaFitxaCodi(fitxa.art_codi);
    } catch (err) {
      // Si l'article ja existeix, oferir conversió o afegir com a nova versió
      if (err.status === 409 && err.body?.existent) {
        setConflicte({ existent: err.body.existent, file: pdfForm.file });
      } else {
        setError(err.message);
        toast.error(`Error creant: ${err.message}`);
      }
    } finally {
      setCreatingPdf(false);
    }
  };

  const handleConfirmarConflicte = async () => {
    if (!conflicte) return;
    const { existent, file } = conflicte;
    setCreatingPdf(true);
    try {
      if (existent.tipus_producte === 'comercialitzat') {
        await api.crearVersioPdf(existent.id, file, 'Actualització PDF proveïdor');
        toast.success(`Nova versió PDF de ${existent.nom_producte} creada`);
      } else {
        await api.convertirAComercialitzat(existent.id, file, 'Convertida a producte comercialitzat');
        toast.success(`Fitxa ${existent.nom_producte} convertida a comercialitzada`);
      }
      setConflicte(null);
      navigate(`/fitxes/${existent.id}`);
    } catch (err) {
      setError(err.message);
      toast.error(`Error: ${err.message}`);
    } finally {
      setCreatingPdf(false);
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
              Puja directament el PDF d'una fitxa rebuda d'un proveïdor.
            </p>
            <span style={{ color: 'var(--brand)' }}>Començar</span>
          </div>
        </div>

        <ConfirmDialog
          obert={Boolean(wordExistent)}
          titol="Aquesta fitxa ja existeix"
          textConfirmar="Crear una versió nova"
          onConfirmar={continuarAmbFitxaExistent}
          onCancelar={() => setWordExistent(null)}
        >
          <p style={{ margin: '0 0 0.5rem' }}>
            Ja hi ha una fitxa amb el codi <strong>{wordExistent?.fitxa?.art_codi}</strong>
            {wordExistent?.fitxa?.nom_producte ? <> ({wordExistent.fitxa.nom_producte})</> : null}.
          </p>
          <p style={{ margin: 0 }}>
            Es pot obrir l'editor amb les dades d'aquest Word per crear-hi una versió nova.
            La versió actual es conserva a l'historial.
          </p>
        </ConfirmDialog>
      </>
    );
  }

  if (mode === 'pdf') {
    return (
      <>
        <div className="toolbar">
          <button className="outline secondary btn-sm" onClick={() => { setMode(null); setPdfForm({ art_codi: '', nom_producte: '', categoria: '', file: null }); }}>
            &larr; Tornar
          </button>
          <h2 style={{ margin: 0 }}>Nova fitxa comercialitzada</h2>
        </div>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        <form onSubmit={handleCrearComercialitzat} className="card" style={{ maxWidth: '600px' }}>
          <label>
            Codi d'article *
            <input
              type="text"
              value={pdfForm.art_codi}
              onChange={(e) => setPdfForm((p) => ({ ...p, art_codi: e.target.value }))}
              required
              placeholder="ex: 60360"
            />
          </label>
          <label>
            Nom del producte *
            <input
              type="text"
              value={pdfForm.nom_producte}
              onChange={(e) => setPdfForm((p) => ({ ...p, nom_producte: e.target.value }))}
              required
              placeholder="ex: PBUK PUNJABI ATTA 10 KG"
            />
          </label>
          <label>
            Categoria
            <input
              type="text"
              value={pdfForm.categoria}
              onChange={(e) => setPdfForm((p) => ({ ...p, categoria: e.target.value }))}
              placeholder="opcional"
            />
          </label>
          <label>
            Fitxer PDF *
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setPdfForm((p) => ({ ...p, file: e.target.files?.[0] || null }))}
              required
            />
          </label>
          <button type="submit" disabled={creatingPdf} aria-busy={creatingPdf}>
            {creatingPdf ? 'Creant...' : 'Crear fitxa'}
          </button>
        </form>

        {conflicte && (
          <div className="modal-overlay" onClick={() => !creatingPdf && setConflicte(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <h3 style={{ margin: 0, marginBottom: '1rem' }}>Article ja existent</h3>
              <p style={{ fontSize: '0.92rem', marginBottom: '1rem' }}>
                L'article <strong>{pdfForm.art_codi}</strong> ja existeix a la BD com a{' '}
                <strong>{conflicte.existent.tipus_producte === 'comercialitzat' ? 'comercialitzat' : 'elaborat'}</strong>
                {' '}(<em>{conflicte.existent.nom_producte}</em>).
              </p>
              <p style={{ fontSize: '0.92rem', marginBottom: '1.25rem' }}>
                {conflicte.existent.tipus_producte === 'comercialitzat'
                  ? 'Vols afegir aquest PDF com a nova versió de la fitxa existent?'
                  : 'Vols convertir-la a comercialitzada pujant aquest PDF? Es crearà una nova versió amb el PDF i les versions anteriors elaborades es preservaran a l\'historial.'}
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button type="button" className="outline secondary" onClick={() => setConflicte(null)} disabled={creatingPdf}>
                  Cancel·lar
                </button>
                <button type="button" onClick={handleConfirmarConflicte} disabled={creatingPdf} aria-busy={creatingPdf}>
                  {creatingPdf ? 'Processant...' : (conflicte.existent.tipus_producte === 'comercialitzat' ? 'Afegir com a nova versió' : 'Convertir a comercialitzat')}
                </button>
              </div>
            </div>
          </div>
        )}

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

  const initialData = wordResult
    ? {
        art_codi: wordResult.art_codi || '',
        nom_producte: wordResult.nom_producte || '',
        categoria: '',
        descripcio_canvi: 'Creació inicial',
        contingut: {
          ...(wordResult.dades_extretes || {}),
          // Previsualitzacio: URLs temporals, el backend les substitueix per les
          // definitives en desar (la fitxa encara no te id en aquest punt).
          ...clausCertificacio(wordResult.imatges_temp_urls),
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
