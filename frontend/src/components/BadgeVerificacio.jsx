import { ETIQUETES_VERIFICACIO } from './verificacioEstats';

/** Badge de l'estat d'una comprovacio de desti. */
function BadgeVerificacio({ estat }) {
  if (!estat) return <span className="badge">—</span>;
  return (
    <span className={`badge ${estat}`}>
      {ETIQUETES_VERIFICACIO[estat] || estat}
    </span>
  );
}

export default BadgeVerificacio;
