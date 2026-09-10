(function () {
  const state = {
    users: [],
    pagination: { page: 1, per_page: 20, total: 0, pages: 1 },
    search: '',
    role: '',
    status: '',
    contests: [],
    contestSearch: '',
    contestStatus: '',
    aiReports: [],
    auditLogs: []
  };

  function showToast(message, isError = false) {
    const toast = document.getElementById('admin-toast');
    if (!toast) return;
    toast.textContent = message;
    toast.style.background = isError ? '#b91c1c' : '#f5a623';
    toast.style.color = isError ? '#ffffff' : '#080c14';
    toast.style.display = 'block';
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => {
      toast.style.display = 'none';
    }, 3000);
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function requireAdminSession() {
    const session = window.AuthSession ? window.AuthSession.getSession() : null;
    if (!session || !session.token) {
      window.location.href = '/auth/login';
      return null;
    }
    const role = String(session.role || (session.user && session.user.role) || '').toLowerCase();
    if (role !== 'admin') {
      if (role === 'organizer') {
        window.location.href = '/organizer/dashboard';
      } else {
        window.location.href = '/contests';
      }
      return null;
    }
    return session;
  }

  function formatTimestamp(isoString) {
    if (!isoString) return 'Just now';
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return isoString;
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins} minutes ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours} hours ago`;
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7) return `${diffDays} days ago`;
      return date.toLocaleDateString('en-US', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  }

  // --- Metrics & Health ---
  async function loadAdminMetrics() {
    if (!requireAdminSession()) return;
    try {
      const data = await window.apiClient.get('/admin/dashboard/metrics');
      const metrics = data.metrics || {};

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val ?? 0;
      };

      setVal('statTotalUsers', metrics.total_users);
      setVal('statAdmins', metrics.admins_count);
      setVal('statOrganizers', metrics.organizers_count);
      setVal('statJudges', metrics.judges_count);
      setVal('statParticipants', metrics.participants_count);
      setVal('statLockedUsers', metrics.locked_users);
      setVal('statTotalContests', metrics.total_contests);
      setVal('statActiveContests', metrics.active_contests);
      setVal('statPendingContests', metrics.pending_contests);
      setVal('statTotalSubmissions', metrics.total_submissions);
      setVal('statPendingSubmissions', metrics.pending_submissions);
      setVal('statAiFlaggedSubmissions', metrics.ai_flagged_submissions);
      setVal('statHighSeverityAiFlags', metrics.high_severity_ai_flags);

      renderSystemHealth(data.system_health || {});
      renderRecentActivities(data.recent_activities || []);
    } catch (error) {
      console.error('Error fetching admin metrics:', error);
    }
  }

  function renderSystemHealth(systemHealth) {
    const container = document.getElementById('systemHealthContainer');
    if (!container) return;

    const services = [
      { key: 'database', defaultName: 'Database (PostgreSQL Supabase)' },
      { key: 'storage', defaultName: 'Storage (Tải lên media)' },
      { key: 'email', defaultName: 'Dịch vụ Email Notification' }
    ];

    container.innerHTML = services.map(srv => {
      const info = systemHealth[srv.key] || {};
      const status = (info.status || 'online').toLowerCase();
      const isOnline = status === 'online' || status === 'active' || status === 'ok';

      const badgeBg = isOnline ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)';
      const badgeColor = isOnline ? '#4ade80' : '#f87171';
      const badgeBorder = isOnline ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)';
      const dot = isOnline ? '🟢' : '🔴';
      const statusText = isOnline ? 'HOẠT ĐỘNG TỐT (ONLINE)' : 'CẦN KIỂM TRA (DEGRADED)';

      return `
        <div style="background: rgba(13, 22, 34, 0.6); border: 1px solid #1e2a3a; border-radius: 12px; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div style="font-weight: 700; color: #f0f4f8; font-size: 0.95rem; margin-bottom: 4px;">
              ${escapeHtml(info.name || srv.defaultName)}
            </div>
            <div style="font-size: 0.8rem; color: ${badgeColor}; display: flex; align-items: center; gap: 6px;">
              <span>${dot}</span>
              <span style="font-weight: 700;">${statusText}</span>
            </div>
          </div>
          <span style="padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; font-weight: 700; background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder};">
            ${isOnline ? 'STABLE' : 'ALERT'}
          </span>
        </div>
      `;
    }).join('');
  }

  function renderRecentActivities(activities) {
    const container = document.getElementById('recentActivitiesContainer');
    if (!container) return;

    if (!activities.length) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:20px;">Chưa có hoạt động hệ thống nào gần đây.</p>';
      return;
    }

    container.innerHTML = activities.map(act => {
      let badgeStyle = 'background: rgba(245, 166, 35, 0.15); color: #f5a623; border: 1px solid rgba(245, 166, 35, 0.3);';
      if (act.type === 'user') {
        badgeStyle = 'background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3);';
      } else if (act.type === 'contest') {
        badgeStyle = 'background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3);';
      } else if (act.type === 'submission') {
        badgeStyle = 'background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3);';
      }

      return `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #1e2a3a;background:rgba(13,22,34,0.5);border-radius:10px;margin-bottom:8px;">
          <div style="display:flex;align-items:center;gap:12px;overflow:hidden;">
            <span style="padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700;white-space:nowrap;${badgeStyle}">
              ${escapeHtml(act.badge || 'HỆ THỐNG')}
            </span>
            <span style="color:#e8edf2;font-size:0.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              ${escapeHtml(act.title)}
            </span>
          </div>
          <span style="color:#6b7f94;font-size:0.8rem;white-space:nowrap;margin-left:12px;">
            ${escapeHtml(formatTimestamp(act.timestamp))}
          </span>
        </div>
      `;
    }).join('');
  }

  // --- TAB 1: User & Role Management ---
  async function loadUsers(page = 1) {
    if (!requireAdminSession()) return;
    state.pagination.page = page;

    const queryParams = new URLSearchParams();
    queryParams.set('page', page);
    queryParams.set('per_page', 50);
    if (state.search) queryParams.set('search', state.search);
    if (state.role) queryParams.set('role', state.role);
    if (state.status) queryParams.set('status', state.status);

    const container = document.getElementById('usersListContainer');
    if (container) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">Đang tải danh sách người dùng...</p>';
    }

    try {
      const response = await window.apiClient.get(`/admin/users?${queryParams.toString()}`);
      state.users = response.users || [];
      if (response.pagination) {
        state.pagination = response.pagination;
      }
      renderUsersTable();
      renderPagination();
    } catch (error) {
      console.error(error);
      if (container) {
        container.innerHTML = `<p style="color:#f87171;text-align:center;padding:30px;">Error loading users: ${escapeHtml(error.message)}</p>`;
      }
      showToast(error.message || 'Unable to load user accounts', true);
    }
  }

  function renderUsersTable() {
    const container = document.getElementById('usersListContainer');
    if (!container) return;

    if (!state.users.length) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">No user accounts found.</p>';
      return;
    }

    const currentSession = window.AuthSession ? window.AuthSession.getSession() : null;
    const currentUserId = currentSession && currentSession.user ? currentSession.user.id : null;

    const tableHtml = `
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>User</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${state.users.map(u => {
            const isSelf = currentUserId && String(currentUserId) === String(u.id);
            const statusClass = `status-${u.status || 'active'}`;

            return `
              <tr>
                <td>#${escapeHtml(u.id)}</td>
                <td>
                  <div class="user-meta-name">${escapeHtml(u.full_name || u.username)}</div>
                  <div class="user-meta-sub">@${escapeHtml(u.username)}</div>
                </td>
                <td>${escapeHtml(u.email || '-')}</td>
                <td>
                  <select class="field-input role-select btn-sm" data-user-id="${escapeHtml(u.id)}" ${isSelf ? 'disabled' : ''}>
                    <option value="participant" ${u.role === 'participant' ? 'selected' : ''}>Participant</option>
                    <option value="judge" ${u.role === 'judge' ? 'selected' : ''}>Judge</option>
                    <option value="organizer" ${u.role === 'organizer' ? 'selected' : ''}>Organizer</option>
                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Administrator</option>
                  </select>
                </td>
                <td>
                  <span class="status-badge ${statusClass}">${escapeHtml((u.status || 'active').toUpperCase())}</span>
                </td>
                <td>
                  <div class="action-group">
                    <button class="btn btn-outline btn-sm toggle-status-btn" data-user-id="${escapeHtml(u.id)}" data-current-status="${escapeHtml(u.status)}" ${isSelf ? 'disabled' : ''}>
                      ${u.status === 'locked' ? 'Unlock' : 'Lock'}
                    </button>
                    <button class="btn btn-danger btn-sm delete-user-btn" data-user-id="${escapeHtml(u.id)}" data-username="${escapeHtml(u.username)}" ${isSelf ? 'disabled' : ''}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    `;

    container.innerHTML = tableHtml;
    bindTableEvents();
  }

  function bindTableEvents() {
    const container = document.getElementById('usersListContainer');
    if (!container) return;

    container.querySelectorAll('.role-select').forEach(select => {
      select.addEventListener('change', async (e) => {
        const userId = Number(select.dataset.userId);
        const newRole = select.value;
        try {
          await window.apiClient.patch(`/admin/users/${userId}/role`, { role: newRole });
          showToast(`Changed role for user #${userId} to ${newRole.toUpperCase()}`);
          await loadUsers(state.pagination.page);
          await loadAdminMetrics();
        } catch (error) {
          showToast(error.message || 'Unable to update user role', true);
          await loadUsers(state.pagination.page);
        }
      });
    });

    container.querySelectorAll('.toggle-status-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = Number(btn.dataset.userId);
        const currentStatus = btn.dataset.currentStatus;
        const newStatus = currentStatus === 'locked' ? 'active' : 'locked';
        try {
          await window.apiClient.patch(`/admin/users/${userId}/status`, { status: newStatus });
          showToast(`Account #${userId} is now ${newStatus.toUpperCase()}`);
          await loadUsers(state.pagination.page);
          await loadAdminMetrics();
        } catch (error) {
          showToast(error.message || 'Unable to update account status', true);
        }
      });
    });

    container.querySelectorAll('.delete-user-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = Number(btn.dataset.userId);
        const username = btn.dataset.username;
        if (!confirm(`Are you sure you want to permanently delete account "${username}" (#${userId})? This action cannot be undone.`)) {
          return;
        }

        try {
          await window.apiClient.delete(`/admin/users/${userId}`);
          showToast(`Deleted user "${username}" (#${userId}) successfully`);
          await loadUsers(state.pagination.page);
          await loadAdminMetrics();
        } catch (error) {
          showToast(error.message || 'Unable to delete user account', true);
        }
      });
    });
  }

  function renderPagination() {
    const container = document.getElementById('paginationContainer');
    if (!container) return;

    const { page, pages, total } = state.pagination;
    if (pages <= 1) {
      container.innerHTML = `<span>Total: ${total} accounts</span>`;
      return;
    }

    container.innerHTML = `
      <span>Page ${page} of ${pages} (Total: ${total} accounts)</span>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-outline btn-sm" id="prevPageBtn" ${page <= 1 ? 'disabled' : ''}>&laquo; Previous</button>
        <button class="btn btn-outline btn-sm" id="nextPageBtn" ${page >= pages ? 'disabled' : ''}>Next &raquo;</button>
      </div>
    `;

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    if (prevBtn) prevBtn.addEventListener('click', () => loadUsers(page - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => loadUsers(page + 1));
  }

  // --- TAB 2: Contest Oversight ---
  async function loadContests() {
    if (!requireAdminSession()) return;
    const container = document.getElementById('contestsListContainer');
    if (container) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">Loading contests...</p>';
    }

    try {
      const response = await window.apiClient.get('/admin/contests');
      state.contests = response.contests || [];
      renderContestsTable();
    } catch (error) {
      console.error(error);
      if (container) {
        container.innerHTML = `<p style="color:#f87171;text-align:center;padding:30px;">Error loading contests: ${escapeHtml(error.message)}</p>`;
      }
    }
  }

  function renderContestsTable() {
    const container = document.getElementById('contestsListContainer');
    if (!container) return;

    let filtered = state.contests;
    if (state.contestSearch) {
      const kw = state.contestSearch.toLowerCase();
      filtered = filtered.filter(c => (c.title || '').toLowerCase().includes(kw) || String(c.id).includes(kw));
    }
    if (state.contestStatus) {
      filtered = filtered.filter(c => String(c.status || '').toLowerCase() === state.contestStatus.toLowerCase());
    }

    if (!filtered.length) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">No contests found matching criteria.</p>';
      return;
    }

    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Contest Title</th>
            <th>Organizer</th>
            <th>Status</th>
            <th>Admin Actions</th>
          </tr>
        </thead>
        <tbody>
          ${filtered.map(c => {
            const st = (c.status || 'draft').toLowerCase();
            let stBadge = `<span class="status-badge status-active">${escapeHtml(st.toUpperCase())}</span>`;
            if (st === 'suspended') {
              stBadge = `<span class="status-badge status-locked">SUSPENDED</span>`;
            } else if (st === 'draft' || st === 'pending') {
              stBadge = `<span class="status-badge" style="background:rgba(245,166,35,0.18);color:#f5a623;">PENDING</span>`;
            }

            return `
              <tr>
                <td>#${escapeHtml(c.id)}</td>
                <td>
                  <div class="user-meta-name">${escapeHtml(c.title)}</div>
                  <div class="user-meta-sub">${escapeHtml(c.description || 'No description')}</div>
                </td>
                <td>ID: #${escapeHtml(c.organizer_id || '-')}</td>
                <td>${stBadge}</td>
                <td>
                  <div class="action-group">
                    ${st !== 'published' && st !== 'active' ? `
                      <button class="btn btn-outline btn-sm approve-contest-btn" data-contest-id="${escapeHtml(c.id)}">
                        ✅ Approve / Publish
                      </button>
                    ` : ''}
                    ${st !== 'rejected' && st !== 'published' ? `
                      <button class="btn btn-danger btn-sm reject-contest-btn" data-contest-id="${escapeHtml(c.id)}">
                        ❌ Reject
                      </button>
                    ` : ''}
                    ${st !== 'suspended' ? `
                      <button class="btn btn-danger btn-sm suspend-contest-btn" data-contest-id="${escapeHtml(c.id)}">
                        ⛔ Suspend
                      </button>
                    ` : ''}
                  </div>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    `;

    // Bind Contest actions
    container.querySelectorAll('.approve-contest-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = Number(btn.dataset.contestId);
        try {
          await window.apiClient.post(`/admin/contests/${id}/approve`);
          showToast(`Contest #${id} approved and published`);
          await loadContests();
          await loadAdminMetrics();
        } catch (err) {
          showToast(err.message || 'Unable to approve contest', true);
        }
      });
    });

    container.querySelectorAll('.suspend-contest-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = Number(btn.dataset.contestId);
        if (!confirm(`Are you sure you want to SUSPEND contest #${id}?`)) return;
        try {
          await window.apiClient.post(`/admin/contests/${id}/suspend`);
          showToast(`Contest #${id} suspended`);
          await loadContests();
          await loadAdminMetrics();
        } catch (err) {
          showToast(err.message || 'Unable to suspend contest', true);
        }
      });
    });

    container.querySelectorAll('.reject-contest-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = Number(btn.dataset.contestId);
        const reason = window.prompt('Enter rejection reason:');
        if (!reason || !reason.trim()) return;
        try {
          await window.apiClient.post(`/admin/contests/${id}/reject`, { reason: reason.trim() });
          showToast(`Contest #${id} rejected`);
          await loadContests();
          await loadAdminMetrics();
          await loadAuditLogs();
        } catch (err) {
          showToast(err.message || 'Unable to reject contest', true);
        }
      });
    });
  }

  // --- TAB 3: AI Inspection ---
  async function loadAiReports() {
    if (!requireAdminSession()) return;
    const container = document.getElementById('aiReportsListContainer');
    if (container) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">Loading AI inspection reports...</p>';
    }

    try {
      const response = await window.apiClient.get('/admin/ai-reports');
      state.aiReports = response.reports || [];
      renderAiReportsTable();
    } catch (error) {
      console.error(error);
      if (container) {
        container.innerHTML = `<p style="color:#f87171;text-align:center;padding:30px;">Error loading AI reports: ${escapeHtml(error.message)}</p>`;
      }
    }
  }

  function renderAiReportsTable() {
    const container = document.getElementById('aiReportsListContainer');
    if (!container) return;

    if (!state.aiReports.length) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">No AI flag reports in the system.</p>';
      return;
    }

    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Report ID</th>
            <th>Submission ID</th>
            <th>AI Model</th>
            <th>Confidence</th>
            <th>Details</th>
            <th>Timestamp</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${state.aiReports.map(r => {
            const score = r.ai_confidence_score !== null ? (r.ai_confidence_score * 100).toFixed(1) + '%' : 'N/A';
            const isHighRisk = (r.ai_confidence_score || 0) >= 0.75;
            const badgeColor = isHighRisk ? '#ef4444' : '#f5a623';

            return `
              <tr>
                <td>#${escapeHtml(r.id)}</td>
                <td><strong>#${escapeHtml(r.submission_id)}</strong></td>
                <td>${escapeHtml(r.ai_model_name || 'Sightengine / OpenAI Vision')}</td>
                <td><span style="font-weight:800;color:${badgeColor}">${score}</span></td>
                <td style="font-size:0.85rem;color:#8899aa;max-width:300px;overflow:hidden;text-overflow:ellipsis;">
                  ${escapeHtml(JSON.stringify(r.raw_details || {}))}
                </td>
                <td>${escapeHtml(formatTimestamp(r.created_at))}</td>
                <td>
                  <div class="action-group">
                    <button class="btn btn-sm approve-submission-btn" data-submission-id="${escapeHtml(r.submission_id)}">✅ Approve</button>
                    <button class="btn btn-danger btn-sm reject-submission-btn" data-submission-id="${escapeHtml(r.submission_id)}">❌ Reject</button>
                    <button class="btn btn-outline btn-sm dismiss-flag-btn" data-submission-id="${escapeHtml(r.submission_id)}">Dismiss Flag</button>
                  </div>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    `;

    const moderate = async (button, action, promptText) => {
      const submissionId = Number(button.dataset.submissionId);
      const reviewNotes = promptText ? window.prompt(promptText) : '';
      if (promptText && (!reviewNotes || !reviewNotes.trim())) return;
      try {
        await window.apiClient.post(`/moderator/submissions/${submissionId}/${action}`, {
          review_notes: reviewNotes || undefined,
        });
        showToast('Submission status updated');
        await loadAiReports();
        await loadAdminMetrics();
      } catch (err) {
        showToast(err.message || 'Unable to update submission', true);
      }
    };
    container.querySelectorAll('.approve-submission-btn').forEach(btn => btn.addEventListener('click', () => moderate(btn, 'approve')));
    container.querySelectorAll('.reject-submission-btn').forEach(btn => btn.addEventListener('click', () => moderate(btn, 'reject', 'Enter rejection reason:')));
    container.querySelectorAll('.dismiss-flag-btn').forEach(btn => btn.addEventListener('click', () => moderate(btn, 'dismiss-flag')));
  }

  // --- TAB 4: Audit Logs ---
  async function loadAuditLogs() {
    if (!requireAdminSession()) return;
    const container = document.getElementById('auditLogsListContainer');
    if (container) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">Loading audit logs...</p>';
    }

    try {
      const response = await window.apiClient.get('/admin/audit-logs');
      state.auditLogs = response.audit_logs || [];
      renderAuditLogsTable();
    } catch (error) {
      console.error(error);
      if (container) {
        container.innerHTML = `<p style="color:#f87171;text-align:center;padding:30px;">Error loading audit logs: ${escapeHtml(error.message)}</p>`;
      }
    }
  }

  function renderAuditLogsTable() {
    const container = document.getElementById('auditLogsListContainer');
    if (!container) return;

    if (!state.auditLogs.length) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">No system audit logs recorded.</p>';
      return;
    }

    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Log ID</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Entity</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          ${state.auditLogs.map(l => `
            <tr>
              <td>#${escapeHtml(l.id)}</td>
              <td>User #${escapeHtml(l.user_id || 'System')}</td>
              <td><span style="font-weight:700;color:#f5a623;">${escapeHtml(l.action)}</span></td>
              <td>${escapeHtml(l.entity_name || '')} #${escapeHtml(l.entity_id || '')}</td>
              <td>${escapeHtml(formatTimestamp(l.created_at))}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  // --- Notification Form Handler ---
  function bindSettingsForm() {
    const form = document.getElementById('systemSettingsForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        max_file_size_mb: Number(document.getElementById('cfgMaxFileSize').value),
        allowed_extensions: document.getElementById('cfgAllowedExts').value,
        ai_threshold_percent: Number(document.getElementById('cfgAiThreshold').value),
        ai_action: document.getElementById('cfgAiAction').value,
        maintenance_mode: document.getElementById('cfgMaintenanceMode').checked
      };

      try {
        await window.apiClient.put('/admin/settings', payload);
        showToast('System configuration saved successfully');
      } catch (err) {
        showToast(err.message || 'Error saving configuration', true);
      }
    });
  }

  function bindNotificationForm() {
    const form = document.getElementById('systemNotificationForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('notifTitle').value.trim();
      const body = document.getElementById('notifBody').value.trim();

      if (!title || !body) {
        showToast('Please enter both title and message body', true);
        return;
      }

      try {
        const response = await window.apiClient.post('/admin/notifications/system', { title, body });
        showToast(response.message || 'Broadcast notification sent successfully!');
        form.reset();
      } catch (err) {
        showToast(err.message || 'Unable to send broadcast notification', true);
      }
    });
  }

  // --- TAB SWITCHING LOGIC ---
  function bindTabs() {
    const tabBtns = document.querySelectorAll('.admin-tab-btn');
    const tabContents = document.querySelectorAll('.admin-tab-content');

    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.dataset.tab;
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));

        btn.classList.add('active');
        const targetContent = document.getElementById(targetId);
        if (targetContent) targetContent.classList.add('active');

        // Lazy load data for selected tab
        if (targetId === 'tab-contests' && !state.contests.length) {
          loadContests();
        } else if (targetId === 'tab-ai' && !state.aiReports.length) {
          loadAiReports();
        } else if (targetId === 'tab-audit' && !state.auditLogs.length) {
          loadAuditLogs();
        }
      });
    });
  }

  function bindEvents() {
    const searchInput = document.getElementById('searchInput');
    const roleFilter = document.getElementById('roleFilter');
    const statusFilter = document.getElementById('statusFilter');
    const refreshBtn = document.getElementById('btnRefreshUsers');

    let debounceTimer = null;
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        state.search = e.target.value.trim();
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => loadUsers(1), 350);
      });
    }

    if (roleFilter) {
      roleFilter.addEventListener('change', (e) => {
        state.role = e.target.value;
        loadUsers(1);
      });
    }

    if (statusFilter) {
      statusFilter.addEventListener('change', (e) => {
        state.status = e.target.value;
        loadUsers(1);
      });
    }

    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        loadUsers(state.pagination.page);
        loadAdminMetrics();
        showToast('User list and metrics refreshed');
      });
    }

    // Contest Oversight filters & buttons
    const contestSearchInput = document.getElementById('contestSearchInput');
    const contestStatusFilter = document.getElementById('contestStatusFilter');
    const btnRefreshContests = document.getElementById('btnRefreshContests');

    if (contestSearchInput) {
      contestSearchInput.addEventListener('input', (e) => {
        state.contestSearch = e.target.value.trim();
        renderContestsTable();
      });
    }

    if (contestStatusFilter) {
      contestStatusFilter.addEventListener('change', (e) => {
        state.contestStatus = e.target.value;
        renderContestsTable();
      });
    }

    if (btnRefreshContests) {
      btnRefreshContests.addEventListener('click', () => {
        loadContests();
        showToast('Contests refreshed');
      });
    }

    const btnRefreshAiReports = document.getElementById('btnRefreshAiReports');
    if (btnRefreshAiReports) {
      btnRefreshAiReports.addEventListener('click', () => {
        loadAiReports();
        showToast('AI reports refreshed');
      });
    }

    const btnRefreshAuditLogs = document.getElementById('btnRefreshAuditLogs');
    if (btnRefreshAuditLogs) {
      btnRefreshAuditLogs.addEventListener('click', () => {
        loadAuditLogs();
        showToast('Audit logs refreshed');
      });
    }

    bindTabs();
    bindSettingsForm();
    bindNotificationForm();
  }

  document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadAdminMetrics();
    loadUsers(1);
    loadContests();
    loadAiReports();
  });
})();
