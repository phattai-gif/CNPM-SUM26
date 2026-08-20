const dashboardState = {
  contests: [],
  judges: [],
  assignments: [],
  selectedContestId: '',
  selectedRoundId: ''
};

function requireDashboardSession() {
  const session = window.AuthSession.getSession();
  if (!session.token) {
    window.location.href = '/auth/login';
    return null;
  }
  return session;
}

function showToast(message, isError = false) {
  const toast = document.getElementById('dashboard-toast');
  if (!toast) return;
  toast.textContent = message;
  toast.style.background = isError ? '#b91c1c' : '#111827';
  toast.style.display = 'block';
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    toast.style.display = 'none';
  }, 2600);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

async function fetchContests() {
  if (!requireDashboardSession()) return { contests: [] };
  return await window.apiClient.get('/organizer/contests');
}

async function fetchMetrics() {
  const root = document.getElementById('dashboard');
  if (!root || !requireDashboardSession()) return null;
  return await window.apiClient.get(`/organizer/dashboard/metrics?organizer_id=${encodeURIComponent(root.dataset.organizerId)}`);
}

async function fetchAvailableJudges() {
  if (!requireDashboardSession()) return { judges: [] };
  return await window.apiClient.get('/organizer/judges');
}

async function fetchRoundAssignments(contestId, roundId) {
  if (!contestId || !roundId || !requireDashboardSession()) {
    return { assignments: [] };
  }
  return await window.apiClient.get(`/organizer/contests/${encodeURIComponent(contestId)}/rounds/${encodeURIComponent(roundId)}/judges`);
}

function getSelectedContest() {
  return dashboardState.contests.find((contest) => String(contest.id) === String(dashboardState.selectedContestId)) || null;
}

function getSelectedRound() {
  const contest = getSelectedContest();
  if (!contest) return null;
  return (contest.rounds || []).find((round) => String(round.id) === String(dashboardState.selectedRoundId)) || null;
}

function renderContests(contests) {
  const list = document.getElementById('contests-list');
  if (!list) return;
  list.innerHTML = '';

  if (!contests || contests.length === 0) {
    list.innerHTML = '<p class="empty-state">You do not have any contests yet.</p>';
    return;
  }

  const table = document.createElement('table');
  table.innerHTML = `
    <thead>
      <tr>
        <th>ID</th>
        <th>Title</th>
        <th>Status</th>
        <th>Rounds</th>
        <th>Start</th>
        <th>End</th>
        <th>Actions</th>
      </tr>
    </thead>
  `;

  const tbody = document.createElement('tbody');
  contests.forEach((contest) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(contest.id)}</td>
      <td>${escapeHtml(contest.title)}</td>
      <td>${escapeHtml(contest.status || '-')}</td>
      <td>${escapeHtml((contest.rounds || []).length)}</td>
      <td>${escapeHtml(contest.start_date || '-')}</td>
      <td>${escapeHtml(contest.end_date || '-')}</td>
      <td>
        <a href="/organizer/create-contest?contest_id=${encodeURIComponent(contest.id)}" class="btn" style="display:inline-block;padding:6px 10px;font-size:0.9rem;">Edit</a>
        <a href="/organizer/contest-detail?contest_id=${encodeURIComponent(contest.id)}" style="margin-left:8px;display:inline-block;padding:6px 10px;font-size:0.9rem;text-decoration:none;border-radius:8px;border:1px solid #e5e7eb;background:#fff;color:#374151;">View</a>
      </td>
    `;
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  list.appendChild(table);
}

function renderMetrics(metrics) {
  if (!metrics) return;
  const subs = document.getElementById('overview-submissions');
  const judges = document.getElementById('overview-judges');
  if (subs) subs.textContent = (metrics.submissions ?? metrics.submissions_count ?? '-');
  if (judges) judges.textContent = (metrics.judges ?? metrics.judges_count ?? '-');
}

function renderContestOptions() {
  const select = document.getElementById('contest-select');
  if (!select) return;

  if (!dashboardState.contests.length) {
    select.innerHTML = '<option value="">Không có contest</option>';
    return;
  }

  if (!dashboardState.selectedContestId) {
    dashboardState.selectedContestId = String(dashboardState.contests[0].id);
  }

  select.innerHTML = dashboardState.contests.map((contest) => {
    const isSelected = String(contest.id) === String(dashboardState.selectedContestId) ? 'selected' : '';
    return `<option value="${escapeHtml(contest.id)}" ${isSelected}>#${escapeHtml(contest.id)} - ${escapeHtml(contest.title)}</option>`;
  }).join('');
}

