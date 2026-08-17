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

      return { token, user, role };
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
        throw new Error(
        payload?.message || 'You do not have permission for this action.');
    }

      if (response.status === 403) {
        this.logout();
        throw new Error(payload?.message || 'You do not have permission for this action.');
      }

      if (!response.ok) {
        throw new Error(payload?.message || `Request failed with status ${response.status}`);
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

    uploadFormData(url, formData, options = {}) {
      const { onProgress, headers = {}, ...rest } = options;
      const { token } = this.getSession();

      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', url, true);

        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }

        Object.entries(headers).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            xhr.setRequestHeader(key, value);
          }
        });

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable && typeof onProgress === 'function') {
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress({ percent, loaded: event.loaded, total: event.total });
          }
        };

        xhr.onload = () => {
          const contentType = xhr.getResponseHeader('content-type') || '';
          let payload = null;

          if (contentType.includes('application/json')) {
            try {
              payload = JSON.parse(xhr.responseText);
            } catch (error) {
              payload = null;
            }
          } else {
            payload = xhr.responseText || '';
          }

          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(payload);
            return;
          }

          reject(new Error(payload?.message || `Request failed with status ${xhr.status}`));
        };

        xhr.onerror = () => reject(new Error('Network error while uploading the file.'));
        xhr.ontimeout = () => reject(new Error('Upload timed out.'));

        xhr.send(formData);
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
