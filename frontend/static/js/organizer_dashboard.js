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
  // add Actions column header
  table.querySelector('thead tr').insertAdjacentHTML('beforeend', '<th>Actions</th>');
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
    const actionsTd = document.createElement('td');
    const editLink = document.createElement('a');
    editLink.href = `/organizer/create-contest?contest_id=${encodeURIComponent(c.id)}`;
    editLink.textContent = 'Edit';
    editLink.className = 'btn';
    editLink.style = 'display:inline-block;padding:6px 10px;font-size:0.9rem;';

    const manageLink = document.createElement('a');
    // Route to frontend detail UI which loads contest detail via API (authenticated)
    manageLink.href = `/organizer/contest-detail?contest_id=${encodeURIComponent(c.id)}`;
    manageLink.textContent = 'View';
    manageLink.style = 'margin-left:8px;display:inline-block;padding:6px 10px;font-size:0.9rem;text-decoration:none;border-radius:8px;border:1px solid #e5e7eb;background:#fff;color:#374151;';

    actionsTd.appendChild(editLink);
    actionsTd.appendChild(manageLink);
    tr.appendChild(actionsTd);
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  list.appendChild(table);
}

function renderMetrics(metrics) {
  if (!metrics) return;
  const subs = document.getElementById('overview-submissions');
  const judges = document.getElementById('overview-judges');
  // backend now returns `submissions` and `judges`
  if (subs) subs.textContent = (metrics.submissions ?? metrics.submissions_count ?? '-') ;
  if (judges) judges.textContent = (metrics.judges ?? metrics.judges_count ?? '-') ;
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
