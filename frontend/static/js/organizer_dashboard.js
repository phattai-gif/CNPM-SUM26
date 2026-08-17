async function fetchContests() {
  const root = document.getElementById('dashboard');
  if (!root) return { contests: [] };
  const session = window.AuthSession.getSession();
  if (!session.token) {
    window.location.href = '/auth/login';
    return { contests: [] };
  }

  // Use global apiClient which attaches Authorization header
  return await window.apiClient.get('/organizer/contests');
}

async function fetchMetrics() {
  const root = document.getElementById('dashboard');
  if (!root) return null;
  const session = window.AuthSession.getSession();
  if (!session.token) {
    window.location.href = '/auth/login';
    return null;
  }

  return await window.apiClient.get(`/organizer/dashboard/metrics?organizer_id=${encodeURIComponent(root.dataset.organizerId)}`);
}

function renderContests(contests) {
  const list = document.getElementById('contests-list');
  if (!list) return;
  // If server already rendered a table, replace it with a dynamic list
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
        <th>Start</th>
        <th>End</th>
      </tr>
    </thead>
  `;
  const tbody = document.createElement('tbody');

  contests.forEach(c => {
    const tr = document.createElement('tr');
    const start = c.start_date || '-';
    const end = c.end_date || '-';
    tr.innerHTML = `
      <td>${c.id}</td>
      <td>${c.title}</td>
      <td>${c.status || '-'}</td>
      <td>${start}</td>
      <td>${end}</td>
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
  if (subs) subs.textContent = metrics.submissions_count ?? '-';
  if (judges) judges.textContent = metrics.judges_count ?? '-';
}

async function initDashboard() {
  const errEl = document.getElementById('error');
  try {
    const contestsResp = await fetchContests();
    const contests = (contestsResp && contestsResp.contests) ? contestsResp.contests : [];
    renderContests(contests);

    const metrics = await fetchMetrics();
    if (metrics) renderMetrics(metrics);
  } catch (err) {
    console.error(err);
    if (errEl) {
      // If apiClient triggered logout, it already redirected; otherwise show message
      errEl.textContent = 'Không thể tải dữ liệu. Vui lòng thử lại.';
    }
  }
}

document.addEventListener('DOMContentLoaded', initDashboard);
