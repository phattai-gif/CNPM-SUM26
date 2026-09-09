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

  async function loadWinnerCandidates(roundId, target) {
    try {
      const data = await window.apiClient.get(`/organizer/contests/${encodeURIComponent(contestId)}/rounds/${roundId}/winners`);
      const rows = data.winner_candidates || data.leaderboard || [];
      if (!rows.length) {
        target.innerHTML = '<p class="text-muted mb-0">No rankings available.</p>';
        return;
      }
      target.innerHTML = `
        <div class="table-responsive">
          <table class="table table-dark table-sm align-middle mb-0">
            <thead><tr><th>Hạng</th><th>Bài dự thi</th><th>Thí sinh</th><th>Điểm</th><th>Trạng thái</th><th></th></tr></thead>
            <tbody>${rows.map(row => `
              <tr>
                <td>${row.rank ?? '-'}</td>
                <td>${row.title || `#${row.submission_id}`}</td>
                <td>${row.author_name || '-'}</td>
                <td>${row.final_score ?? '-'}</td>
                <td>${row.status || '-'}</td>
                <td>
                  <button class="btn btn-sm btn-warning approve-winner" data-submission-id="${row.submission_id}">Approve Winner</button>
                  <button class="btn btn-sm btn-outline-danger reject-winner" data-submission-id="${row.submission_id}">Reject</button>
                </td>
              </tr>`).join('')}</tbody>
          </table>
        </div>`;

      target.querySelectorAll('.approve-winner').forEach(button => button.addEventListener('click', async () => {
        const awardTitle = window.prompt('Tên giải thưởng:', 'Winner');
        if (!awardTitle) return;
        await decideWinner(roundId, button.dataset.submissionId, 'approve', { award_title: awardTitle });
        await loadWinnerCandidates(roundId, target);
      }));
      target.querySelectorAll('.reject-winner').forEach(button => button.addEventListener('click', async () => {
        const reason = window.prompt('Lý do từ chối winner:');
        if (!reason) return;
        await decideWinner(roundId, button.dataset.submissionId, 'reject', { reason });
        await loadWinnerCandidates(roundId, target);
      }));
    } catch (err) {
      target.innerHTML = `<p class="text-danger mb-0">${err.message || 'Unable to load rankings.'}</p>`;
    }
  }

  async function decideWinner(roundId, submissionId, decision, payload) {
    await window.apiClient.patch(
      `/organizer/contests/${encodeURIComponent(contestId)}/rounds/${roundId}/winners/${submissionId}`,
      { decision, ...payload },
    );
  }

  async function finalizeRound(roundId, button, resultsEl) {
    if (!window.confirm('Chốt vòng thi sẽ khóa điểm. Bạn có chắc chắn muốn tiếp tục?')) return;
    button.disabled = true;
    try {
      await window.apiClient.post(`/organizer/contests/${encodeURIComponent(contestId)}/rounds/${roundId}/finalize`);
      button.textContent = 'Round Finalized';
      resultsEl.hidden = false;
      await loadWinnerCandidates(roundId, resultsEl);
    } catch (err) {
      button.disabled = false;
      window.alert(err.message || 'Không thể chốt vòng thi.');
    }
  }

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

      const actions = document.createElement('div');
      actions.className = 'd-flex gap-2 flex-wrap mt-2';
      const finalizeButton = document.createElement('button');
      finalizeButton.className = 'btn btn-warning btn-sm';
      finalizeButton.textContent = String(r.status).toLowerCase() === 'finalized' ? 'Round Finalized' : 'Finalize Round';
      finalizeButton.disabled = String(r.status).toLowerCase() === 'finalized';
      const resultsButton = document.createElement('button');
      resultsButton.className = 'btn btn-outline-light btn-sm';
      resultsButton.textContent = 'View Rankings / Winners';
      actions.append(finalizeButton, resultsButton);
      rdiv.appendChild(actions);

      const resultsEl = document.createElement('div');
      resultsEl.className = 'mt-3';
      resultsEl.hidden = true;
      rdiv.appendChild(resultsEl);
      finalizeButton.addEventListener('click', () => finalizeRound(r.id, finalizeButton, resultsEl));
      resultsButton.addEventListener('click', async () => {
        resultsEl.hidden = !resultsEl.hidden;
        if (!resultsEl.hidden) await loadWinnerCandidates(r.id, resultsEl);
      });

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
