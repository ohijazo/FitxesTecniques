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
  potConfirmar = true,
  onConfirmar,
  onCancelar,
}) {
  const dialogRef = useRef(null);
  const confirmarRef = useRef(null);
  const focusPrevi = useRef(null);
  const titolId = useId();

  // Els callbacks arriben com a funcions inline i canvien a cada render. Si
  // entressin a les dependències de l'efecte, aquest es reexecutaria sempre i
  // la neteja robaria el focus.
  const accions = useRef({ onConfirmar, onCancelar });
  useEffect(() => {
    accions.current = { onConfirmar, onCancelar };
  }, [onConfirmar, onCancelar]);

  // Focus: entrar-hi en obrir i tornar-lo al botó que l'ha obert en tancar.
  useEffect(() => {
    if (!obert) return undefined;

    focusPrevi.current = document.activeElement;
    // Si el diàleg demana una dada, el focus hi va. Si no, va al botó de
    // cancel·lar en accions destructives, per no confirmar sense voler amb un
    // Enter, i al de confirmar en la resta.
    const camp = dialogRef.current?.querySelector('[data-focus-inicial]');
    const inicial = camp
      || (destructiu ? dialogRef.current?.querySelector('[data-cancelar]') : confirmarRef.current);
    inicial?.focus();
    if (camp && typeof camp.select === 'function') camp.select();

    const previ = focusPrevi.current;
    return () => {
      if (previ && document.contains(previ)) previ.focus();
    };
  }, [obert, destructiu]);

  // Escape tanca; Enter dins d'un camp confirma (com feia el prompt() natiu);
  // Tab no ha de poder sortir del diàleg.
  useEffect(() => {
    if (!obert) return undefined;
    const node = dialogRef.current;
    if (!node) return undefined;

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        accions.current.onCancelar?.();
        return;
      }
      if (e.key === 'Enter' && e.target?.matches?.('input:not([type=checkbox])')) {
        e.preventDefault();
        accions.current.onConfirmar?.();
        return;
      }
      if (e.key !== 'Tab') return;
      const focusables = node.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusables.length === 0) return;
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

    node.addEventListener('keydown', onKeyDown);
    return () => node.removeEventListener('keydown', onKeyDown);
  }, [obert]);

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
            style={{ margin: 0 }} onClick={onConfirmar} aria-busy={ocupat}
            disabled={ocupat || !potConfirmar}>
            {textConfirmar}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;
