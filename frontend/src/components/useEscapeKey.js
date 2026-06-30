import { useEffect } from 'react';

/**
 * Crida `onEscape` quan l'usuari prem la tecla Escape.
 * Útil per tancar modals des del teclat (WCAG 2.1).
 */
export function useEscapeKey(onEscape) {
  useEffect(() => {
    if (!onEscape) return;
    const handler = (e) => {
      if (e.key === 'Escape') onEscape();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onEscape]);
}
