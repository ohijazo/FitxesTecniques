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
    const raw = await response.text().catch(() => '');
    let parsed = null;
    try { parsed = raw ? JSON.parse(raw) : null; } catch { /* no JSON */ }
    if (parsed && parsed.error) {
      const err = new Error(parsed.error);
      err.body = parsed;
      err.status = response.status;
      throw err;
    }
    const body = raw ? raw.slice(0, 300) : '(resposta buida)';
    const err = new Error(`HTTP ${response.status}: ${body}`);
    err.status = response.status;
    throw err;
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
    const token = getToken();
    return fetch(`${API_BASE}/fitxes/${fitxaId}/parse-pdf`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    }).then(async (res) => {
      if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('usuari');
        window.location.href = '/login';
        throw new Error('Sessió expirada');
      }
      const raw = await res.text().catch(() => '');
      let parsed = null;
      try { parsed = raw ? JSON.parse(raw) : null; } catch { /* no JSON */ }
      if (!res.ok) {
        throw new Error((parsed && parsed.error) || `HTTP ${res.status}: ${raw.slice(0, 200)}`);
      }
      return parsed;
    });
  },

  // Pujada de PDF per a fitxes de producte comercialitzat
  uploadPdfTemp: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getToken();
    return fetch(`${API_BASE}/fitxes/upload-pdf-temp`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    }).then(async (res) => {
      if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('usuari');
        window.location.href = '/login';
        throw new Error('Sessió expirada');
      }
      const raw = await res.text().catch(() => '');
      let parsed = null;
      try { parsed = raw ? JSON.parse(raw) : null; } catch { /* no JSON */ }
      if (!res.ok) {
        throw new Error((parsed && parsed.error) || `HTTP ${res.status}: ${raw.slice(0, 200)}`);
      }
      return parsed;
    });
  },
  crearVersioPdf: (fitxaId, file, descripcioCanvi) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('descripcio_canvi', descripcioCanvi || '');
    const token = getToken();
    return fetch(`${API_BASE}/fitxes/${fitxaId}/versions/upload-pdf`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    }).then(async (res) => {
      if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('usuari');
        window.location.href = '/login';
        throw new Error('Sessió expirada');
      }
      const raw = await res.text().catch(() => '');
      let parsed = null;
      try { parsed = raw ? JSON.parse(raw) : null; } catch { /* no JSON */ }
      if (!res.ok) {
        throw new Error((parsed && parsed.error) || `HTTP ${res.status}: ${raw.slice(0, 200)}`);
      }
      return parsed;
    });
  },
  convertirAComercialitzat: (fitxaId, file, descripcioCanvi) => {
    const formData = new FormData();
    formData.append('file', file);
    if (descripcioCanvi) formData.append('descripcio_canvi', descripcioCanvi);
    const token = getToken();
    return fetch(`${API_BASE}/fitxes/${fitxaId}/convertir-a-comercialitzat`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    }).then(async (res) => {
      if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('usuari');
        window.location.href = '/login';
        throw new Error('Sessió expirada');
      }
      const raw = await res.text().catch(() => '');
      let parsed = null;
      try { parsed = raw ? JSON.parse(raw) : null; } catch { /* no JSON */ }
      if (!res.ok) {
        throw new Error((parsed && parsed.error) || `HTTP ${res.status}: ${raw.slice(0, 200)}`);
      }
      return parsed;
    });
  },

  // Imatges
  pujarImatge: (fitxaId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getToken();
    return fetch(`${API_BASE}/fitxes/${fitxaId}/imatges`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    }).then(res => {
      if (!res.ok) return res.json().then(e => { throw new Error(e.error); });
      return res.json();
    });
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