function renderRoundOptions() {
  const select = document.getElementById('round-select');
  const summary = document.getElementById('judge-manager-summary');
  const contest = getSelectedContest();
  if (!select) return;

  if (!contest || !(contest.rounds || []).length) {
    dashboardState.selectedRoundId = '';
    select.innerHTML = '<option value="">Contest chưa có round</option>';
    if (summary) summary.textContent = 'Contest này chưa có round để phân công judge.';
    renderAssignments([]);
    return;
  }

  const rounds = contest.rounds || [];
  const validCurrent = rounds.some((round) => String(round.id) === String(dashboardState.selectedRoundId));
  if (!validCurrent) {
    dashboardState.selectedRoundId = String(rounds[0].id);
  }

  select.innerHTML = rounds.map((round) => {
    const isSelected = String(round.id) === String(dashboardState.selectedRoundId) ? 'selected' : '';
    return `<option value="${escapeHtml(round.id)}" ${isSelected}>Round ${escapeHtml(round.round_number || '?')} - ${escapeHtml(round.title)}</option>`;
  }).join('');

  const selectedRound = getSelectedRound();
  if (summary && selectedRound) {
    summary.textContent = `Đang phân công cho Round ${selectedRound.round_number || '-'} của contest #${contest.id}.`;
  }
}

function renderAvailableJudges() {
  const container = document.getElementById('available-judges');
  if (!container) return;

  if (!dashboardState.judges.length) {
    container.innerHTML = '<p class="empty-state">Không có judge khả dụng.</p>';
    return;
  }

  const assignedJudgeIds = new Set(dashboardState.assignments.map((assignment) => String(assignment.judge_id)));
  container.innerHTML = dashboardState.judges.map((judge) => {
    const stats = judge.stats || {};
    const disabled = assignedJudgeIds.has(String(judge.id)) ? 'disabled' : '';
    const checkedLabel = assignedJudgeIds.has(String(judge.id)) ? '<span class="stat-pill" style="background:#dcfce7;color:#166534;">Đã gán round này</span>' : '';
    return `
      <label class="judge-card">
        <div class="judge-card-top">
          <div>
            <div style="font-weight:700;color:#111827;">${escapeHtml(judge.full_name || judge.username || `Judge #${judge.id}`)}</div>
            <div class="muted">@${escapeHtml(judge.username || 'unknown')} | ${escapeHtml(judge.email || 'No email')}</div>
          </div>
          <input type="checkbox" class="judge-select" value="${escapeHtml(judge.id)}" ${disabled} />
        </div>
        <div class="judge-stats">
          <span class="stat-pill">${escapeHtml(stats.assigned_rounds ?? 0)} round</span>
          <span class="stat-pill">${escapeHtml(stats.assigned_submissions ?? 0)} bài</span>
          <span class="stat-pill">${escapeHtml(stats.total_assignments ?? 0)} assignment</span>
          ${checkedLabel}
        </div>
      </label>
    `;
  }).join('');
}

function renderAssignments(assignments) {
  const container = document.getElementById('round-assignments');
  if (!container) return;

  dashboardState.assignments = assignments || [];
  if (!dashboardState.assignments.length) {
    container.innerHTML = '<p class="empty-state">Round này chưa có judge nào được gán.</p>';
    renderAvailableJudges();
    return;
  }

  container.innerHTML = dashboardState.assignments.map((assignment) => {
    const judgeName = assignment.judge_name || assignment.judge_username || `Judge #${assignment.judge_id}`;
    return `
      <div class="assignment-card">
        <div class="assignment-card-top">
          <div>
            <div style="font-weight:700;color:#111827;">${escapeHtml(judgeName)}</div>
            <div class="muted">Judge ID: ${escapeHtml(assignment.judge_id)} | Status: ${escapeHtml(assignment.status || 'assigned')}</div>
            <div class="muted">Assigned at: ${escapeHtml(assignment.assigned_at || '-')}</div>
          </div>
          <button class="btn btn-danger btn-sm unassign-btn" data-judge-id="${escapeHtml(assignment.judge_id)}">Gỡ</button>
        </div>
      </div>
    `;
  }).join('');

  container.querySelectorAll('.unassign-btn').forEach((button) => {
    button.addEventListener('click', async () => {
      const judgeId = button.dataset.judgeId;
      await unassignJudge(judgeId);
    });
  });

  renderAvailableJudges();
}

