/* Same-origin cookie-session client for the Job Beeper dashboard. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.JobBeeperAuth = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this), function () {
  'use strict';

  function resolveApiBase(apiBase = '/api', locationRef = null) {
    const candidate = String(apiBase || '/api').trim() || '/api';
    const origin = locationRef && locationRef.origin;
    if (!origin) {
      if (/^(?:[a-z][a-z0-9+.-]*:)?\/\//i.test(candidate)) return '/api';
      return candidate.replace(/\/+$/, '') || '/api';
    }
    try {
      const resolved = new URL(candidate, origin);
      if (resolved.origin !== origin || resolved.username || resolved.password) return '/api';
      return resolved.pathname.replace(/\/+$/, '') || '/api';
    } catch (_error) {
      return '/api';
    }
  }

  function createClient({
    apiBase = '/api',
    fetchImpl = fetch,
    documentRef = document,
    locationRef = (typeof window !== 'undefined' ? window.location : null),
  } = {}) {
    const base = resolveApiBase(apiBase, locationRef);

    function readCookie(name) {
      const prefix = `${name}=`;
      const entry = String(documentRef.cookie || '').split(';').map(value => value.trim()).find(value => value.startsWith(prefix));
      if (!entry) return '';
      const value = entry.slice(prefix.length);
      try { return decodeURIComponent(value); } catch (_error) { return value; }
    }

    function request(path, options = {}) {
      const method = String(options.method || 'GET').toUpperCase();
      const headers = Object.assign({}, options.headers || {});
      let body = options.body;
      const isJsonBody = Array.isArray(body) || (
        body !== null
        && typeof body === 'object'
        && (Object.getPrototypeOf(body) === Object.prototype || Object.getPrototypeOf(body) === null)
      );
      if (isJsonBody) {
        body = JSON.stringify(body);
        const hasContentType = Object.keys(headers).some(name => name.toLowerCase() === 'content-type');
        if (!hasContentType) headers['Content-Type'] = 'application/json';
      }
      if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const csrfToken = readCookie('job_beeper_csrf');
        if (csrfToken) headers['X-CSRF-Token'] = csrfToken;
      }
      return fetchImpl(`${base}${path}`, Object.assign({}, options, {
        method,
        headers,
        body,
        credentials: 'same-origin',
      }));
    }

    function formatErrorDetail(detail) {
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail.map(item => {
          if (typeof item === 'string') return item;
          if (!item || typeof item !== 'object') return '';
          const location = Array.isArray(item.loc)
            ? item.loc.filter(part => part !== 'body').join('.')
            : '';
          const message = typeof item.msg === 'string' ? item.msg
            : typeof item.message === 'string' ? item.message : '';
          return [location, message].filter(Boolean).join(': ');
        }).filter(Boolean).join('; ');
      }
      if (detail && typeof detail === 'object') {
        if (typeof detail.message === 'string') return detail.message;
        try { return JSON.stringify(detail); } catch (_error) { return ''; }
      }
      return '';
    }

    function login(email, password) {
      return fetchImpl(`${base}/auth/login`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
    }

    function currentUser() {
      return request('/auth/me', { cache: 'no-store' });
    }

    function logout() {
      return request('/auth/logout', { method: 'POST' });
    }

    async function bootstrap({ onAdmin, onUser, onLogin, onError } = {}) {
      try {
        const response = await currentUser();
        if (response.status === 401) {
          if (typeof onLogin === 'function') onLogin();
          return { access: 'login' };
        }
        if (!response.ok) throw new Error(`Session verification failed (${response.status}).`);
        const payload = await response.json();
        const user = payload && payload.user;
        if (!user || !Number.isInteger(user.id) || !['admin', 'user'].includes(user.role)) {
          throw new Error('Session response was invalid.');
        }
        if (user.role === 'admin') {
          if (typeof onAdmin === 'function') onAdmin(user);
          return { access: 'admin', user };
        }
        if (typeof onUser === 'function') onUser(user);
        return { access: 'user', user };
      } catch (error) {
        if (typeof onError === 'function') onError(error);
        return { access: 'error', error };
      }
    }

    return { login, currentUser, logout, request, bootstrap, formatErrorDetail };
  }

  return { createClient, resolveApiBase };
});
