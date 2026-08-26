/**
 * reset_password.js
 * Handles the Reset Password page logic:
 *  - Reads ?token= from URL and pre-fills the token field
 *  - Validates that the two passwords match before submitting
 *  - POSTs { token, password, passwordconfirm } to /auth/reset-password
 *  - Redirects to /auth/login on success
 *  - Maps all known backend error messages to user-friendly strings
 */

(function () {
  'use strict';

  /* ── DOM refs ─────────────────────────────────────────────── */
  const form          = document.getElementById('resetPasswordForm');
  const tokenInput    = document.getElementById('token');
  const passwordInput = document.getElementById('password');
  const confirmInput  = document.getElementById('passwordconfirm');
  const alertBox      = document.getElementById('message');
  const msgIcon       = document.getElementById('msgIcon');
  const msgText       = document.getElementById('msgText');
  const submitBtn     = document.getElementById('submitBtn');

  /* ── Helpers ──────────────────────────────────────────────── */
  function showAlert(text, isError = false) {
    if (!alertBox) return;
    if (msgIcon) msgIcon.textContent = isError ? '⚠️' : '✅';
    if (msgText) msgText.textContent = text;
    alertBox.className = 'rp-alert ' + (isError ? 'error' : 'success');
  }

  function clearAlert() {
    if (!alertBox) return;
    alertBox.className = 'rp-alert';
    if (msgText) msgText.textContent = '';
    if (msgIcon) msgIcon.textContent = '';
  }

  function setLoading(loading) {
    if (!submitBtn) return;
    submitBtn.disabled = loading;
    submitBtn.classList.toggle('loading', loading);
  }

  /* ── Pre-fill token from ?token= URL param ───────────────── */
  function prefillToken() {
    if (!tokenInput) return;
    const params = new URLSearchParams(window.location.search);
    const token  = params.get('token');
    if (token && !tokenInput.value.trim()) {
      tokenInput.value = token;
    }
  }

  /* ── API call ─────────────────────────────────────────────── */
  async function callResetPassword(token, password, passwordconfirm) {
    try {
      const data = await window.apiClient.post('/auth/reset-password', {
        token,
        password,
        passwordconfirm,
      });
      return { ok: true, data };
    } catch (error) {
      const details     = error?.payload || error?.details || {};
      const payloadData = details?.data  || details         || {};
      return {
        ok: false,
        data: {
          message: payloadData.message || error.message || 'Server error',
        },
      };
    }
  }

  /* ── Map backend errors → user-friendly messages ─────────── */
  function mapError(raw) {
    const lower = (raw || '').toLowerCase();
    if (lower.includes('expired'))
      return 'Your reset token has expired. Please go back and request a new one.';
    if (lower.includes('invalid token type'))
      return 'This link is not a valid password reset link.';
    if (lower.includes('invalid token') || lower.includes('invalidtoken'))
      return 'Your reset token is invalid or malformed. Please request a new one.';
    if (lower.includes('passwords do not match'))
      return 'Passwords do not match. Please re-enter them.';
    if (lower.includes('user not found'))
      return 'No account is associated with this token. Please sign up again.';
    if (lower.includes('all fields'))
      return 'Please fill in all fields before submitting.';
    return raw || 'Failed to reset password. Please try again.';
  }

  /* ── Form submit handler ─────────────────────────────────── */
  async function handleSubmit(event) {
    event.preventDefault();
    clearAlert();

    const token    = tokenInput    ? tokenInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value      : '';
    const confirm  = confirmInput  ? confirmInput.value       : '';

    /* Client-side validation */
    if (!token) {
      showAlert('Please enter or paste your reset token.', true);
      return;
    }
    if (!password) {
      showAlert('Please enter a new password.', true);
      return;
    }
    if (password.length < 8) {
      showAlert('Password must be at least 8 characters long.', true);
      return;
    }
    if (password !== confirm) {
      showAlert('Passwords do not match. Please re-enter them.', true);
      return;
    }

    setLoading(true);
    const { ok, data } = await callResetPassword(token, password, confirm);
    setLoading(false);

    if (ok) {
      showAlert(data.message || 'Password reset successfully! Redirecting to login…', false);
      setTimeout(() => { window.location.href = '/auth/login'; }, 2200);
    } else {
      showAlert(mapError(data.message), true);
    }
  }

  /* ── Bootstrap ───────────────────────────────────────────── */
  prefillToken();
  if (form) form.addEventListener('submit', handleSubmit);
})();