async function loadAssignmentsForCurrentRound() {
  const contest = getSelectedContest();
  const round = getSelectedRound();
  if (!contest || !round) {
    renderAssignments([]);
    return;
  }

  const response = await fetchRoundAssignments(contest.id, round.id);
  renderAssignments((response && response.assignments) ? response.assignments : []);
}

async function assignSelectedJudges() {
  const contest = getSelectedContest();
  const round = getSelectedRound();
  if (!contest || !round) {
    showToast('Vui lòng chọn contest và round trước', true);
    return;
  }

  const selectedJudgeIds = Array.from(document.querySelectorAll('.judge-select:checked'))
    .map((input) => Number(input.value))
    .filter((value) => Number.isFinite(value));

  if (!selectedJudgeIds.length) {
    showToast('Chọn ít nhất một judge để phân công', true);
    return;
  }

  await window.apiClient.post(
    `/organizer/contests/${encodeURIComponent(contest.id)}/rounds/${encodeURIComponent(round.id)}/judges`,
    { judge_ids: selectedJudgeIds }
  );

  showToast(`Đã gán ${selectedJudgeIds.length} judge vào round`);
  await refreshJudgeManager();
}

async function unassignJudge(judgeId) {
  const contest = getSelectedContest();
  const round = getSelectedRound();
  if (!contest || !round) {
    showToast('Không xác định được round để gỡ judge', true);
    return;
  }

  await window.apiClient.delete(
    `/organizer/contests/${encodeURIComponent(contest.id)}/rounds/${encodeURIComponent(round.id)}/judges/${encodeURIComponent(judgeId)}`
  );

  showToast('Đã gỡ judge khỏi round');
  await refreshJudgeManager();
}

async function refreshJudgeManager() {
  const judgesResponse = await fetchAvailableJudges();
  dashboardState.judges = (judgesResponse && judgesResponse.judges) ? judgesResponse.judges : [];
  await loadAssignmentsForCurrentRound();
  renderAvailableJudges();
}

function bindManagerEvents() {
  const contestSelect = document.getElementById('contest-select');
  const roundSelect = document.getElementById('round-select');
  const assignButton = document.getElementById('assign-selected-btn');
  const refreshButton = document.getElementById('refresh-judge-manager-btn');

  if (contestSelect) {
    contestSelect.addEventListener('change', async (event) => {
      dashboardState.selectedContestId = event.target.value;
      renderRoundOptions();
      await refreshJudgeManager();
    });
  }

  if (roundSelect) {
    roundSelect.addEventListener('change', async (event) => {
      dashboardState.selectedRoundId = event.target.value;
      await refreshJudgeManager();
    });
  }

  if (assignButton) {
    assignButton.addEventListener('click', async () => {
      try {
        assignButton.disabled = true;
        await assignSelectedJudges();
      } catch (error) {
        console.error(error);
        showToast(error.message || 'Không thể phân công judge', true);
      } finally {
        assignButton.disabled = false;
      }
    });
  }

  if (refreshButton) {
    refreshButton.addEventListener('click', async () => {
      try {
        refreshButton.disabled = true;
        const contestsResp = await fetchContests();
        dashboardState.contests = contestsResp && contestsResp.contests ? contestsResp.contests : [];
        renderContests(dashboardState.contests);
        renderContestOptions();
        renderRoundOptions();
        await refreshJudgeManager();
        showToast('Đã làm mới dữ liệu judge assignment');
      } catch (error) {
        console.error(error);
        showToast(error.message || 'Không thể làm mới dữ liệu', true);
      } finally {
        refreshButton.disabled = false;
      }
    });
  }
}

async function initDashboard() {
  const errEl = document.getElementById('error');
  try {
    const contestsResp = await fetchContests();
    dashboardState.contests = (contestsResp && contestsResp.contests) ? contestsResp.contests : [];
    renderContests(dashboardState.contests);
    renderContestOptions();
    renderRoundOptions();
    bindManagerEvents();

    const metrics = await fetchMetrics();
    if (metrics) renderMetrics(metrics);

    await refreshJudgeManager();
  } catch (error) {
    console.error(error);
    if (errEl) {
      errEl.textContent = 'Không thể tải dữ liệu. Vui lòng thử lại.';
    }
    showToast(error.message || 'Không thể tải dashboard', true);
  }
}

document.addEventListener('DOMContentLoaded', initDashboard);
