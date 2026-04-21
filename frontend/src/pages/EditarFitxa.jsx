import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../api/client';
import FitxaForm from '../components/FitxaForm';

function EditarFitxa() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [fitxa, setFitxa] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const carregarFitxa = async () => {
      try {
        const f = await api.detallFitxa(id);
        setFitxa(f);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    carregarFitxa();
  }, [id]);

  const handleSubmit = async (formData) => {
    try {
      await api.editarFitxa(id, {
        nom_producte: formData.nom_producte,
        categoria: formData.categoria,
      });

      await api.crearVersio(id, {
        descripcio_canvi: formData.descripcio_canvi,
        contingut: formData.contingut,
      });

      if (confirm('Versió desada correctament. Vols distribuir-la ara?')) {
        navigate(`/fitxes/${id}`, { state: { openDistribuir: true } });
      } else {
        navigate(`/fitxes/${id}`);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <p aria-busy="true">Carregant...</p>;
  if (error && !fitxa) return <p style={{ color: '#dc3545' }}>{error}</p>;

  const versioActiva = fitxa?.versions?.find((v) => v.activa);
  const ultimaVersio = versioActiva || fitxa?.versions?.[0];
  const dadesWord = location.state?.dadesWord;
  const contingut = dadesWord || ultimaVersio?.contingut || {};

  const initialData = {
    art_codi: fitxa?.art_codi || '',
    nom_producte: fitxa?.nom_producte || '',
    categoria: fitxa?.categoria || '',
    descripcio_canvi: dadesWord ? 'Actualització des de Word' : '',
    contingut,
  };

  return (
    <>
      <div className="toolbar">
        <button className="outline secondary btn-sm" onClick={() => navigate(`/fitxes/${id}`)}>
          ← Tornar al detall
        </button>
        <h2 style={{ margin: 0 }}>Editar: {fitxa?.art_codi} - {fitxa?.nom_producte}</h2>
      </div>
      {error && <p style={{ color: '#dc3545' }}>{error}</p>}
      {dadesWord && <p style={{ color: '#28a745' }}>Dades actualitzades des del Word.</p>}

      <FitxaForm initialData={initialData} onSubmit={handleSubmit} isNew={false} versio={ultimaVersio} />
    </>
  );
}

export default EditarFitxa;
