/**
 * forgot_password.js
 * Handles the Forgot Password page logic:
 *  - Form submission to request a password-reset token
 *  - Displays the token in a demo helper box for easy copy-paste
 *  - Builds the "Proceed to Reset Password" link with ?token=... pre-filled
 */

(function () {
  'use strict';

  /* ── DOM refs ─────────────────────────────────────────────── */
  const form          = document.getElementById('forgotPasswordForm');
  const emailInput    = document.getElementById('email');
  const alertBox      = document.getElementById('message');
  const msgIcon       = document.getElementById('msgIcon');
  const msgText       = document.getElementById('msgText');
  const demoContainer = document.getElementById('demoTokenContainer');
  const demoTokenText = document.getElementById('demoTokenText');
  const goToResetLink = document.getElementById('goToResetLink');
  const submitBtn     = document.getElementById('submitBtn');

  /* ── Helpers ──────────────────────────────────────────────── */
  function showAlert(text, isError = false) {
    if (!alertBox) return;
    if (msgIcon)  msgIcon.textContent  = isError ? '⚠️' : '✅';
    if (msgText)  msgText.textContent  = text;
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

  /* ── API call ─────────────────────────────────────────────── */
  async function requestReset(email) {
    try {
      const data = await window.apiClient.post('/auth/forgot-password', { email });
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

  /* ── Map errors → user-friendly strings ─────────────────── */
  function mapError(raw) {
    const lower = (raw || '').toLowerCase();
    if (lower.includes('email does not exist') || lower.includes('not found'))
      return 'This email address is not registered in our system.';
    if (lower.includes('email is required'))
      return 'Please enter your email address.';
    return raw || 'Failed to send reset token. Please try again.';
  }

  /* ── Token demo box ──────────────────────────────────────── */
  function showDemoToken(token) {
    if (!demoContainer || !demoTokenText || !goToResetLink) return;
    demoTokenText.value = token;
    goToResetLink.href  = `/auth/reset-password?token=${encodeURIComponent(token)}`;
    demoContainer.style.display = 'block';
    demoTokenText.addEventListener('click', () => demoTokenText.select(), { once: true });
  }

  /* ── Form submit handler ─────────────────────────────────── */
  async function handleSubmit(event) {
    event.preventDefault();
    clearAlert();

    const email = emailInput ? emailInput.value.trim() : '';

    if (!email) {
      showAlert('Please enter your email address.', true);
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showAlert('Please enter a valid email address.', true);
      return;
    }

    setLoading(true);
    const { ok, data } = await requestReset(email);
    setLoading(false);

    if (ok) {
      showAlert(data.message || 'Reset token generated! Copy it below.', false);
      if (data.token) showDemoToken(data.token);
    } else {
      showAlert(mapError(data.message), true);
    }
  }

  /* ── Bootstrap ───────────────────────────────────────────── */
  if (form) form.addEventListener('submit', handleSubmit);
})();
