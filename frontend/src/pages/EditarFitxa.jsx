import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import FitxaForm from '../components/FitxaForm';
import DistribuirModal from '../components/DistribuirModal';

function EditarFitxa() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const [fitxa, setFitxa] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showDistModal, setShowDistModal] = useState(false);
  const [importedPdf, setImportedPdf] = useState(null);
  const [importingPdf, setImportingPdf] = useState(false);
  const [formKey, setFormKey] = useState(0);
  const pdfInputRef = useRef(null);

  useEffect(() => {
    const carregarFitxa = async () => {
      try {
        const f = await api.detallFitxa(id);
        if ((f.tipus_producte || 'elaborat') === 'comercialitzat') {
          navigate(`/fitxes/${id}`, { replace: true });
          return;
        }
        setFitxa(f);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    carregarFitxa();
  }, [id, navigate]);

  const handleSubmit = async (formData) => {
    try {
      await api.editarFitxa(id, {
        nom_producte: formData.nom_producte,
        categoria: formData.categoria,
      });

      await api.crearVersio(id, {
        descripcio_canvi: formData.descripcio_canvi,
        contingut: formData.contingut,
        num_versio: formData.rev,
        data_revisio: formData.data_revisio || null,
        data_comprovacio: formData.data_comprovacio || null,
      });

      toast.success('Versió desada correctament');
      setShowDistModal(true);
    } catch (err) {
      setError(err.message);
      toast.error(`Error desant: ${err.message}`);
    }
  };

  const handlePdfImport = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    if (importedPdf || (ultimaVersio?.contingut && Object.keys(ultimaVersio.contingut).length > 0)) {
      if (!window.confirm("El formulari actual es sobreescriurà amb el contingut del PDF. Vols continuar?")) {
        return;
      }
    }

    setImportingPdf(true);
    try {
      const res = await api.parsePdf(id, file);
      setImportedPdf(res);
      setFormKey((k) => k + 1);
      if (res.warning) {
        toast.warning(res.warning);
      } else {
        toast.success("PDF importat correctament. Revisa el formulari abans de desar.");
      }
    } catch (err) {
      toast.error(`Error important PDF: ${err.message}`);
    } finally {
      setImportingPdf(false);
    }
  };

  if (loading) return <p aria-busy="true">Carregant...</p>;
  if (error && !fitxa) return <p style={{ color: 'var(--danger)' }}>{error}</p>;

  const versioActiva = fitxa?.versions?.find((v) => v.activa);
  const ultimaVersio = versioActiva || fitxa?.versions?.[0];
  const dadesWord = location.state?.dadesWord;
  const contingut = importedPdf?.contingut || dadesWord || ultimaVersio?.contingut || {};

  const initialData = {
    art_codi: fitxa?.art_codi || '',
    nom_producte: fitxa?.nom_producte || '',
    categoria: fitxa?.categoria || '',
    descripcio_canvi: importedPdf
      ? 'Actualització des de PDF'
      : (dadesWord ? 'Actualització des de Word' : ''),
    contingut,
    ...(importedPdf?.rev != null ? { rev: importedPdf.rev } : {}),
    ...(importedPdf?.data_revisio ? { data_revisio: importedPdf.data_revisio } : {}),
    ...(importedPdf?.data_comprovacio ? { data_comprovacio: importedPdf.data_comprovacio } : {}),
  };

  return (
    <>
      <div className="toolbar">
        <button className="outline secondary btn-sm" onClick={() => navigate(`/fitxes/${id}`)}>
          &larr; Tornar al detall
        </button>
        <h2 style={{ margin: 0 }}>Editar: {fitxa?.art_codi} - {fitxa?.nom_producte}</h2>
        <input
          type="file"
          accept=".pdf,application/pdf"
          ref={pdfInputRef}
          onChange={handlePdfImport}
          style={{ display: 'none' }}
        />
        <button
          type="button"
          className="outline"
          onClick={() => pdfInputRef.current?.click()}
          disabled={importingPdf}
          aria-busy={importingPdf}
          title="Pujar un PDF i pre-emplenar el formulari amb el seu contingut"
          style={{ marginLeft: 'auto' }}
        >
          {importingPdf ? 'Important PDF...' : 'Importar des de PDF'}
        </button>
      </div>
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {dadesWord && <p style={{ color: 'var(--success)' }}>Dades actualitzades des del Word.</p>}
      {importedPdf && (
        <p style={{ color: 'var(--success)' }}>
          Dades pre-emplenades des del PDF. Revisa-les i ajusta la descripció del canvi abans de desar.
        </p>
      )}

      <FitxaForm key={formKey} initialData={initialData} onSubmit={handleSubmit} isNew={false} versio={ultimaVersio} fitxaId={id} />

      {showDistModal && (
        <DistribuirModal
          titol="Versió desada"
          missatge={`Nova versió de ${fitxa?.art_codi} creada correctament.`}
          onDistribuir={() => navigate(`/fitxes/${id}`, { state: { openDistribuir: true } })}
          onNoDistribuir={() => navigate(`/fitxes/${id}`)}
          onClose={() => navigate(`/fitxes/${id}`)}
        />
      )}
    </>
  );
}

export default EditarFitxa;
