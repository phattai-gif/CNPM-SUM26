document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const messageEl = document.getElementById('message');

  const ROLE_REDIRECTS = {
    participant: '/auth/submit',
    organizer: '/organizer/dashboard',
    judge: '/judge/1',
    admin: '/organizer/dashboard'
  };

  const setFormLoading = (form, isLoading, label) => {
    if (!form) {
      return;
    }

    const button = form.querySelector('button[type="submit"]');
    if (!button) {
      return;
    }

    button.disabled = isLoading;
    button.textContent = isLoading ? label : button.dataset.defaultText || label.replace(/\.\.\./g, '');
  };

  const setButtonDefaultText = (form) => {
    const button = form?.querySelector('button[type="submit"]');
    if (button && !button.dataset.defaultText) {
      button.dataset.defaultText = button.textContent.trim();
    }
  };

  const clearFieldErrors = (form) => {
    if (!form) {
      return;
    }

    form.querySelectorAll('.field-error').forEach((node) => node.remove());
    form.querySelectorAll('input').forEach((input) => {
      input.classList.remove('input-error');
      input.setCustomValidity('');
    });
  };

  const showFieldErrors = (form, payload) => {
    if (!form || !payload) {
      return;
    }

    const fieldErrors = payload.errors && typeof payload.errors === 'object' ? payload.errors : {};
    const entries = Object.entries(fieldErrors);

    entries.forEach(([fieldName, errorValue]) => {
      const input = form.querySelector(`[name="${fieldName}"]`) || form.querySelector(`#${fieldName}`);
      if (!input) {
        return;
      }

      const normalizedMessage = Array.isArray(errorValue) ? errorValue.join(', ') : String(errorValue);
      input.classList.add('input-error');
      input.setCustomValidity(normalizedMessage);

      const errorNode = document.createElement('div');
      errorNode.className = 'field-error';
      errorNode.textContent = normalizedMessage;

      const parent = input.parentElement || form;
      if (parent && !parent.querySelector(`.field-error[data-field="${fieldName}"]`)) {
        errorNode.dataset.field = fieldName;
        parent.appendChild(errorNode);
      }
    });
  };

  const showMessage = (text, success = false) => {
    if (!messageEl) {
      return;
    }
    messageEl.textContent = text;
    messageEl.className = success ? 'message success' : 'message error';
  };

  const redirectToRole = (role) => {
    const target = ROLE_REDIRECTS[(role || '').toLowerCase()] || '/';
    window.location.href = target;
  };

  const requestJson = async (url, payload) => {
    try {
      const data = await window.apiClient.post(url, payload);
      return { ok: true, data };
    } catch (error) {
      const details = error?.payload || error?.details || error?.response || {};
      const responseData = details?.data || details || {};

      return {
        ok: false,
        data: {
          message: responseData.message || error.message || 'Invalid server response',
          errors: responseData.errors || error.errors || null
        },
        error
      };
    }
  };

  if (loginForm) {
    setButtonDefaultText(loginForm);
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      clearFieldErrors(loginForm);
      showMessage('');

      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;
      setFormLoading(loginForm, true, 'Logging in...');

      const { ok, data } = await requestJson('/auth/login', { username, password });
      setFormLoading(loginForm, false, 'Login');

      if (!ok) {
        showMessage(data.message || 'Login failed. Please check your credentials.');
        showFieldErrors(loginForm, data);
        return;
      }

      if (data.token) {
        window.AuthSession.setSession({
          token: data.token,
          user: data.user,
          role: data.user?.role || null
        });
      }

      showMessage('Login successful! Welcome, ' + (data.user?.username || username), true);
      setTimeout(() => {
        if (window.location.pathname === '/auth/login') {
          redirectToRole(data.user?.role || window.AuthSession.getSession().role);
        }
      }, 400);
    });
  }

  if (registerForm) {
    setButtonDefaultText(registerForm);
    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      clearFieldErrors(registerForm);
      showMessage('');

      const username = document.getElementById('username').value.trim();
      const email = document.getElementById('email').value.trim();
      const full_name = document.getElementById('full_name').value.trim();
      const password = document.getElementById('password').value;
      const passwordconfirm = document.getElementById('passwordconfirm').value;
      setFormLoading(registerForm, true, 'Creating account...');

      const { ok, data } = await requestJson('/auth/signup', {
        username,
        email,
        full_name,
        password,
        passwordconfirm,
      });
      setFormLoading(registerForm, false, 'Register');

      if (!ok) {
        showMessage(data.message || 'Registration failed. Please check your input.');
        showFieldErrors(registerForm, data);
        return;
      }

      showMessage('Registration successful! Redirecting to login...', true);
      registerForm.reset();
      setTimeout(() => {
        window.location.href = '/auth/login';
      }, 900);
    });
  }
});
