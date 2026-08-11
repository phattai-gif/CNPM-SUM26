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
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({ message: 'Invalid server response' }));
    return { ok: response.ok, data };
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
        localStorage.setItem('authToken', data.token);
      }
      showMessage('Login successful! Welcome, ' + (data.user?.username || username), true);
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

      const { ok, data } = await requestJson('/auth/signup', {
        username,
        email,
        full_name,
        password,
        passwordconfirm,
      });

      if (!ok) {
        showMessage(data.message || 'Registration failed. Please check your input.');
        return;
      }

      showMessage('Registration successful! You can now login.', true);
      registerForm.reset();
    });
  }
});
