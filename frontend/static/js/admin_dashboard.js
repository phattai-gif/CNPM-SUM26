(function () {
  const state = {
    users: [],
    pagination: { page: 1, per_page: 20, total: 0, pages: 1 },
    search: '',
    role: '',
    status: ''
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
    const session = window.AuthSession.getSession();
    if (!session || !session.token) {
      window.location.href = '/auth/login';
      return null;
    }
    const role = String(session.role || (session.user && session.user.role) || '').toLowerCase();
    if (role !== 'admin') {
      window.location.href = '/contests';
      return null;
    }
    return session;
  }

  function formatTimestamp(isoString) {
    if (!isoString) return 'Vừa xong';
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return isoString;
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Vừa xong';
      if (diffMins < 60) return `${diffMins} phút trước`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours} giờ trước`;
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7) return `${diffDays} ngày trước`;
      return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  }

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
      setVal('statPendingContests', metrics.pending_contests);
      setVal('statTotalSubmissions', metrics.total_submissions);
      setVal('statAiFlaggedSubmissions', metrics.ai_flagged_submissions);

      renderRecentActivities(data.recent_activities || []);
    } catch (error) {
      console.error('Error fetching admin metrics:', error);
    }
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
        container.innerHTML = `<p style="color:#f87171;text-align:center;padding:30px;">Lỗi khi tải danh sách: ${escapeHtml(error.message)}</p>`;
      }
      showToast(error.message || 'Không thể tải danh sách người dùng', true);
    }
  }

  function renderUsersTable() {
    const container = document.getElementById('usersListContainer');
    if (!container) return;

    if (!state.users.length) {
      container.innerHTML = '<p style="color:#6b7f94;text-align:center;padding:30px;">Không tìm thấy tài khoản người dùng nào.</p>';
      return;
    }

    const currentSession = window.AuthSession.getSession();
    const currentUserId = currentSession.user ? currentSession.user.id : null;

    const tableHtml = `
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Người Dùng</th>
            <th>Email</th>
            <th>Vai Trò</th>
            <th>Trạng Thái</th>
            <th>Hành Động</th>
          </tr>
        </thead>
        <tbody>
          ${state.users.map(u => {
            const isSelf = currentUserId && String(currentUserId) === String(u.id);
            const roleClass = `role-${u.role || 'participant'}`;
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
                    <option value="participant" ${u.role === 'participant' ? 'selected' : ''}>Participant (Thí sinh)</option>
                    <option value="judge" ${u.role === 'judge' ? 'selected' : ''}>Judge (Giám khảo)</option>
                    <option value="organizer" ${u.role === 'organizer' ? 'selected' : ''}>Organizer (Ban tổ chức)</option>
                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin (Quản trị viên)</option>
                  </select>
                </td>
                <td>
                  <span class="status-badge ${statusClass}">${escapeHtml((u.status || 'active').toUpperCase())}</span>
                </td>
                <td>
                  <div class="action-group">
                    <button class="btn btn-outline btn-sm toggle-status-btn" data-user-id="${escapeHtml(u.id)}" data-current-status="${escapeHtml(u.status)}" ${isSelf ? 'disabled' : ''}>
                      ${u.status === 'locked' ? 'Mở Khóa' : 'Khóa'}
                    </button>
                    <button class="btn btn-danger btn-sm delete-user-btn" data-user-id="${escapeHtml(u.id)}" data-username="${escapeHtml(u.username)}" ${isSelf ? 'disabled' : ''}>
                      Xóa
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

    // Role select change handler
    container.querySelectorAll('.role-select').forEach(select => {
      select.addEventListener('change', async (e) => {
        const userId = Number(select.dataset.userId);
        const newRole = select.value;
        try {
          await window.apiClient.patch(`/admin/users/${userId}/role`, { role: newRole });
          showToast(`Đã thay đổi vai trò tài khoản #${userId} thành ${newRole.toUpperCase()}`);
          await loadUsers(state.pagination.page);
          await loadAdminMetrics();
        } catch (error) {
          showToast(error.message || 'Không thể đổi vai trò', true);
          await loadUsers(state.pagination.page);
        }
      });
    });

    // Toggle status button handler
    container.querySelectorAll('.toggle-status-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = Number(btn.dataset.userId);
        const currentStatus = btn.dataset.currentStatus;
        const newStatus = currentStatus === 'locked' ? 'active' : 'locked';
        try {
          await window.apiClient.patch(`/admin/users/${userId}/status`, { status: newStatus });
          showToast(`Đã ${newStatus === 'locked' ? 'khóa' : 'mở khóa'} tài khoản #${userId}`);
          await loadUsers(state.pagination.page);
          await loadAdminMetrics();
        } catch (error) {
          showToast(error.message || 'Không thể cập nhật trạng thái', true);
        }
      });
    });

    // Delete user button handler
    container.querySelectorAll('.delete-user-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = Number(btn.dataset.userId);
        const username = btn.dataset.username;
        if (!confirm(`Bạn có chắc chắn muốn XÓA vĩnh viễn tài khoản "${username}" (#${userId})? Hành động này không thể hoàn tác.`)) {
          return;
        }

        try {
          await window.apiClient.delete(`/admin/users/${userId}`);
          showToast(`Đã xóa thành công tài khoản "${username}" (#${userId})`);
          await loadUsers(state.pagination.page);
          await loadAdminMetrics();
        } catch (error) {
          showToast(error.message || 'Không thể xóa tài khoản', true);
        }
      });
    });
  }

  function renderPagination() {
    const container = document.getElementById('paginationContainer');
    if (!container) return;

    const { page, pages, total } = state.pagination;
    if (pages <= 1) {
      container.innerHTML = `<span>Tổng số: ${total} tài khoản</span>`;
      return;
    }

    container.innerHTML = `
      <span>Trang ${page} / ${pages} (Tổng số: ${total} tài khoản)</span>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-outline btn-sm" id="prevPageBtn" ${page <= 1 ? 'disabled' : ''}>&laquo; Trang trước</button>
        <button class="btn btn-outline btn-sm" id="nextPageBtn" ${page >= pages ? 'disabled' : ''}>Trang sau &raquo;</button>
      </div>
    `;

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    if (prevBtn) prevBtn.addEventListener('click', () => loadUsers(page - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => loadUsers(page + 1));
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
        showToast('Đã làm mới danh sách người dùng & thống kê');
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadAdminMetrics();
    loadUsers(1);
  });
})();
