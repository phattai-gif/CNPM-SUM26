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
    if (!form) return;
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;

    button.disabled = isLoading;
    if (button.dataset.defaultText === undefined) {
      button.dataset.defaultText = button.textContent.trim();
    }

    button.textContent = isLoading ? label : button.dataset.defaultText;
  };

  const clearFieldErrors = (form) => {
    if (!form) return;
    form.querySelectorAll('.field-error').forEach((node) => node.remove());
    form.querySelectorAll('input').forEach((input) => {
      input.classList.remove('input-error');
      input.setCustomValidity('');
    });
  };

  const showFieldErrors = (form, payload) => {
    if (!form || !payload) return;
    const fieldErrors = payload.errors && typeof payload.errors === 'object' ? payload.errors : {};

    Object.entries(fieldErrors).forEach(([fieldName, errorValue]) => {
      const input = form.querySelector(`[name="${fieldName}"]`) || form.querySelector(`#${fieldName}`);
      if (!input) return;

      const message = Array.isArray(errorValue) ? errorValue.join(', ') : String(errorValue);
      input.classList.add('input-error');
      input.setCustomValidity(message);

      const errorNode = document.createElement('div');
      errorNode.className = 'field-error';
      errorNode.textContent = message;
      errorNode.dataset.field = fieldName;

      const wrapper = input.parentElement || form;
      if (!wrapper.querySelector(`.field-error[data-field="${fieldName}"]`)) {
        wrapper.appendChild(errorNode);
      }
    });
  };

  const showMessage = (text, success = false) => {
    if (!messageEl) return;
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
      const details = error?.payload || error?.details || {};
      const payloadData = details?.data || details || {};
      return {
        ok: false,
        data: {
          message: payloadData.message || error.message || 'Invalid server response',
          errors: payloadData.errors || error.errors || null
        }
      };
    }
  };

  if (loginForm) {
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
          window.location.href = '/organizer/dashboard';
          redirectToRole(data.user?.role || window.AuthSession.getSession().role);
        }
      }, 400);
    });
  }

  if (registerForm) {
    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      clearFieldErrors(registerForm);
      showMessage('');

      const username = document.getElementById('username').value.trim();
      const email = document.getElementById('email').value.trim();
      const full_name = document.getElementById('full_name').value.trim();
      const password = document.getElementById('password').value;
      const passwordconfirm = document.getElementById('passwordconfirm').value;
      const roleInput = document.querySelector('input[name="role"]:checked');
      const role = roleInput ? roleInput.value : 'participant';

      setFormLoading(registerForm, true, 'Creating account...');
      const { ok, data } = await requestJson('/auth/signup', {
        username,
        email,
        full_name,
        password,
        passwordconfirm,
        role
      });
      setFormLoading(registerForm, false, 'Register');

      if (!ok) {
        showMessage(data.message || 'Registration failed. Please check your input.');
        showFieldErrors(registerForm, data);
        return;
      }

      // If backend returned token, set session and redirect appropriately
      if (data.token) {
        window.AuthSession.setSession({ token: data.token, user: data.user, role: data.user?.role });
        showMessage('Registration successful! Redirecting...', true);
        setTimeout(() => {
          if (role === 'organizer') {
            window.location.href = '/organizer/dashboard';
          } else {
            window.location.href = '/';
          }
        }, 300);
        return;
      }

      showMessage('Registration successful! You can now login.', true);
      showMessage('Registration successful! Redirecting to login...', true);
      registerForm.reset();
      setTimeout(() => {
        window.location.href = '/auth/login';
      }, 900);
    });
  }
});
