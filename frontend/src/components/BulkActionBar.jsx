/**
 * Barra flotant inferior que apareix quan hi ha fitxes seleccionades.
 * Mostra el comptador i botons per accions massives (edició / distribució).
 */
function BulkActionBar({ count, usuariRol, onDistribuir, onEditar, onDeseleccionar }) {
  if (count <= 0) return null;

  const potEditar = usuariRol === 'admin';
  const potDistribuir = ['admin', 'editor', 'distribuidor'].includes(usuariRol);

  return (
    <div className="bulk-action-bar" role="region" aria-label="Accions massives">
      <span className="bulk-action-count">
        <strong>{count}</strong> {count === 1 ? 'fitxa seleccionada' : 'fitxes seleccionades'}
      </span>
      <div className="bulk-action-buttons">
        {potEditar && (
          <button type="button" className="outline" onClick={onEditar} title="Edició massiva">
            Edició massiva
          </button>
        )}
        {potDistribuir && (
          <button type="button" onClick={onDistribuir} title="Distribució massiva">
            Distribució massiva
          </button>
        )}
        <button type="button" className="outline secondary" onClick={onDeseleccionar}>
          Deselecciona
        </button>
      </div>
    </div>
  );
}

export default BulkActionBar;
