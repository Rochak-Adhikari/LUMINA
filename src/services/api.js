// services/api.js — REST client for the FastAPI backend.
// Thin fetch wrapper with JSON handling + error normalization. Uses only
// endpoints documented in docs/backend/API_REFERENCE.md.
import { BASE_URL, REST } from './endpoints';

async function request(path, { method = 'GET', body } = {}) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE_URL}${path}`, opts);
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON / empty */ }
  if (!res.ok) {
    const msg = (data && (data.error || data.msg)) || `HTTP ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  status: () => request(REST.status),
  whatsappReply: (text, sender) => request(REST.whatsappReply, { method: 'POST', body: { text, sender } }),
  getBrowserConfirmation: () => request(REST.browserConfirmationGet),
  setBrowserConfirmation: (mode) => request(REST.browserConfirmationSet, { method: 'POST', body: { mode } }),
  visionLatest: () => request(REST.visionLatest),
  localBrowserStatus: () => request(REST.localBrowserStatus),
  localBrowserOpen: (url) => request(REST.localBrowserOpen, { method: 'POST', body: { url } }),
  memoryStatus: () => request(REST.memoryStatus),
  memorySearch: (query, top_k = 8) => request(REST.memorySearch, { method: 'POST', body: { query, top_k } }),
  memoryReindex: () => request(REST.memoryReindex, { method: 'POST' }),
  memoryPending: () => request(REST.memoryPending),
  memoryConfirm: (id) => request(REST.memoryConfirm, { method: 'POST', body: { id } }),
  memoryDeny: (id) => request(REST.memoryDeny, { method: 'POST', body: { id } }),
};

export default api;
