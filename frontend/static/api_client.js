(function () {
  const STORAGE_KEYS = {
    TOKEN: 'authToken',
    USER: 'authUser',
    ROLE: 'authRole'
  };

  const apiClient = {
    STORAGE_KEYS,

    setSession({ token, user, role } = {}) {
      const currentUser = user || this.getSession().user || null;
      const currentRole = role || currentUser?.role || this.getSession().role || null;
      const accessToken = token || this.getSession().token || null;

      if (accessToken) {
        localStorage.setItem(STORAGE_KEYS.TOKEN, accessToken);
      } else {
        localStorage.removeItem(STORAGE_KEYS.TOKEN);
      }

      if (currentUser) {
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(currentUser));
      } else {
        localStorage.removeItem(STORAGE_KEYS.USER);
      }

      if (currentRole) {
        localStorage.setItem(STORAGE_KEYS.ROLE, currentRole);
      } else {
        localStorage.removeItem(STORAGE_KEYS.ROLE);
      }

      return { token: accessToken, user: currentUser, role: currentRole };
    },

    getSession() {
      let user = null;
      try {
        user = JSON.parse(localStorage.getItem(STORAGE_KEYS.USER) || 'null');
      } catch (error) {
        user = null;
      }

      const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
      const role = localStorage.getItem(STORAGE_KEYS.ROLE) || user?.role || null;

      // Fallback: check cookies if localStorage doesn't have token
      let finalToken = token;
      if (!finalToken && typeof document !== 'undefined' && document.cookie) {
        const match = document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith(STORAGE_KEYS.TOKEN + '='));
        if (match) {
          finalToken = decodeURIComponent(match.split('=')[1] || '');
        }
      }

      return { token: finalToken, user, role };
    },

    isAuthenticated() {
      return Boolean(this.getSession().token);
    },

    clearSession() {
      Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
    },

    logout() {
      this.clearSession();
      if (window.location.pathname !== '/auth/login') {
        window.location.href = '/auth/login';
      }
    },

    getHeaders(extraHeaders = {}) {
      const { token } = this.getSession();
      return {
        Accept: 'application/json',
        ...extraHeaders,
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      };
    },

    async request(url, options = {}) {
      const method = (options.method || 'GET').toUpperCase();
      const headers = {
        ...this.getHeaders(),
        ...(options.headers || {})
      };

      const response = await fetch(url, {
        ...options,
        method,
        headers,
        credentials: options.credentials || 'same-origin'
      });

      const contentType = response.headers.get('content-type') || '';
      let payload = null;

      if (contentType.includes('application/json')) {
        payload = await response.json().catch(() => null);
      } else {
        payload = await response.text().catch(() => '');
      }

      if (response.status === 401) {
        // Unauthorized: clear session and redirect to login
        this.logout();
        throw new Error(payload?.message || 'Unauthorized. Please login again.');
      }

      if (response.status === 403) {
        // Forbidden: also clear session and redirect
        this.logout();
        throw new Error(payload?.message || 'Forbidden. Please login with sufficient privileges.');
      }

      if (!response.ok) {
        let errMsg = payload?.message || `Request failed with status ${response.status}`;
        if (payload && payload.error) {
          try {
            const extra = typeof payload.error === 'string' ? payload.error : JSON.stringify(payload.error);
            errMsg = `${errMsg} - ${extra}`;
          } catch (e) {
            // ignore
          }
        }
        throw new Error(errMsg);
      }

      return payload;
    },

    get(url, options = {}) {
      return this.request(url, { ...options, method: 'GET' });
    },

    post(url, body = {}, options = {}) {
      const { headers = {}, ...rest } = options;
      return this.request(url, {
        ...rest,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...headers
        },
        body: JSON.stringify(body)
      });
    },

    put(url, body = {}, options = {}) {
      const { headers = {}, ...rest } = options;
      return this.request(url, {
        ...rest,
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...headers
        },
        body: JSON.stringify(body)
      });
    },

    patch(url, body = {}, options = {}) {
      const { headers = {}, ...rest } = options;
      return this.request(url, {
        ...rest,
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...headers
        },
        body: JSON.stringify(body)
      });
    },

    delete(url, options = {}) {
      return this.request(url, { ...options, method: 'DELETE' });
    }
  };

  window.apiClient = apiClient;
  window.AuthSession = {
    setSession: apiClient.setSession.bind(apiClient),
    getSession: apiClient.getSession.bind(apiClient),
    isAuthenticated: apiClient.isAuthenticated.bind(apiClient),
    clearSession: apiClient.clearSession.bind(apiClient),
    logout: apiClient.logout.bind(apiClient)
  };
})();
