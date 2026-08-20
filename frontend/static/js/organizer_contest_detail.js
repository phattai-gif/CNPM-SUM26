(async function () {
  function qs(key) {
    const params = new URLSearchParams(window.location.search);
    return params.get(key);
  }

  const contestId = qs('contest_id');
  const errorEl = document.getElementById('error');
  const titleEl = document.getElementById('contest-title');
  const metaEl = document.getElementById('contest-meta');
  const descEl = document.getElementById('contest-description');
  const roundsEl = document.getElementById('rounds');

  if (!contestId) {
    if (errorEl) errorEl.textContent = 'Missing contest id';
    if (titleEl) titleEl.textContent = 'Unknown contest';
    return;
  }

  const session = window.AuthSession.getSession();
  if (!session.token) {
    // not logged in — redirect to login
    window.location.href = '/auth/login';
    return;
  }

  try {
    const payload = await window.apiClient.get(`/organizer/contests/${encodeURIComponent(contestId)}`);
    if (!payload || !payload.contest) {
      if (errorEl) errorEl.textContent = payload?.message || 'Failed to load contest';
      return;
    }

    const c = payload.contest;
    if (titleEl) titleEl.textContent = c.title || 'Untitled contest';
    if (metaEl) metaEl.textContent = `Status: ${c.status || '-'} • Start: ${c.start_date || '-'} • End: ${c.end_date || '-'}`;
    if (descEl) descEl.textContent = c.description || c.rules || '';

    // render rounds and criteria
    roundsEl.innerHTML = '';
    (c.rounds || []).forEach(r => {
      const rdiv = document.createElement('div');
      rdiv.className = 'round';
      const header = document.createElement('div');
      header.innerHTML = `<strong>${r.title || 'Round'}</strong> • ${r.status || '-'} `;
      rdiv.appendChild(header);

      if (r.criteria && r.criteria.length) {
        const ul = document.createElement('ul');
        r.criteria.forEach(cr => {
          const li = document.createElement('li');
          li.textContent = `${cr.title || 'Criteria'} — weight: ${cr.weight ?? '-'} `;
          ul.appendChild(li);
        });
        rdiv.appendChild(ul);
      } else {
        const p = document.createElement('div');
        p.style = 'color:#6b7280; margin-top:6px';
        p.textContent = 'No criteria defined for this round.';
        rdiv.appendChild(p);
      }

      roundsEl.appendChild(rdiv);
    });

  } catch (err) {
    console.error(err);
    if (errorEl) errorEl.textContent = err.message || 'Lỗi khi tải dữ liệu cuộc thi';
  }
})();
