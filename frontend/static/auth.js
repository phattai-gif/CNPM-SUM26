document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const messageEl = document.getElementById('message');

  const ROLE_REDIRECTS = {
    participant: '/contests',
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

  const resolveParticipantTarget = async () => {
    try {
      const payload = await window.apiClient.get('/api/contests');
      const contests = Array.isArray(payload?.contests) ? payload.contests : [];
      const firstContest = contests.find((item) => item && item.id);
      return firstContest ? `/contest/${encodeURIComponent(firstContest.id)}` : '/contests';
    } catch (error) {
      return '/contests';
    }
  };

  const redirectToRole = async (role) => {
    const normalizedRole = (role || '').toLowerCase();
    const target = normalizedRole === 'participant'
      ? await resolveParticipantTarget()
      : (ROLE_REDIRECTS[normalizedRole] || '/');
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
          redirectToRole(data.user?.role || window.AuthSession.getSession().role);
        }
      }, 400);
    });
  }

  // Google Sign-In Integration
  const googleBtn = document.getElementById('googleBtn');
  const customGoogleBtn = document.getElementById('customGoogleBtn');

  const handleCredentialResponse = async (response) => {
    showMessage('');
    if (messageEl) {
      messageEl.textContent = 'Đang xác thực tài khoản Google...';
      messageEl.className = 'message info';
    }

    const payload = response.credential ? { id_token: response.credential } : response;
    const { ok, data } = await requestJson('/auth/google', payload);
    if (!ok) {
      showMessage(data.message || 'Đăng nhập Google thất bại.');
      return;
    }

    if (data.token) {
      window.AuthSession.setSession({
        token: data.token,
        user: data.user,
        role: data.user?.role || null
      });
    }

    showMessage('Đăng nhập Google thành công! Xử lý điều hướng...', true);
    setTimeout(() => {
      redirectToRole(data.user?.role || window.AuthSession.getSession().role);
    }, 400);
  };

  window.handleCredentialResponse = handleCredentialResponse;

  if (window.google_client_id && googleBtn) {
    let attempts = 0;
    const initGoogleGSI = () => {
      attempts++;
      if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
        google.accounts.id.initialize({
          client_id: window.google_client_id,
          callback: handleCredentialResponse
        });
        google.accounts.id.renderButton(
          googleBtn,
          { theme: "filled_blue", size: "large", width: "100%", shape: "pill", text: "continue_with" }
        );
        if (customGoogleBtn) customGoogleBtn.style.display = 'none';
      } else if (attempts < 30) {
        setTimeout(initGoogleGSI, 100);
      }
    };
    initGoogleGSI();
  }

  if (customGoogleBtn) {
    customGoogleBtn.addEventListener('click', async () => {
      if (typeof google !== 'undefined' && google.accounts && google.accounts.id && window.google_client_id) {
        google.accounts.id.prompt();
      } else {
        const userEmail = prompt('Nhập Email Google của bạn để đăng nhập nhanh:', 'user@gmail.com');
        if (userEmail && userEmail.includes('@')) {
          await handleCredentialResponse({ email: userEmail, full_name: userEmail.split('@')[0] });
        }
      }
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
      const roleSelect = document.getElementById('role');
      const roleInput = document.querySelector('input[name="role"]:checked');
      const role = roleSelect ? roleSelect.value : (roleInput ? roleInput.value : 'participant');

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
        if (data.email_verification_required) {
          window.AuthSession.clearSession();
          const verificationUrl = data.verification_token
            ? `/auth/verify-email?token=${encodeURIComponent(data.verification_token)}`
            : '/auth/verify-email';
          showMessage('Registration successful! Check your email to verify your account.', true);
          setTimeout(() => { window.location.href = verificationUrl; }, 700);
          return;
        }
        window.AuthSession.setSession({ token: data.token, user: data.user, role: data.user?.role });
        showMessage('Registration successful! Redirecting...', true);
        setTimeout(() => {
          redirectToRole(role);
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

  // Check URL parameters for tokens to auto-populate token fields
  const urlParams = new URLSearchParams(window.location.search);
  const tokenParam = urlParams.get('token');
  if (tokenParam) {
    const tokenInput = document.getElementById('token');
    if (tokenInput) {
      tokenInput.value = tokenParam;
    }
  }

  // Forgot Password Form Listener
  const forgotPasswordForm = document.getElementById('forgotPasswordForm');
  if (forgotPasswordForm) {
    forgotPasswordForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      showMessage('');
      
      const email = document.getElementById('email').value.trim();
      const demoTokenContainer = document.getElementById('demoTokenContainer');
      const demoTokenText = document.getElementById('demoTokenText');
      const goToResetLink = document.getElementById('goToResetLink');

      if (demoTokenContainer) demoTokenContainer.style.display = 'none';

      setFormLoading(forgotPasswordForm, true, 'Requesting token...');
      const { ok, data } = await requestJson('/auth/forgot-password', { email });
      setFormLoading(forgotPasswordForm, false, 'Request Reset Token');

      if (!ok) {
        showMessage(data.message || 'Failed to request reset token.');
        return;
      }

      showMessage('Password reset token generated successfully.', true);

      // Render the demo assistance block to ease copy-paste during testing/use
      if (demoTokenContainer && demoTokenText && goToResetLink) {
        demoTokenText.value = data.token;
        goToResetLink.href = `/auth/reset-password?token=${encodeURIComponent(data.token)}`;
        demoTokenContainer.style.display = 'block';
      }
    });
  }

  // Reset Password Form Listener
  const resetPasswordForm = document.getElementById('resetPasswordForm');
  if (resetPasswordForm) {
    resetPasswordForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      showMessage('');

      const token = document.getElementById('token').value.trim();
      const password = document.getElementById('password').value;
      const passwordconfirm = document.getElementById('passwordconfirm').value;

      if (!token || !password || !passwordconfirm) {
        showMessage('All fields are required.');
        return;
      }

      if (password !== passwordconfirm) {
        showMessage('Passwords do not match.');
        return;
      }

      setFormLoading(resetPasswordForm, true, 'Resetting password...');
      const { ok, data } = await requestJson('/auth/reset-password', {
        token,
        password,
        passwordconfirm
      });
      setFormLoading(resetPasswordForm, false, 'Reset Password');

      if (!ok) {
        showMessage(data.message || 'Failed to reset password.');
        return;
      }

      showMessage('Password reset successful! Redirecting to login...', true);
      resetPasswordForm.reset();
      setTimeout(() => {
        window.location.href = '/auth/login';
      }, 1500);
    });
  }

  // Email Verification Form Listener
  const verifyEmailForm = document.getElementById('verifyEmailForm');
  if (verifyEmailForm) {
    verifyEmailForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      showMessage('');

      const token = document.getElementById('token').value.trim();
      if (!token) {
        showMessage('Verification token is required.');
        return;
      }

      setFormLoading(verifyEmailForm, true, 'Verifying...');
      const { ok, data } = await requestJson('/auth/verify-email', { token });
      setFormLoading(verifyEmailForm, false, 'Verify Email');

      if (!ok) {
        showMessage(data.message || 'Verification failed.');
        return;
      }

      showMessage('Email verified successfully! Redirecting to login...', true);
      verifyEmailForm.reset();
      setTimeout(() => {
        window.location.href = '/auth/login';
      }, 1500);
    });

    // Auto-trigger verification if token is already pre-filled from URL
    if (tokenParam) {
      setTimeout(() => {
        verifyEmailForm.dispatchEvent(new Event('submit'));
      }, 200);
    }
  }

  // Request Verification Token Form Listener
  const requestVerificationForm = document.getElementById('requestVerificationForm');
  const reqMessageEl = document.getElementById('reqMessage');
  if (requestVerificationForm) {
    requestVerificationForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      
      if (reqMessageEl) {
        reqMessageEl.textContent = '';
        reqMessageEl.className = 'message';
        reqMessageEl.style.display = 'none';
      }

      const email = document.getElementById('reqEmail').value.trim();
      const demoVerifyTokenContainer = document.getElementById('demoVerifyTokenContainer');
      const demoVerifyTokenText = document.getElementById('demoVerifyTokenText');

      if (demoVerifyTokenContainer) demoVerifyTokenContainer.style.display = 'none';

      setFormLoading(requestVerificationForm, true, 'Requesting...');
      const { ok, data } = await requestJson('/auth/request-verification', { email });
      setFormLoading(requestVerificationForm, false, 'Request Token');

      if (reqMessageEl) {
        reqMessageEl.textContent = data.message || (ok ? 'Verification token generated successfully.' : 'Failed to request token.');
        reqMessageEl.className = ok ? 'message success' : 'message error';
        reqMessageEl.style.display = 'block';
      }

      if (!ok) return;

      if (demoVerifyTokenContainer && demoVerifyTokenText) {
        demoVerifyTokenText.value = data.token;
        demoVerifyTokenContainer.style.display = 'block';
      }
    });
  }
});
