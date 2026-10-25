/**
 * api.js — Centralized HTTP client for SAFAR AICTE FDR Management Portal.
 * Connects React frontend directly to FastAPI backend on http://localhost:8000.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function getToken() {
  return sessionStorage.getItem('safar_token') || '';
}

export function setToken(token) {
  if (token) {
    sessionStorage.setItem('safar_token', token);
  } else {
    sessionStorage.removeItem('safar_token');
  }
}

export function getCurrentUser() {
  const user = sessionStorage.getItem('safar_user');
  try {
    return user ? JSON.parse(user) : null;
  } catch {
    return null;
  }
}

export function setCurrentUser(user) {
  if (user) {
    sessionStorage.setItem('safar_user', JSON.stringify(user));
  } else {
    sessionStorage.removeItem('safar_user');
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}`;
      try {
        const errJson = await res.json();
        errorMsg = errJson.detail || errJson.message || errorMsg;
      } catch {
        // fallback
      }
      throw new Error(errorMsg);
    }
    // Return json if content-type matches, else raw
    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await res.json();
    }
    return await res.text();
  } catch (err) {
    console.error(`API Error [${options.method || 'GET'} ${endpoint}]:`, err);
    throw err;
  }
}

export const api = {
  // ── Authentication ───────────────────────────────────────────────────────────
  login: async (username, password = 'demo1234') => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    setToken(data.access_token);
    setCurrentUser(data.user);
    return data;
  },

  getMe: () => request('/auth/me'),

  // ── Dashboard Metrics ────────────────────────────────────────────────────────
  getDashboardStats: () => request('/dashboard/stats'),

  // ── Technical Institutions ───────────────────────────────────────────────────
  getInstitutions: () => request('/institutions'),

  // ── FDR Instruments ──────────────────────────────────────────────────────────
  getInstruments: (params = {}) => {
    const query = new URLSearchParams();
    if (params.institution_id) query.append('institution_id', params.institution_id);
    if (params.status) query.append('status', params.status);
    if (params.stage) query.append('stage', params.stage);
    const qs = query.toString();
    return request(`/instruments${qs ? `?${qs}` : ''}`);
  },

  getInstrumentDetail: (id) => request(`/instruments/${id}`),

  createInstrument: (data) =>
    request('/instruments', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  verifyBank: (instrumentId) =>
    request(`/instruments/${instrumentId}/verify-bank`, {
      method: 'POST',
    }),

  triggerTransition: (instrumentId, event, reason = '', payload = {}) =>
    request(`/instruments/${instrumentId}/transition`, {
      method: 'POST',
      body: JSON.stringify({ event, reason, payload }),
    }),

  getLineage: (instrumentId) => request(`/instruments/${instrumentId}/lineage`),

  addNote: (instrumentId, text) =>
    request(`/instruments/${instrumentId}/notes`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  openDispute: (instrumentId, reason) =>
    request(`/instruments/${instrumentId}/disputes`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  clearDispute: (disputeId, reason) =>
    request(`/disputes/${disputeId}/clear?reason=${encodeURIComponent(reason)}`, {
      method: 'POST',
    }),

  requestRelease: (instrumentId, data) =>
    request(`/instruments/${instrumentId}/release`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ── Cryptographic Audit Ledger ───────────────────────────────────────────────
  getAuditEntries: (skip = 0, limit = 100) =>
    request(`/audit/entries?skip=${skip}&limit=${limit}`),

  verifyAuditChain: () => request('/audit/verify'),

  simulateTamper: () =>
    request('/audit/simulate-tamper', {
      method: 'POST',
    }),

  repairAuditChain: () =>
    request('/audit/repair', {
      method: 'POST',
    }),

  // ── Evaluator Simulation Clock ───────────────────────────────────────────────
  getClock: () => request('/clock'),

  advanceClock: (days = 30) =>
    request(`/clock/advance?days=${days}`, {
      method: 'POST',
    }),

  resetClock: () =>
    request('/clock/reset', {
      method: 'POST',
    }),

  // ── Alerts & Scheduler ───────────────────────────────────────────────────────
  getAlerts: (instrumentId) => {
    const qs = instrumentId ? `?instrument_id=${encodeURIComponent(instrumentId)}` : '';
    return request(`/alerts${qs}`);
  },

  runSchedulerNow: () =>
    request('/scheduler/run-now', {
      method: 'POST',
    }),

  // ── AICTE Rules ──────────────────────────────────────────────────────────────
  getRules: () => request('/rules'),

  updateRule: (key, value, clause_reference = '') =>
    request('/rules', {
      method: 'POST',
      body: JSON.stringify({ key, value, clause_reference }),
    }),
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Format amount in Indian Rupees (₹).
 * Handles amounts stored in paise (1 INR = 100 paise) or rupees.
 */
export function formatINR(amountPaise) {
  if (amountPaise === null || amountPaise === undefined) return '₹0';
  const rupees = typeof amountPaise === 'number' ? Math.round(amountPaise / 100) : 0;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(rupees);
}

/**
 * Format ISO date string into readable format (e.g. "15 Nov 2026")
 */
export function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return isoStr;
  }
}
