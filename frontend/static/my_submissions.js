/**
 * My Submissions (Portfolio) JavaScript Handler
 * Fetches user submissions from DB, handles stats, tabs, filtering, and interactions
 */

document.addEventListener('DOMContentLoaded', () => {
    class MySubmissionsApp {
        constructor() {
            this.submissions = [];
            this.currentFilter = 'all';
            this.searchQuery = '';
            
            // DOM Elements
            this.grid = document.getElementById('submissionsGrid');
            this.loadingState = document.getElementById('loadingState');
            this.emptyState = document.getElementById('emptyState');
            this.emptyMessage = document.getElementById('emptyMessage');
            this.filterTabs = document.getElementById('filterTabs');
            this.searchInput = document.getElementById('searchInput');
            this.userNameEl = document.getElementById('userName');
            this.userAvatarEl = document.getElementById('userAvatar');
            this.logoutBtn = document.getElementById('logoutBtn');
            this.brandHomeLink = document.getElementById('brandHomeLink');
            
            // Stat counters
            this.statTotal = document.getElementById('statTotal');
            this.statSubmitted = document.getElementById('statSubmitted');
            this.statDraft = document.getElementById('statDraft');
            this.statGraded = document.getElementById('statGraded');
            
            this.countAll = document.getElementById('countAll');
            this.countSubmitted = document.getElementById('countSubmitted');
            this.countDraft = document.getElementById('countDraft');
            this.countGraded = document.getElementById('countGraded');

            this.init();
        }

        init() {
            this.setupUser();
            this.setupEvents();
            this.fetchSubmissions();
        }

        setupUser() {
            const session = window.AuthSession ? window.AuthSession.getSession() : {};
            const user = session.user || {};
            const role = String(session.role || user.role || '').toLowerCase();
            const canManage = role === 'organizer' || role === 'admin';

            if (this.brandHomeLink) {
                this.brandHomeLink.href = canManage ? '/organizer/dashboard' : '/contests';
            }

            if (canManage) {
                const btnSubmitHeader = document.getElementById('btnMySubmissionsSubmit');
                const btnSubmitEmpty = document.getElementById('btnEmptySubmissionsSubmit');
                if (btnSubmitHeader) btnSubmitHeader.style.display = 'none';
                if (btnSubmitEmpty) btnSubmitEmpty.style.display = 'none';
            }
            
            if (this.userNameEl && user && (user.username || user.full_name)) {
                const displayName = user.full_name || user.username;
                this.userNameEl.textContent = displayName;
                if (this.userAvatarEl) {
                    this.userAvatarEl.textContent = displayName.charAt(0).toUpperCase();
                }
            }

            if (this.logoutBtn) {
                this.logoutBtn.addEventListener('click', () => {
                    if (window.AuthSession) {
                        window.AuthSession.logout();
                    } else {
                        sessionStorage.removeItem('authToken');
                        sessionStorage.removeItem('authUser');
                        sessionStorage.removeItem('authRole');
                        window.location.href = '/auth/login';
                    }
                });
            }
        }

        setupEvents() {
            // Tab filtering
            if (this.filterTabs) {
                this.filterTabs.addEventListener('click', (e) => {
                    const btn = e.target.closest('.filter-tab');
                    if (!btn) return;
                    
                    this.filterTabs.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                    btn.classList.add('active');
                    this.currentFilter = btn.dataset.filter || 'all';
                    this.renderSubmissions();
                });
            }

            // Search input
            if (this.searchInput) {
                this.searchInput.addEventListener('input', (e) => {
                    this.searchQuery = e.target.value.toLowerCase().trim();
                    this.renderSubmissions();
                });
            }
        }

        async fetchSubmissions() {
            this.loadingState.style.display = 'block';
            this.emptyState.style.display = 'none';
            this.grid.innerHTML = '';

            try {
                // Ensure auth token is present
                const session = window.AuthSession ? window.AuthSession.getSession() : {};
                if (!session.token) {
                    this.loadingState.style.display = 'none';
                    this.emptyState.style.display = 'block';
                    this.emptyMessage.innerHTML = 'Bạn chưa đăng nhập. Vui lòng <a href="/auth/login" style="color:var(--accent-amber); font-weight:700;">Đăng nhập</a> để xem bài dự thi.';
                    return;
                }

                const data = await window.apiClient.get('/submissions/my');
                this.submissions = data.submissions || [];

                this.updateStats();
                this.renderSubmissions();
            } catch (error) {
                console.error('Failed to fetch submissions:', error);
                this.showToast(error.message || 'Không thể tải danh sách bài thi.', 'error');
                
                // Fallback attempt to general list if needed
                try {
                    const fallbackData = await window.apiClient.get('/submissions');
                    if (Array.isArray(fallbackData)) {
                        this.submissions = fallbackData;
                        this.updateStats();
                        this.renderSubmissions();
                        return;
                    }
                } catch (e) {
                    // Ignore fallback failure
                }

                this.loadingState.style.display = 'none';
                this.emptyState.style.display = 'block';
                this.emptyMessage.textContent = 'Có lỗi xảy ra khi kết nối máy chủ. Vui lòng thử lại sau.';
            } finally {
                this.loadingState.style.display = 'none';
            }
        }

        updateStats() {
            const total = this.submissions.length;
            const submitted = this.submissions.filter(s => s.status === 'submitted' || s.status === 'under_review').length;
            const draft = this.submissions.filter(s => s.status === 'draft').length;
            const graded = this.submissions.filter(s => s.final_score !== null || s.status === 'graded').length;

            if (this.statTotal) this.statTotal.textContent = total;
            if (this.statSubmitted) this.statSubmitted.textContent = submitted;
            if (this.statDraft) this.statDraft.textContent = draft;
            if (this.statGraded) this.statGraded.textContent = graded;

            if (this.countAll) this.countAll.textContent = total;
            if (this.countSubmitted) this.countSubmitted.textContent = submitted;
            if (this.countDraft) this.countDraft.textContent = draft;
            if (this.countGraded) this.countGraded.textContent = graded;
        }

        renderSubmissions() {
            const filtered = this.submissions.filter(sub => {
                // Filter by tab
                let matchesTab = true;
                if (this.currentFilter === 'submitted') {
                    matchesTab = sub.status === 'submitted' || sub.status === 'under_review';
                } else if (this.currentFilter === 'draft') {
                    matchesTab = sub.status === 'draft';
                } else if (this.currentFilter === 'graded') {
                    matchesTab = sub.final_score !== null || sub.status === 'graded';
                }

                // Filter by search query
                let matchesSearch = true;
                if (this.searchQuery) {
                    const title = (sub.title || '').toLowerCase();
                    const contest = (sub.contest_title || '').toLowerCase();
                    const round = (sub.round_title || '').toLowerCase();
                    matchesSearch = title.includes(this.searchQuery) || contest.includes(this.searchQuery) || round.includes(this.searchQuery);
                }

                return matchesTab && matchesSearch;
            });

            this.grid.innerHTML = '';

            if (filtered.length === 0) {
                this.emptyState.style.display = 'block';
                if (this.searchQuery || this.currentFilter !== 'all') {
                    this.emptyMessage.textContent = 'Không tìm thấy bài thi nào phù hợp với bộ lọc hiện tại.';
                } else {
                    this.emptyMessage.textContent = 'Bạn chưa nộp hoặc lưu bản nháp tác phẩm nào. Hãy tham gia cuộc thi ngay hôm nay!';
                }
                return;
            }

            this.emptyState.style.display = 'none';

            filtered.forEach(sub => {
                const card = this.createCardElement(sub);
                this.grid.appendChild(card);
            });
        }

        createCardElement(sub) {
            const card = document.createElement('article');
            card.className = 'submission-card';

            const statusClass = sub.status || 'submitted';
            const statusLabel = this.getStatusLabel(sub.status);
            const formattedDate = this.formatDate(sub.submitted_at || sub.created_at);
            const imageSrc = sub.thumbnail_url || sub.image_hd_url || '';
            const isDraft = sub.status === 'draft';

            let mediaHtml = '';
            if (imageSrc) {
                mediaHtml = `<img src="${this.escapeHtml(imageSrc)}" alt="${this.escapeHtml(sub.title || 'Submission')}" class="card-image" loading="lazy">`;
            } else {
                mediaHtml = `
                    <div class="no-image-placeholder">
                        <span>📷</span>
                        <p>${isDraft ? 'Bản nháp chưa có ảnh' : 'Không có ảnh hiển thị'}</p>
                    </div>
                `;
            }

            let scoreBadgeHtml = '';
            if (sub.final_score !== null && sub.final_score !== undefined) {
                scoreBadgeHtml = `
                    <div class="score-badge">
                        <span>★</span> ${Number(sub.final_score).toFixed(1)} / 100
                    </div>
                `;
            }

            let aiRiskChip = '';
            if (sub.ai_flag) {
                const riskLevel = sub.ai_flag.risk_level || 'safe';
                if (riskLevel === 'safe') {
                    aiRiskChip = `<span class="info-chip" style="color:var(--accent-emerald);">🛡️ Phim gốc hợp lệ</span>`;
                } else if (riskLevel === 'high' || riskLevel === 'high_risk') {
                    aiRiskChip = `<span class="info-chip" style="color:var(--accent-rose);">⚠️ Cảnh báo AI</span>`;
                } else {
                    aiRiskChip = `<span class="info-chip" style="color:var(--accent-amber);">🔍 AI thẩm định</span>`;
                }
            }

            card.innerHTML = `
                <div class="card-media">
                    ${mediaHtml}
                    <div class="card-badges">
                        <span class="status-badge ${this.escapeHtml(statusClass)}">${this.escapeHtml(statusLabel)}</span>
                        ${scoreBadgeHtml}
                    </div>
                </div>
                <div class="card-body">
                    <div class="contest-meta">
                        <span class="contest-title-tag">${this.escapeHtml(sub.contest_title || 'Analog Contest')}</span>
                        <span>•</span>
                        <span>${this.escapeHtml(sub.round_title || ('Vòng ' + (sub.round_number || '1')))}</span>
                    </div>
                    <h3 class="card-title">${this.escapeHtml(sub.title || 'Chưa đặt tiêu đề')}</h3>
                    <p class="card-desc">${this.escapeHtml(sub.story_description || 'Không có mô tả kèm theo.')}</p>
                    
                    <div class="card-info-chips">
                        <span class="info-chip">📅 ${formattedDate}</span>
                        ${aiRiskChip}
                    </div>

                    <div class="card-footer">
                        <span class="card-date">Mã bài: #${sub.id}</span>
                        <div class="card-actions">
                            ${isDraft ? `
                                <a href="/submit?draft_id=${sub.id}" class="btn-card-edit" title="Sửa bản nháp này">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                                    Sửa Draft
                                </a>
                            ` : ''}
                            <a href="/my-submissions/${sub.id}" class="btn-card-detail">
                                Xem Chi Tiết →
                            </a>
                        </div>
                    </div>
                </div>
            `;

            return card;
        }

        getStatusLabel(status) {
            switch (status) {
                case 'draft': return 'Bản Nháp';
                case 'submitted': return 'Đã Nộp';
                case 'under_review': return 'Đang Chấm';
                case 'graded': return 'Đã Có Điểm';
                case 'rejected': return 'Bị Từ Chối';
                case 'flagged': return 'Cần Lưu Ý';
                default: return status || 'Đã Nộp';
            }
        }

        formatDate(isoString) {
            if (!isoString) return 'Chưa ghi nhận';
            try {
                const date = new Date(isoString);
                return date.toLocaleDateString('vi-VN', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric'
                });
            } catch (e) {
                return isoString;
            }
        }

        escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        showToast(message, type = 'info') {
            const container = document.getElementById('toastContainer');
            if (!container) return;

            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            container.appendChild(toast);

            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(10px)';
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }
    }

    new MySubmissionsApp();
});
