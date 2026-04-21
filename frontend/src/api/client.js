const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('token');
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

  const response = await fetch(url, config);

  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('usuari');
    window.location.href = '/login';
    throw new Error('Sessió expirada');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Error desconegut' }));
    throw new Error(error.error || `Error ${response.status}`);
  }

  return response.json();
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
  detallFitxa: (id) => request(`/fitxes/${id}`),
  crearFitxa: (data) => request('/fitxes', { method: 'POST', body: JSON.stringify(data) }),
  editarFitxa: (id, data) => request(`/fitxes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  eliminarFitxa: (id, esborrarFtp = false) => request(`/fitxes/${id}${esborrarFtp ? '?esborrar_ftp=1' : ''}`, { method: 'DELETE' }),

  // Versions
  llistarVersions: (fitxaId) => request(`/fitxes/${fitxaId}/versions`),
  crearVersio: (fitxaId, data) => request(`/fitxes/${fitxaId}/versions`, { method: 'POST', body: JSON.stringify(data) }),
  publicarVersio: (fitxaId, vid) => request(`/fitxes/${fitxaId}/versions/${vid}/publicar`, { method: 'POST' }),
  aprovarVersio: (fitxaId, vid) => request(`/fitxes/${fitxaId}/versions/${vid}/aprovar`, { method: 'POST' }),
  enviarRevisio: (fitxaId, vid) => request(`/fitxes/${fitxaId}/versions/${vid}/revisar`, { method: 'POST' }),
  diffVersions: (fitxaId, v1, v2) => request(`/fitxes/${fitxaId}/versions/diff?v1=${v1}&v2=${v2}`),

  // Distribucions
  llistarDistribucions: (fitxaId) => request(`/fitxes/${fitxaId}/distribucions`),
  distribuirTots: (fitxaId) => request(`/fitxes/${fitxaId}/distribuir`, { method: 'POST' }),
  distribuirDesti: (fitxaId, destiId) => request(`/fitxes/${fitxaId}/distribuir/${destiId}`, { method: 'POST' }),

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
};
