/**
 * Enllac al fitxer del desti, per poder-lo obrir i revisar manualment.
 *
 * Les carpetes de xarxa no son navegables des del navegador (els enllacos
 * file:// estan bloquejats), aixi que el path es mostra seleccionable amb un
 * boto per copiar-lo i enganxar-lo a l'explorador.
 */
function EnllacDesti({ enllac, filename }) {
  const text = filename || enllac;
  if (!enllac) {
    return <code style={{ fontSize: '0.78rem' }}>{text || '—'}</code>;
  }

  const esWeb = /^https?:\/\//i.test(enllac);

  if (esWeb) {
    return (
      <a
        href={enllac}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: 'var(--brand)', fontSize: '0.82rem', wordBreak: 'break-all' }}
        title={`Obrir ${enllac}`}
      >
        {text}
      </a>
    );
  }

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
      <code style={{ fontSize: '0.78rem' }} title={enllac}>{text}</code>
      <button
        type="button"
        className="link-button"
        style={{ margin: 0, padding: 0, border: 'none', background: 'none', fontSize: '0.75rem' }}
        title={`Copiar ${enllac}`}
        onClick={() => navigator.clipboard?.writeText(enllac)}
      >
        copiar ruta
      </button>
    </span>
  );
}

export default EnllacDesti;
