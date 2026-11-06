/* Same-origin cookie-session client for the Job Beeper dashboard. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.JobBeeperAuth = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this), function () {
  'use strict';

  function createClient({ apiBase = '/api', fetchImpl = fetch, documentRef = document } = {}) {
    const base = String(apiBase || '/api').replace(/\/+$/, '');

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
      if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const csrfToken = readCookie('job_beeper_csrf');
        if (csrfToken) headers['X-CSRF-Token'] = csrfToken;
      }
      return fetchImpl(`${base}${path}`, Object.assign({}, options, {
        method,
        headers,
        credentials: 'same-origin',
      }));
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

    return { login, currentUser, logout, request, bootstrap };
  }

  return { createClient };
});
