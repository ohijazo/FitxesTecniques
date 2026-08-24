const API_BASE = '/api';

// Prou per a una pujada gran, però evita que una petició es quedi penjada per
// sempre si el backend no respon.
const TIMEOUT_MS = 60000;

function getToken() {
  return localStorage.getItem('token');
}

/** Tanca la sessió i torna al login recordant on érem, per no perdre el lloc. */
export function sessioCaducada() {
  localStorage.removeItem('token');
  localStorage.removeItem('usuari');
  const desti = window.location.pathname + window.location.search;
  if (desti && desti !== '/login') {
    sessionStorage.setItem('desti_despres_login', desti);
  }
  // replace i no href: així el botó "enrere" no torna a una pàgina sense sessió.
  window.location.replace('/login?expirada=1');
}

/**
 * Converteix els errors de xarxa en un missatge que l'usuari pugui entendre.
 * Sense això arribava "Failed to fetch" (o "NetworkError...") a la interfície,
 * en anglès i sense dir què fer.
 */
export function missatgeError(err) {
  if (!err) return 'Hi ha hagut un error inesperat.';
  if (err.name === 'AbortError' || err.name === 'TimeoutError') {
    return "El servidor ha trigat massa a respondre. Torna-ho a provar d'aquí a un moment.";
  }
  if (err instanceof TypeError) {
    return "No s'ha pogut connectar amb el servidor. Comprova la connexió i torna-ho a provar.";
  }
  return err.message || 'Hi ha hagut un error inesperat.';
}

