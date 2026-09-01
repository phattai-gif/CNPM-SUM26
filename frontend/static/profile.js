/**
 * Profile & Portfolio Showcase App (FE01.3)
 * Handles user profile retrieval, real-time updates, portfolio showcase, filtering, and lightbox.
 */

document.addEventListener('DOMContentLoaded', () => {
    class ProfileApp {
        constructor() {
            this.user = null;
            this.submissions = [];
            this.currentFilter = 'all';
            this.searchQuery = '';

            // DOM Elements - Profile Header
            this.profileFullName = document.getElementById('profileFullName');
            this.profileUsername = document.getElementById('profileUsername');
            this.profileEmail = document.getElementById('profileEmail');
            this.profileRolePill = document.getElementById('profileRolePill');
            this.profileBioText = document.getElementById('profileBioText');
            this.profileJoinedDate = document.getElementById('profileJoinedDate');
            this.profileAvatarImg = document.getElementById('profileAvatarImg');
            this.profileAvatarInitial = document.getElementById('profileAvatarInitial');

            // DOM Elements - Navbar
            this.navUserName = document.getElementById('nav-username') || document.getElementById('navUserName');
            this.navUserAvatar = document.getElementById('nav-avatar') || document.getElementById('navUserAvatar');
            this.logoutBtn = document.getElementById('nav-logout') || document.getElementById('logoutBtn');

            // DOM Elements - Stats
            this.statTotalPhotos = document.getElementById('statTotalPhotos');
            this.statApprovedPhotos = document.getElementById('statApprovedPhotos');
            this.statHighScore = document.getElementById('statHighScore');
            this.statContestsJoined = document.getElementById('statContestsJoined');

            // DOM Elements - Tabs
            this.tabBtnPortfolio = document.getElementById('tabBtnPortfolio');
            this.tabBtnAbout = document.getElementById('tabBtnAbout');
            this.panelPortfolio = document.getElementById('panelPortfolio');
            this.panelAbout = document.getElementById('panelAbout');
            this.tabPortfolioCount = document.getElementById('tabPortfolioCount');

            // DOM Elements - Filters & Search
            this.portfolioFilterGroup = document.getElementById('portfolioFilterGroup');
            this.portfolioSearch = document.getElementById('portfolioSearch');
            this.filterCountAll = document.getElementById('filterCountAll');
            this.filterCountPublic = document.getElementById('filterCountPublic');
            this.filterCountHighScore = document.getElementById('filterCountHighScore');
            this.filterCountDraft = document.getElementById('filterCountDraft');

            // DOM Elements - Portfolio Grid & States
            this.portfolioGrid = document.getElementById('portfolioGrid');
            this.portfolioLoading = document.getElementById('portfolioLoading');
            this.portfolioEmpty = document.getElementById('portfolioEmpty');
            this.emptyTitle = document.getElementById('emptyTitle');
            this.emptySubtitle = document.getElementById('emptySubtitle');

            // DOM Elements - Settings Form
            this.profileEditForm = document.getElementById('profileEditForm');
            this.inputFullName = document.getElementById('inputFullName');
            this.inputUsername = document.getElementById('inputUsername');
            this.inputEmail = document.getElementById('inputEmail');
            this.inputRole = document.getElementById('inputRole');
            this.inputAvatarUrl = document.getElementById('inputAvatarUrl');
            this.inputBio = document.getElementById('inputBio');
            this.avatarMiniImg = document.getElementById('avatarMiniImg');
            this.avatarMiniInitial = document.getElementById('avatarMiniInitial');
            this.btnResetForm = document.getElementById('btnResetForm');

            // DOM Elements - Quick Edit Modal
            this.editProfileModal = document.getElementById('editProfileModal');
            this.btnOpenEditModal = document.getElementById('btnOpenEditModal');
            this.modalCloseBtn = document.getElementById('modalCloseBtn');
            this.modalCancelBtn = document.getElementById('modalCancelBtn');
            this.quickEditProfileForm = document.getElementById('quickEditProfileForm');
            this.modalFullName = document.getElementById('modalFullName');
            this.modalAvatarUrl = document.getElementById('modalAvatarUrl');
            this.modalBio = document.getElementById('modalBio');

            // DOM Elements - Lightbox Modal
            this.portfolioLightbox = document.getElementById('portfolioLightbox');
            this.lightboxBackdrop = document.getElementById('lightboxBackdrop');
            this.lightboxCloseBtn = document.getElementById('lightboxCloseBtn');
            this.lightboxImg = document.getElementById('lightboxImg');
            this.lightboxContestTag = document.getElementById('lightboxContestTag');
            this.lightboxTitle = document.getElementById('lightboxTitle');
            this.lightboxStatusBadge = document.getElementById('lightboxStatusBadge');
            this.lightboxScoreBadge = document.getElementById('lightboxScoreBadge');
            this.lightboxStory = document.getElementById('lightboxStory');
            this.lightboxFilmStock = document.getElementById('lightboxFilmStock');
            this.lightboxFilmIso = document.getElementById('lightboxFilmIso');
            this.lightboxCamera = document.getElementById('lightboxCamera');
            this.lightboxLens = document.getElementById('lightboxLens');
            this.lightboxLab = document.getElementById('lightboxLab');
            this.lightboxLocation = document.getElementById('lightboxLocation');
            this.lightboxFullLink = document.getElementById('lightboxFullLink');

            // DOM Elements - Share
            this.btnShareProfile = document.getElementById('btnShareProfile');

            this.init();
        }

        init() {
            this.setupEvents();
            this.loadUserProfile();
            this.loadUserPortfolio();
        }

        setupEvents() {
            // Logout
            if (this.logoutBtn) {
                this.logoutBtn.addEventListener('click', () => {
                    if (window.AuthSession) {
                        window.AuthSession.logout();
                    } else {
                        localStorage.clear();
                        window.location.href = '/auth/login';
                    }
                });
            }

            // Tab navigation
            if (this.tabBtnPortfolio) {
                this.tabBtnPortfolio.addEventListener('click', () => this.switchTab('portfolio'));
            }
            if (this.tabBtnAbout) {
                this.tabBtnAbout.addEventListener('click', () => this.switchTab('about'));
            }

            // Filter buttons
            if (this.portfolioFilterGroup) {
                this.portfolioFilterGroup.addEventListener('click', (e) => {
                    const btn = e.target.closest('.filter-pill-btn');
                    if (!btn) return;

                    this.portfolioFilterGroup.querySelectorAll('.filter-pill-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.currentFilter = btn.dataset.filter || 'all';
                    this.renderPortfolio();
                });
            }

            // Search input
            if (this.portfolioSearch) {
                this.portfolioSearch.addEventListener('input', (e) => {
                    this.searchQuery = e.target.value.toLowerCase().trim();
                    this.renderPortfolio();
                });
            }

            // Settings Form Submit
            if (this.profileEditForm) {
                this.profileEditForm.addEventListener('submit', (e) => this.handleProfileSubmit(e, 'main'));
            }

            // Quick Edit Modal events
            if (this.btnOpenEditModal) {
                this.btnOpenEditModal.addEventListener('click', () => this.openEditModal());
            }
            if (this.modalCloseBtn) {
                this.modalCloseBtn.addEventListener('click', () => this.closeEditModal());
            }
            if (this.modalCancelBtn) {
                this.modalCancelBtn.addEventListener('click', () => this.closeEditModal());
            }
            if (this.quickEditProfileForm) {
                this.quickEditProfileForm.addEventListener('submit', (e) => this.handleProfileSubmit(e, 'quick'));
            }

            // Reset Form button
            if (this.btnResetForm) {
                this.btnResetForm.addEventListener('click', () => this.populateFormFromUser());
            }

            // Live avatar preview in Settings Form
            if (this.inputAvatarUrl) {
                this.inputAvatarUrl.addEventListener('input', (e) => {
                    this.updateMiniAvatarPreview(e.target.value);
                });
            }

            // Lightbox close events
            if (this.lightboxCloseBtn) {
                this.lightboxCloseBtn.addEventListener('click', () => this.closeLightbox());
            }
            if (this.lightboxBackdrop) {
                this.lightboxBackdrop.addEventListener('click', () => this.closeLightbox());
            }
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.closeLightbox();
                    this.closeEditModal();
                }
            });

            // Share profile link
            if (this.btnShareProfile) {
                this.btnShareProfile.addEventListener('click', () => {
                    if (navigator.clipboard) {
                        navigator.clipboard.writeText(window.location.href)
                            .then(() => this.showToast('Đã sao chép liên kết hồ sơ vào bộ nhớ tạm!', 'success'))
                            .catch(() => this.showToast('Không thể sao chép liên kết.', 'error'));
                    } else {
                        this.showToast('Liên kết: ' + window.location.href, 'info');
                    }
                });
            }
        }

        switchTab(tabName) {
            if (tabName === 'portfolio') {
                this.tabBtnPortfolio.classList.add('active');
                this.tabBtnAbout.classList.remove('active');
                this.panelPortfolio.style.display = 'block';
                this.panelAbout.style.display = 'none';
            } else {
                this.tabBtnPortfolio.classList.remove('active');
                this.tabBtnAbout.classList.add('active');
                this.panelPortfolio.style.display = 'none';
                this.panelAbout.style.display = 'block';
            }
        }

        async loadUserProfile() {
            try {
                const session = window.AuthSession ? window.AuthSession.getSession() : {};
                if (!session.token) {
                    this.renderGuestState();
                    return;
                }

                // Call API GET /auth/me
                const response = await window.apiClient.get('/auth/me');
                this.user = response.user || session.user || {};

                this.renderUserHeader(this.user);
                this.populateFormFromUser();
            } catch (error) {
                console.error('Failed to load user profile:', error);
                const session = window.AuthSession ? window.AuthSession.getSession() : {};
                if (session.user) {
                    this.user = session.user;
                    this.renderUserHeader(this.user);
                    this.populateFormFromUser();
                } else {
                    this.renderGuestState();
                }
            }
        }

        renderUserHeader(user) {
            const displayName = user.full_name || user.username || 'Nhiếp Ảnh Gia';
            const username = user.username ? `@${user.username}` : '@photographer';
            const email = user.email || 'Chưa cập nhật email';
            const rawRole = (user.role || 'participant').toLowerCase();
            const roleDisplay = rawRole === 'organizer' ? 'ORGANIZER' : (user.role || 'Participant').toUpperCase();
            const bio = user.bio || 'Chưa cập nhật tiểu sử nghệ sĩ. Hãy bấm "Chỉnh Sửa Hồ Sơ" để giới thiệu bản thân và chia sẻ niềm đam mê ảnh phim analog!';
            const initial = displayName.charAt(0).toUpperCase();

            this.profileFullName.textContent = displayName;
            this.profileUsername.textContent = username;
            this.profileEmail.textContent = email;
            
            if (this.profileRolePill) {
                this.profileRolePill.textContent = roleDisplay;
                this.profileRolePill.className = `role-pill role-${rawRole}`;
            }

            const btnDash = document.getElementById('btnOrganizerDashboard');
            if (btnDash) {
                btnDash.style.display = (rawRole === 'organizer' || rawRole === 'admin') ? 'inline-flex' : 'none';
            }

            this.profileBioText.textContent = bio;

            if (user.created_at) {
                const joinDate = new Date(user.created_at);
                this.profileJoinedDate.textContent = `Thành viên từ ${joinDate.getFullYear()}`;
            } else {
                this.profileJoinedDate.textContent = 'Thành viên 2026';
            }

            // Render Avatar
            if (user.avatar_url && user.avatar_url.trim()) {
                this.profileAvatarImg.src = user.avatar_url;
                this.profileAvatarImg.style.display = 'block';
                this.profileAvatarInitial.style.display = 'none';
            } else {
                this.profileAvatarImg.style.display = 'none';
                this.profileAvatarInitial.style.display = 'flex';
                this.profileAvatarInitial.textContent = initial;
            }

            // Sync with navbar
            if (this.navUserName) this.navUserName.textContent = displayName;
            if (this.navUserAvatar) this.navUserAvatar.textContent = initial;
        }

        populateFormFromUser() {
            if (!this.user) return;
            if (this.inputFullName) this.inputFullName.value = this.user.full_name || '';
            if (this.inputUsername) this.inputUsername.value = this.user.username || '';
            if (this.inputEmail) this.inputEmail.value = this.user.email || '';
            if (this.inputRole) this.inputRole.value = (this.user.role || 'Participant').toUpperCase();
            if (this.inputAvatarUrl) this.inputAvatarUrl.value = this.user.avatar_url || '';
            if (this.inputBio) this.inputBio.value = this.user.bio || '';

            this.updateMiniAvatarPreview(this.user.avatar_url);
        }

        updateMiniAvatarPreview(url) {
            if (url && url.trim()) {
                this.avatarMiniImg.src = url;
                this.avatarMiniImg.style.display = 'block';
                this.avatarMiniInitial.style.display = 'none';
            } else {
                this.avatarMiniImg.style.display = 'none';
                this.avatarMiniInitial.style.display = 'block';
                const initial = (this.user?.full_name || this.user?.username || 'U').charAt(0).toUpperCase();
                this.avatarMiniInitial.textContent = initial;
            }
        }

        openEditModal() {
            if (!this.user) return;
            this.modalFullName.value = this.user.full_name || '';
            this.modalAvatarUrl.value = this.user.avatar_url || '';
            this.modalBio.value = this.user.bio || '';
            this.editProfileModal.style.display = 'flex';
        }

        closeEditModal() {
            if (this.editProfileModal) {
                this.editProfileModal.style.display = 'none';
            }
        }

        async handleProfileSubmit(event, source = 'main') {
            event.preventDefault();

            let fullName = '';
            let avatarUrl = '';
            let bio = '';

            if (source === 'main') {
                fullName = this.inputFullName.value.trim();
                avatarUrl = this.inputAvatarUrl.value.trim();
                bio = this.inputBio.value.trim();
            } else {
                fullName = this.modalFullName.value.trim();
                avatarUrl = this.modalAvatarUrl.value.trim();
                bio = this.modalBio.value.trim();
            }

            if (!fullName) {
                this.showToast('Vui lòng nhập họ và tên hiển thị.', 'error');
                return;
            }

            try {
                const payload = {
                    full_name: fullName,
                    avatar_url: avatarUrl,
                    bio: bio
                };

                const response = await window.apiClient.put('/auth/profile', payload);
                const updatedUser = response.user || { ...this.user, ...payload };

                this.user = updatedUser;
                this.renderUserHeader(this.user);
                this.populateFormFromUser();

                // Update session storage
                if (window.AuthSession) {
                    window.AuthSession.setSession({
                        token: window.AuthSession.getSession().token,
                        user: updatedUser,
                        role: updatedUser.role
                    });
                }

                this.closeEditModal();
                this.showToast('Cập nhật thông tin hồ sơ thành công!', 'success');
            } catch (error) {
                console.error('Failed to update profile:', error);
                this.showToast(error.message || 'Không thể cập nhật hồ sơ. Vui lòng thử lại.', 'error');
            }
        }

        renderGuestState() {
            this.profileFullName.textContent = 'Khách truy cập';
            this.profileUsername.textContent = '@guest';
            this.profileEmail.textContent = 'Chưa đăng nhập';
            this.profileRolePill.textContent = 'GUEST';
            this.profileBioText.innerHTML = 'Vui lòng <a href="/auth/login" style="color:var(--accent-amber); font-weight:700;">Đăng Nhập</a> để quản lý hồ sơ và tác phẩm nhiếp ảnh cá nhân.';
            this.statTotalPhotos.textContent = '0';
            this.statApprovedPhotos.textContent = '0';
            this.statHighScore.textContent = '--';
            this.statContestsJoined.textContent = '0';
            this.portfolioLoading.style.display = 'none';
            this.portfolioEmpty.style.display = 'block';
            this.emptyTitle.textContent = 'Bạn chưa đăng nhập';
            this.emptySubtitle.textContent = 'Đăng nhập hoặc đăng ký tài khoản để khám phá tính năng quản lý hồ sơ nghệ sĩ và tác phẩm nhiếp ảnh phim analog.';
        }

        async loadUserPortfolio() {
            this.portfolioLoading.style.display = 'block';
            this.portfolioEmpty.style.display = 'none';
            this.portfolioGrid.innerHTML = '';

            try {
                const session = window.AuthSession ? window.AuthSession.getSession() : {};
                if (!session.token) {
                    this.portfolioLoading.style.display = 'none';
                    return;
                }

                const data = await window.apiClient.get('/submissions/my');
                this.submissions = data.submissions || [];

                this.updatePortfolioStats();
                this.renderPortfolio();
            } catch (error) {
                console.error('Failed to load user submissions for portfolio:', error);
                this.portfolioLoading.style.display = 'none';
                this.portfolioEmpty.style.display = 'block';
                this.emptyTitle.textContent = 'Chưa thể tải tác phẩm';
                this.emptySubtitle.textContent = 'Không thể kết nối đến thư viện ảnh. Vui lòng kiểm tra lại kết nối mạng.';
            } finally {
                this.portfolioLoading.style.display = 'none';
            }
        }

        updatePortfolioStats() {
            const total = this.submissions.length;
            const approved = this.submissions.filter(s => s.status === 'graded' || s.status === 'submitted' || s.status === 'under_review').length;
            const drafts = this.submissions.filter(s => s.status === 'draft').length;
            const highScores = this.submissions.filter(s => s.final_score !== null && Number(s.final_score) >= 80).length;

            // Compute highest score
            let maxScore = null;
            this.submissions.forEach(s => {
                if (s.final_score !== null && s.final_score !== undefined) {
                    const score = Number(s.final_score);
                    if (maxScore === null || score > maxScore) {
                        maxScore = score;
                    }
                }
            });

            // Compute unique contests
            const uniqueContests = new Set();
            this.submissions.forEach(s => {
                if (s.contest_id) uniqueContests.add(s.contest_id);
                else if (s.contest_title) uniqueContests.add(s.contest_title);
            });

            this.statTotalPhotos.textContent = total;
            this.statApprovedPhotos.textContent = approved;
            this.statHighScore.textContent = maxScore !== null ? `${maxScore.toFixed(1)}/100` : '--';
            this.statContestsJoined.textContent = uniqueContests.size;

            if (this.tabPortfolioCount) this.tabPortfolioCount.textContent = total;
            if (this.filterCountAll) this.filterCountAll.textContent = total;
            if (this.filterCountPublic) this.filterCountPublic.textContent = approved;
            if (this.filterCountHighScore) this.filterCountHighScore.textContent = highScores;
            if (this.filterCountDraft) this.filterCountDraft.textContent = drafts;
        }

        renderPortfolio() {
            const filtered = this.submissions.filter(sub => {
                // Tab filter
                let matchesFilter = true;
                if (this.currentFilter === 'public') {
                    matchesFilter = sub.status === 'submitted' || sub.status === 'under_review' || sub.status === 'graded';
                } else if (this.currentFilter === 'highscore') {
                    matchesFilter = sub.final_score !== null && Number(sub.final_score) >= 80;
                } else if (this.currentFilter === 'draft') {
                    matchesFilter = sub.status === 'draft';
                }

                // Search query
                let matchesSearch = true;
                if (this.searchQuery) {
                    const title = (sub.title || '').toLowerCase();
                    const contest = (sub.contest_title || '').toLowerCase();
                    const round = (sub.round_title || '').toLowerCase();
                    matchesSearch = title.includes(this.searchQuery) || contest.includes(this.searchQuery) || round.includes(this.searchQuery);
                }

                return matchesFilter && matchesSearch;
            });

            this.portfolioGrid.innerHTML = '';

            if (filtered.length === 0) {
                this.portfolioEmpty.style.display = 'block';
                if (this.searchQuery || this.currentFilter !== 'all') {
                    this.emptyTitle.textContent = 'Không tìm thấy tác phẩm';
                    this.emptySubtitle.textContent = 'Không có tác phẩm nào phù hợp với bộ lọc hoặc từ khóa tìm kiếm của bạn.';
                } else {
                    this.emptyTitle.textContent = 'Chưa có tác phẩm nào trong portfolio';
                    this.emptySubtitle.textContent = 'Hãy gửi bài dự thi đầu tiên của bạn để trưng bày tác phẩm nghệ thuật tại đây.';
                }
                return;
            }

            this.portfolioEmpty.style.display = 'none';

            filtered.forEach(sub => {
                const card = this.createPortfolioCard(sub);
                this.portfolioGrid.appendChild(card);
            });
        }

        createPortfolioCard(sub) {
            const card = document.createElement('article');
            card.className = 'portfolio-card';

            const statusClass = sub.status || 'submitted';
            const statusLabel = this.getStatusLabel(sub.status);
            const imageSrc = sub.thumbnail_url || sub.image_hd_url || '';
            const isDraft = sub.status === 'draft';
            const formattedDate = this.formatDate(sub.submitted_at || sub.created_at);

            let mediaHtml = '';
            if (imageSrc) {
                mediaHtml = `
                    <img src="${this.escapeHtml(imageSrc)}" alt="${this.escapeHtml(sub.title || 'Portfolio Item')}" class="portfolio-card-img" loading="lazy">
                    <div class="card-media-overlay">
                        <span class="btn-preview-quick">🔍 Xem nhanh</span>
                    </div>
                `;
            } else {
                mediaHtml = `
                    <div class="no-img-placeholder">
                        <span>📷</span>
                        <p>${isDraft ? 'Bản nháp chưa tải ảnh' : 'Không có ảnh'}</p>
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

            // Tags for film and gear if available
            let gearTagsHtml = '';
            if (sub.round_title || sub.round_number) {
                gearTagsHtml += `<span class="film-gear-tag">🎯 ${this.escapeHtml(sub.round_title || ('Vòng ' + sub.round_number))}</span>`;
            }
            if (sub.ai_flag) {
                const riskLevel = sub.ai_flag.risk_level || 'safe';
                if (riskLevel === 'safe') {
                    gearTagsHtml += `<span class="film-gear-tag" style="color:var(--accent-emerald);">🛡️ Phim gốc</span>`;
                }
            }

            card.innerHTML = `
                <div class="portfolio-card-media" title="Nhấn để xem chi tiết ảnh">
                    ${mediaHtml}
                    <div class="card-top-badges">
                        <span class="status-badge ${this.escapeHtml(statusClass)}">${this.escapeHtml(statusLabel)}</span>
                        ${scoreBadgeHtml}
                    </div>
                </div>
                <div class="portfolio-card-content">
                    <span class="portfolio-card-contest">${this.escapeHtml(sub.contest_title || 'Analog Film Contest')}</span>
                    <h3 class="portfolio-card-title">${this.escapeHtml(sub.title || 'Chưa đặt tiêu đề')}</h3>
                    <p class="portfolio-card-story">${this.escapeHtml(sub.story_description || 'Không có mô tả kèm theo.')}</p>
                    
                    <div class="portfolio-card-tags">
                        ${gearTagsHtml}
                    </div>

                    <div class="portfolio-card-footer">
                        <span class="portfolio-card-date">${formattedDate}</span>
                        <div class="portfolio-card-links">
                            ${isDraft ? `
                                <a href="/submit?draft_id=${sub.id}" class="btn-card-view" style="color:var(--accent-amber); margin-right:8px;">Sửa Draft</a>
                            ` : ''}
                            <a href="/my-submissions/${sub.id}" class="btn-card-view">Xem chi tiết →</a>
                        </div>
                    </div>
                </div>
            `;

            // Add click listener for quickview / lightbox
            const mediaEl = card.querySelector('.portfolio-card-media');
            if (mediaEl) {
                mediaEl.addEventListener('click', () => this.openLightbox(sub));
            }

            return card;
        }

        openLightbox(sub) {
            const imageSrc = sub.image_hd_url || sub.thumbnail_url || '';
            this.lightboxImg.src = imageSrc;
            this.lightboxTitle.textContent = sub.title || 'Tác Phẩm Nhiếp Ảnh';
            this.lightboxContestTag.textContent = sub.contest_title || 'Cuộc Thi Analog Film';
            this.lightboxStory.textContent = sub.story_description || 'Không có câu chuyện tác phẩm kèm theo.';

            // Status & Score badges
            this.lightboxStatusBadge.className = `status-badge ${sub.status || 'submitted'}`;
            this.lightboxStatusBadge.textContent = this.getStatusLabel(sub.status);

            if (sub.final_score !== null && sub.final_score !== undefined) {
                this.lightboxScoreBadge.style.display = 'inline-flex';
                this.lightboxScoreBadge.textContent = `★ ${Number(sub.final_score).toFixed(1)} / 100`;
            } else {
                this.lightboxScoreBadge.style.display = 'none';
            }

            // Fill Film Metadata
            this.lightboxFilmStock.textContent = sub.film_stock || 'Chưa cập nhật';
            this.lightboxFilmIso.textContent = sub.film_iso || '--';
            this.lightboxCamera.textContent = sub.camera_body || 'Chưa cập nhật';
            this.lightboxLens.textContent = sub.lens || '--';
            this.lightboxLab.textContent = sub.lab_name || '--';
            this.lightboxLocation.textContent = sub.taken_at_location || '--';

            // Full link
            this.lightboxFullLink.href = `/my-submissions/${sub.id}`;

            this.portfolioLightbox.style.display = 'flex';
        }

        closeLightbox() {
            if (this.portfolioLightbox) {
                this.portfolioLightbox.style.display = 'none';
            }
        }

        getStatusLabel(status) {
            switch (status) {
                case 'draft': return 'Bản Nháp';
                case 'submitted': return 'Đã Nộp';
                case 'under_review': return 'Đang Chấm';
                case 'graded': return 'Đã Có Điểm';
                case 'approved': return 'Đã Phê Duyệt';
                case 'rejected': return 'Bị Từ Chối';
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
            }, 3500);
        }
    }

    new ProfileApp();
});
