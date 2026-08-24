import { useEffect, useRef, useId } from 'react';

/**
 * Diàleg de confirmació reutilitzable.
 *
 * Substitueix els `confirm()` natius, que no es poden estilar, no parlen
 * català i no es distingeixen d'un avís del navegador. També aporta la
 * semàntica de diàleg que als modals de l'app li faltava: role="dialog",
 * aria-modal, focus dins del diàleg en obrir-se, retorn del focus en tancar,
 * retenció del focus amb Tab i tancament amb Escape.
 *
 * El clic al fons NO tanca: en un diàleg destructiu un clic fora és
 * pràcticament sempre accidental.
 */
function ConfirmDialog({
  obert,
  titol,
  children,
  textConfirmar = 'Confirmar',
  textCancelar = 'Cancel·lar',
  destructiu = false,
  ocupat = false,
  onConfirmar,
  onCancelar,
}) {
  const dialogRef = useRef(null);
  const confirmarRef = useRef(null);
  const focusPrevi = useRef(null);
  const titolId = useId();

  useEffect(() => {
    if (!obert) return;

    focusPrevi.current = document.activeElement;
    // El focus va al botó de cancel·lar per defecte en accions destructives,
    // per no confirmar sense voler amb un Enter.
    const inicial = destructiu ? dialogRef.current?.querySelector('[data-cancelar]') : confirmarRef.current;
    inicial?.focus();

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onCancelar?.();
        return;
      }
      if (e.key !== 'Tab') return;
      // Retenir el focus: sense això es tabula cap a la pàgina de sota.
      const focusables = dialogRef.current?.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (!focusables || focusables.length === 0) return;
      const primer = focusables[0];
      const ultim = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === primer) {
        e.preventDefault();
        ultim.focus();
      } else if (!e.shiftKey && document.activeElement === ultim) {
        e.preventDefault();
        primer.focus();
      }
    };

    const node = dialogRef.current;
    node?.addEventListener('keydown', onKeyDown);
    return () => {
      node?.removeEventListener('keydown', onKeyDown);
      focusPrevi.current?.focus?.();
    };
  }, [obert, destructiu, onCancelar]);

  if (!obert) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content" role="dialog" aria-modal="true"
        aria-labelledby={titolId} ref={dialogRef}>
        <h3 id={titolId} style={{ marginTop: 0 }}>{titol}</h3>
        <div style={{ fontSize: '0.9rem', color: 'var(--gray-700)' }}>{children}</div>
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1.25rem' }}>
          <button type="button" data-cancelar className="outline secondary"
            style={{ margin: 0 }} onClick={onCancelar} disabled={ocupat}>
            {textCancelar}
          </button>
          <button type="button" ref={confirmarRef}
            className={destructiu ? 'btn-danger' : ''}
            style={{ margin: 0 }} onClick={onConfirmar} aria-busy={ocupat} disabled={ocupat}>
            {textConfirmar}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;