/** Llegeix el cos d'una resposta d'error sense abocar HTML cru a la interfície. */
export async function errorDeResposta(response) {
  const raw = await response.text().catch(() => '');
  let parsed = null;
  try { parsed = raw ? JSON.parse(raw) : null; } catch { /* no és JSON */ }
  if (parsed && parsed.error) {
    const err = new Error(parsed.error);
    err.body = parsed;
    err.status = response.status;
    return err;
  }
  // Un 500 darrere d'un proxy sol tornar una pàgina HTML: enganxar-la al toast
  // no ajuda ningú.
  const err = new Error(
    response.status >= 500
      ? `El servidor ha respost amb un error (${response.status}). Torna-ho a provar; si continua, avisa l'administrador.`
      : `La petició no s'ha pogut completar (${response.status}).`
  );
  err.status = response.status;
  err.raw = raw ? raw.slice(0, 300) : '';
  return err;
}

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const token = getToken();
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  };

  let response;
  try {
    response = await fetch(url, { ...config, signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch (err) {
    throw new Error(missatgeError(err));
  }

  if (response.status === 401) {
    sessioCaducada();
    throw new Error('La sessió ha caducat. Torna a iniciar sessió.');
  }

  if (!response.ok) {
    throw await errorDeResposta(response);
  }

  return response.json();
}

/**
 * Pujada de fitxers. Les cinc pujades repetien el mateix bloc de gestió de
 * 401 + parse, i `pujarImatge` no en tenia cap: amb un 413 o un 502 amb cos
 * HTML, el `res.json()` rebentava amb un SyntaxError que acabava en un alert.
 */
async function pujarFitxer(path, formData) {
  const token = getToken();
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (err) {
    throw new Error(missatgeError(err));
  }
  if (res.status === 401) {
    sessioCaducada();
    throw new Error('La sessió ha caducat. Torna a iniciar sessió.');
  }
  if (!res.ok) throw await errorDeResposta(res);
  return res.json().catch(() => ({}));
}

export const api = {
  // Auth
  login: (email, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }),
  perfil: () => request('/auth/me'),
  refreshToken: () => request('/auth/refresh', { method: 'POST' }),

  // Fitxes
  llistarFitxes: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/fitxes${query ? `?${query}` : ''}`);
  },
  llistarIdsFitxes: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/fitxes/ids${query ? `?${query}` : ''}`);
  },
  detallFitxa: (id) => request(`/fitxes/${id}`),
  crearFitxa: (data) => request('/fitxes', { method: 'POST', body: JSON.stringify(data) }),
  editarFitxa: (id, data) => request(`/fitxes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  duplicarFitxa: (id, data) => request(`/fitxes/${id}/duplicar`, { method: 'POST', body: JSON.stringify(data) }),
  actualitzarObservacions: (id, observacions) => request(`/fitxes/${id}/observacions`, { method: 'PUT', body: JSON.stringify({ observacions }) }),
  eliminarFitxa: (id, data) => request(`/fitxes/${id}`, { method: 'DELETE', body: JSON.stringify(data) }),
  canviarEstatFitxa: (id, data) => request(`/fitxes/${id}/estat`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Versions
  llistarVersions: (fitxaId) => request(`/fitxes/${fitxaId}/versions`),
  crearVersio: (fitxaId, data) => request(`/fitxes/${fitxaId}/versions`, { method: 'POST', body: JSON.stringify(data) }),
  publicarVersio: (fitxaId, vid) => request(`/fitxes/${fitxaId}/versions/${vid}/publicar`, { method: 'POST' }),
  aprovarVersio: (fitxaId, vid) => request(`/fitxes/${fitxaId}/versions/${vid}/aprovar`, { method: 'POST' }),
  enviarRevisio: (fitxaId, vid) => request(`/fitxes/${fitxaId}/versions/${vid}/revisar`, { method: 'POST' }),
  esborrarUltimaVersio: (fitxaId, data) => request(`/fitxes/${fitxaId}/versions/ultima`, { method: 'DELETE', body: JSON.stringify(data) }),
  diffVersions: (fitxaId, v1, v2) => request(`/fitxes/${fitxaId}/versions/diff?v1=${v1}&v2=${v2}`),

  // Distribucions
  llistarDistribucions: (fitxaId) => request(`/fitxes/${fitxaId}/distribucions`),
  distribuirTots: (fitxaId) => request(`/fitxes/${fitxaId}/distribuir`, { method: 'POST' }),
  distribuirDesti: (fitxaId, destiId) => request(`/fitxes/${fitxaId}/distribuir/${destiId}`, { method: 'POST' }),
  retirarDesti: (fitxaId, destiId, data) => request(`/fitxes/${fitxaId}/retirar/${destiId}`, { method: 'POST', body: JSON.stringify(data) }),

  // Importar PDF a edició (parser → JSON sense persistir)
  parsePdf: (fitxaId, file) => {
    const formData = new FormData();
    formData.append('pdf', file);
    return pujarFitxer(`/fitxes/${fitxaId}/parse-pdf`, formData);
  },

  // Pujada de PDF per a fitxes de producte comercialitzat
  uploadPdfTemp: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return pujarFitxer('/fitxes/upload-pdf-temp', formData);
  },
  crearVersioPdf: (fitxaId, file, descripcioCanvi) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('descripcio_canvi', descripcioCanvi || '');
    return pujarFitxer(`/fitxes/${fitxaId}/versions/upload-pdf`, formData);
  },
  convertirAComercialitzat: (fitxaId, file, descripcioCanvi) => {
    const formData = new FormData();
    formData.append('file', file);
    if (descripcioCanvi) formData.append('descripcio_canvi', descripcioCanvi);
    return pujarFitxer(`/fitxes/${fitxaId}/convertir-a-comercialitzat`, formData);
  },

  // Imatges
  pujarImatge: (fitxaId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return pujarFitxer(`/fitxes/${fitxaId}/imatges`, formData);
  },
  llistarImatges: (fitxaId) => request(`/fitxes/${fitxaId}/imatges`),
  imatgesFromTemp: (fitxaId, tempToken) => request(`/fitxes/${fitxaId}/imatges/from-temp`, { method: 'POST', body: JSON.stringify({ temp_token: tempToken }) }),

  // Admin - Tipus de fitxa
  llistarTipus: () => request('/admin/tipus'),
  detallTipus: (id) => request(`/admin/tipus/${id}`),
  crearTipus: (data) => request('/admin/tipus', { method: 'POST', body: JSON.stringify(data) }),
  editarTipus: (id, data) => request(`/admin/tipus/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  eliminarTipus: (id) => request(`/admin/tipus/${id}`, { method: 'DELETE' }),
  duplicarTipus: (id, data) => request(`/admin/tipus/${id}/duplicar`, { method: 'POST', body: JSON.stringify(data) }),

  // Admin - Seccions + Camps
  llistarSeccions: (tipusId) => request(`/admin/seccions${tipusId ? `?tipus_id=${tipusId}` : ''}`),
  crearSeccio: (data) => request('/admin/seccions', { method: 'POST', body: JSON.stringify(data) }),
  editarSeccio: (id, data) => request(`/admin/seccions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  eliminarSeccio: (id) => request(`/admin/seccions/${id}`, { method: 'DELETE' }),
  reordenarSeccions: (ordre) => request('/admin/seccions/reorder', { method: 'PUT', body: JSON.stringify({ ordre }) }),
  crearCamp: (seccioId, data) => request(`/admin/seccions/${seccioId}/camps`, { method: 'POST', body: JSON.stringify(data) }),
  editarCamp: (id, data) => request(`/admin/camps/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  eliminarCamp: (id) => request(`/admin/camps/${id}`, { method: 'DELETE' }),
  reordenarCamps: (seccioId, ordre) => request(`/admin/seccions/${seccioId}/camps/reorder`, { method: 'PUT', body: JSON.stringify({ ordre }) }),

  // Admin - Usuaris
  llistarUsuaris: () => request('/admin/usuaris'),
  crearUsuari: (data) => request('/admin/usuaris', { method: 'POST', body: JSON.stringify(data) }),
  editarUsuari: (id, data) => request(`/admin/usuaris/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  eliminarUsuari: (id) => request(`/admin/usuaris/${id}`, { method: 'DELETE' }),

  // Admin - Destins
  llistarDestins: () => request('/admin/destins'),
  crearDesti: (data) => request('/admin/destins', { method: 'POST', body: JSON.stringify(data) }),
  detallDesti: (id) => request(`/admin/destins/${id}`),
  editarDesti: (id, data) => request(`/admin/destins/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  eliminarDesti: (id) => request(`/admin/destins/${id}`, { method: 'DELETE' }),

  // Admin - Estats
  llistarEstats: () => request('/admin/estats'),
  crearEstat: (data) => request('/admin/estats', { method: 'POST', body: JSON.stringify(data) }),
  editarEstat: (id, data) => request(`/admin/estats/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  eliminarEstat: (id) => request(`/admin/estats/${id}`, { method: 'DELETE' }),
  llistarAccionsEstat: () => request('/admin/estats/accions'),

  // Admin - Audit log
  llistarAuditLog: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/admin/audit-log${query ? `?${query}` : ''}`);
  },

  // Jobs massius
  crearJobDistribucio: (data) => request('/jobs/distribucio-massiva', { method: 'POST', body: JSON.stringify(data) }),
  llistarJobs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/jobs${query ? `?${query}` : ''}`);
  },
  detallJob: (id) => request(`/jobs/${id}`),
  itemsJob: (id, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/jobs/${id}/items${query ? `?${query}` : ''}`);
  },
  reprendreJob: (id) => request(`/jobs/${id}/reprendre`, { method: 'POST' }),
  retryErrorsJob: (id) => request(`/jobs/${id}/retry-errors`, { method: 'POST' }),
  cancellarJob: (id) => request(`/jobs/${id}/cancellar`, { method: 'POST' }),
  arxivarJob: (id) => request(`/jobs/${id}/arxivar`, { method: 'POST' }),

  // Bulk edit
  bulkEditFitxes: (data) => request('/fitxes/bulk-edit', { method: 'POST', body: JSON.stringify(data) }),
};
