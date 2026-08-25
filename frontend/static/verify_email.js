/**
 * verify_email.js
 * Handles the Email Verification page logic:
 *
 *  Section 1 – Verify token form (#verifyEmailForm)
 *    - Reads ?token= from URL and pre-fills the token field
 *    - POSTs token to /auth/verify-email
 *    - Redirects to /auth/login on success
 *
 *  Section 2 – Request new token form (#requestVerificationForm)
 *    - POSTs email to /auth/request-verification
 *    - Shows demo token box if backend returns the token directly
 */

(function () {
  'use strict';

  /* ── DOM refs – verify form ───────────────────────────────── */
  const verifyForm      = document.getElementById('verifyEmailForm');
  const tokenInput      = document.getElementById('token');
  const alertBox        = document.getElementById('message');
  const msgIcon         = document.getElementById('msgIcon');
  const msgText         = document.getElementById('msgText');
  const verifySubmitBtn = document.getElementById('verifySubmitBtn');

  /* ── DOM refs – request-new-token form ────────────────────── */
  const requestForm     = document.getElementById('requestVerificationForm');
  const reqEmailInput   = document.getElementById('reqEmail');
  const reqAlertBox     = document.getElementById('reqMessage');
  const reqMsgIcon      = document.getElementById('reqMsgIcon');
  const reqMsgText      = document.getElementById('reqMsgText');
  const reqSubmitBtn    = document.getElementById('reqSubmitBtn');
  const demoContainer   = document.getElementById('demoVerifyTokenContainer');
  const demoTokenText   = document.getElementById('demoVerifyTokenText');

  /* ══════════════════════════════════════════════════════════ *
   *  SHARED HELPERS                                            *
   * ══════════════════════════════════════════════════════════ */

  function showAlert(box, iconEl, textEl, text, isError) {
    if (!box) return;
    if (iconEl) iconEl.textContent = isError ? '⚠️' : '✅';
    if (textEl) textEl.textContent = text;
    box.className = 'rp-alert ' + (isError ? 'error' : 'success');
  }

  function clearAlert(box, iconEl, textEl) {
    if (!box) return;
    box.className = 'rp-alert';
    if (iconEl) iconEl.textContent = '';
    if (textEl) textEl.textContent = '';
  }

  function setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle('loading', loading);
  }

  /* ══════════════════════════════════════════════════════════ *
   *  SECTION 1 — VERIFY EMAIL TOKEN                           *
   * ══════════════════════════════════════════════════════════ */

  /** Pre-fill token from ?token= URL param */
  function prefillToken() {
    if (!tokenInput) return;
    const params = new URLSearchParams(window.location.search);
    const token  = params.get('token');
    if (token && !tokenInput.value.trim()) {
      tokenInput.value = token;
    }
  }

  async function verifyEmailToken(token) {
    try {
      const data = await window.apiClient.post('/auth/verify-email', { token });
      return { ok: true, data };
    } catch (error) {
      const details     = error?.payload || error?.details || {};
      const payloadData = details?.data  || details         || {};
      return {
        ok: false,
        data: { message: payloadData.message || error.message || 'Server error' },
      };
    }
  }

  function mapVerifyError(raw) {
    const lower = (raw || '').toLowerCase();
    if (lower.includes('expired'))
      return 'Your verification token has expired. Please request a new one below.';
    if (lower.includes('invalid token type'))
      return 'This link is not a valid email verification link.';
    if (lower.includes('invalid') || lower.includes('token'))
      return 'Your verification token is invalid. Please request a new one below.';
    if (lower.includes('user not found'))
      return 'No account found for this token. Please register again.';
    return raw || 'Verification failed. Please try again.';
  }

  async function handleVerifySubmit(event) {
    event.preventDefault();
    clearAlert(alertBox, msgIcon, msgText);

    const token = tokenInput ? tokenInput.value.trim() : '';
    if (!token) {
      showAlert(alertBox, msgIcon, msgText, 'Please enter or paste your verification token.', true);
      return;
    }

    setLoading(verifySubmitBtn, true);
    const { ok, data } = await verifyEmailToken(token);
    setLoading(verifySubmitBtn, false);

    if (ok) {
      showAlert(
        alertBox, msgIcon, msgText,
        data.message || 'Email verified successfully! Redirecting to login…',
        false,
      );
      setTimeout(() => { window.location.href = '/auth/login'; }, 2200);
    } else {
      showAlert(alertBox, msgIcon, msgText, mapVerifyError(data.message), true);
    }
  }

  /* ══════════════════════════════════════════════════════════ *
   *  SECTION 2 — REQUEST NEW VERIFICATION TOKEN               *
   * ══════════════════════════════════════════════════════════ */

  function showDemoToken(token) {
    if (!demoContainer || !demoTokenText) return;
    demoTokenText.value = token;
    demoContainer.style.display = 'block';
    demoTokenText.addEventListener('click', () => demoTokenText.select(), { once: true });
  }

  async function requestVerificationToken(email) {
    try {
      const data = await window.apiClient.post('/auth/request-verification', { email });
      return { ok: true, data };
    } catch (error) {
      const details     = error?.payload || error?.details || {};
      const payloadData = details?.data  || details         || {};
      return {
        ok: false,
        data: { message: payloadData.message || error.message || 'Server error' },
      };
    }
  }

  function mapRequestError(raw) {
    const lower = (raw || '').toLowerCase();
    if (lower.includes('email does not exist') || lower.includes('not found'))
      return 'This email address is not registered in our system.';
    if (lower.includes('email is required'))
      return 'Please enter your email address.';
    return raw || 'Failed to send verification token. Please try again.';
  }

  async function handleRequestSubmit(event) {
    event.preventDefault();
    clearAlert(reqAlertBox, reqMsgIcon, reqMsgText);

    const email = reqEmailInput ? reqEmailInput.value.trim() : '';
    if (!email) {
      showAlert(reqAlertBox, reqMsgIcon, reqMsgText, 'Please enter your email address.', true);
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showAlert(reqAlertBox, reqMsgIcon, reqMsgText, 'Please enter a valid email address.', true);
      return;
    }

    setLoading(reqSubmitBtn, true);
    const { ok, data } = await requestVerificationToken(email);
    setLoading(reqSubmitBtn, false);

    if (ok) {
      showAlert(
        reqAlertBox, reqMsgIcon, reqMsgText,
        data.message || 'Verification token generated! Copy it and paste it above.',
        false,
      );
      if (data.token) showDemoToken(data.token);
    } else {
      showAlert(reqAlertBox, reqMsgIcon, reqMsgText, mapRequestError(data.message), true);
    }
  }

  /* ══════════════════════════════════════════════════════════ *
   *  BOOTSTRAP                                                 *
   * ══════════════════════════════════════════════════════════ */

  prefillToken();
  if (verifyForm)  verifyForm.addEventListener('submit', handleVerifySubmit);
  if (requestForm) requestForm.addEventListener('submit', handleRequestSubmit);
})();
