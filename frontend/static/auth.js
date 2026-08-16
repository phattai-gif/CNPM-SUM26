document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const messageEl = document.getElementById('message');

  const showMessage = (text, success = false) => {
    if (!messageEl) {
      return;
    }
    messageEl.textContent = text;
    messageEl.className = success ? 'message success' : 'message error';
  };

  const requestJson = async (url, payload) => {
    try {
      const data = await window.apiClient.post(url, payload);
      return { ok: true, data };
    } catch (error) {
      return {
        ok: false,
        data: { message: error.message || 'Invalid server response' }
      };
    }
  };

  if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;

      const { ok, data } = await requestJson('/auth/login', { username, password });
      if (!ok) {
        showMessage(data.message || 'Login failed. Please check your credentials.');
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
        }
      }, 300);
    });
  }

  if (registerForm) {
    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const username = document.getElementById('username').value.trim();
      const email = document.getElementById('email').value.trim();
      const full_name = document.getElementById('full_name').value.trim();
      const password = document.getElementById('password').value;
      const passwordconfirm = document.getElementById('passwordconfirm').value;
      const roleInput = document.querySelector('input[name="role"]:checked');
      const role = roleInput ? roleInput.value : 'participant';

      const { ok, data } = await requestJson('/auth/signup', {
        username,
        email,
        full_name,
        password,
        passwordconfirm,
        role
      });

      if (!ok) {
        showMessage(data.message || 'Registration failed. Please check your input.');
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
      registerForm.reset();
    });
  }
});
