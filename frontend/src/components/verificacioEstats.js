// Vocabulari de la comprovacio de destins (ha de coincidir amb
// backend/app/services/verificador.py ESTATS).
export const ESTATS_VERIFICACIO = [
  'ok',
  'no_trobat',
  'desfasat',
  'error_acces',
  'error_parseig',
  'no_verificable',
];

export const ETIQUETES_VERIFICACIO = {
  ok: 'Correcte',
  no_trobat: 'No hi és',
  desfasat: 'Desfasat',
  error_acces: "No s'hi ha pogut accedir",
  error_parseig: 'PDF il·legible',
  no_verificable: 'No comprovable',
};
