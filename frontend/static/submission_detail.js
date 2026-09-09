/**
 * Submission Detail JavaScript Handler
 * Loads complete submission details from backend API and renders all visual components
 */

document.addEventListener('DOMContentLoaded', () => {
    class SubmissionDetailApp {
        constructor() {
            this.submissionId = this.extractSubmissionId();
            
            // DOM Elements
            this.loadingState = document.getElementById('loadingState');
            this.errorState = document.getElementById('errorState');
            this.errorMessage = document.getElementById('errorMessage');
            this.detailContent = document.getElementById('detailContent');
            this.draftBanner = document.getElementById('draftBanner');
            this.btnEditDraft = document.getElementById('btnEditDraft');
            
            // Visual elements
            this.detailImage = document.getElementById('detailImage');
            this.noImageBox = document.getElementById('noImageBox');
            this.btnOpenFullImage = document.getElementById('btnOpenFullImage');
            
            // Specs
            this.specDimensions = document.getElementById('specDimensions');
            this.specFileSize = document.getElementById('specFileSize');
            this.specFileHash = document.getElementById('specFileHash');
            
            // Info Header
            this.detailContestBadge = document.getElementById('detailContestBadge');
            this.detailStatusBadge = document.getElementById('detailStatusBadge');
            this.detailTitle = document.getElementById('detailTitle');
            this.detailRoundName = document.getElementById('detailRoundName');
            this.detailSubmittedDate = document.getElementById('detailSubmittedDate');
            this.detailSubmissionId = document.getElementById('detailSubmissionId');
            this.detailStory = document.getElementById('detailStory');
            
            // Metadata
            this.metaFilmStock = document.getElementById('metaFilmStock');
            this.metaFilmIso = document.getElementById('metaFilmIso');
            this.metaCamera = document.getElementById('metaCamera');
            this.metaLens = document.getElementById('metaLens');
            this.metaLab = document.getElementById('metaLab');
            this.metaScanner = document.getElementById('metaScanner');
            this.metaProcess = document.getElementById('metaProcess');
            this.metaLocation = document.getElementById('metaLocation');
            
            // Scores & AI
            this.finalScoreContainer = document.getElementById('finalScoreContainer');
            this.finalScoreVal = document.getElementById('finalScoreVal');
            this.scoresContent = document.getElementById('scoresContent');
            this.aiReportContent = document.getElementById('aiReportContent');
            this.aiPollTimer = null;
            this.aiPollAttempts = 0;
            
            this.userNameEl = document.getElementById('userName');
            this.userAvatarEl = document.getElementById('userAvatar');

            this.init();
        }

        extractSubmissionId() {
            // Check query param first
            const params = new URLSearchParams(window.location.search);
            if (params.get('id')) return params.get('id');
            if (params.get('submission_id')) return params.get('submission_id');

            // Extract from URL path (/my-submissions/123 or /submissions/detail/123)
            const parts = window.location.pathname.split('/').filter(Boolean);
            const lastPart = parts[parts.length - 1];
            if (!isNaN(lastPart)) {
                return lastPart;
            }
            return null;
        }

        init() {
            this.setupUser();
            if (!this.submissionId) {
                this.showError('The submission ID was not found in the URL.');
                return;
            }
            this.fetchDetail();
        }

        setupUser() {
            const session = window.AuthSession ? window.AuthSession.getSession() : {};
            const user = session.user || {};
            if (user && (user.username || user.full_name)) {
                const displayName = user.full_name || user.username;
                if (this.userNameEl) this.userNameEl.textContent = displayName;
                if (this.userAvatarEl) this.userAvatarEl.textContent = displayName.charAt(0).toUpperCase();
            }
        }

        async fetchDetail() {
            this.loadingState.style.display = 'block';
            this.errorState.style.display = 'none';
            this.detailContent.style.display = 'none';

            try {
                const session = window.AuthSession ? window.AuthSession.getSession() : {};
                if (!session.token) {
                    this.showError('You must log in to view submission details.');
                    return;
                }

                const data = await window.apiClient.get(`/submissions/${this.submissionId}`);
                this.renderData(data);
            } catch (error) {
                console.error('Failed to fetch submission detail:', error);
                this.showError(error.message || 'Unable to load submission details.');
            } finally {
                this.loadingState.style.display = 'none';
            }
        }

        renderData(data) {
            this.detailContent.style.display = 'block';

            // Top Draft Banner
            const isDraft = data.status === 'draft';
            if (isDraft) {
                this.draftBanner.style.display = 'flex';
                this.btnEditDraft.href = `/submit?draft_id=${data.id}`;
            } else {
                this.draftBanner.style.display = 'none';
            }

            // Media
            const file = data.file || {};
            const imageSrc = file.image_hd_url || file.thumbnail_url;
            if (imageSrc) {
                this.detailImage.src = imageSrc;
                this.detailImage.style.display = 'block';
                this.noImageBox.style.display = 'none';
                this.btnOpenFullImage.href = imageSrc;
                this.btnOpenFullImage.style.display = 'inline-flex';
            } else {
                this.detailImage.style.display = 'none';
                this.noImageBox.style.display = 'block';
                this.btnOpenFullImage.style.display = 'none';
            }

            // Specs
            if (file.width_px && file.height_px) {
                this.specDimensions.textContent = `${file.width_px} × ${file.height_px} px`;
            } else {
                this.specDimensions.textContent = 'Not available';
            }
            this.specFileSize.textContent = file.file_size_bytes ? this.formatFileSize(file.file_size_bytes) : 'Not recorded';
            this.specFileHash.textContent = file.file_hash || 'No SHA-256 hash';

            // Header info
            const contest = data.contest || {};
            const round = data.round || {};
            this.detailContestBadge.textContent = contest.title || 'Analog Photography Contest';
            this.detailStatusBadge.textContent = this.getStatusLabel(data.status);
            this.detailStatusBadge.className = `status-badge-lg ${data.status || 'submitted'}`;
            this.detailTitle.textContent = data.title || 'Untitled';
            this.detailRoundName.textContent = round.title || `Round #${data.round_id || 1}`;
            this.detailSubmittedDate.textContent = this.formatDate(data.submitted_at || data.created_at);
            this.detailSubmissionId.textContent = `#${data.id}`;
            this.detailStory.textContent = data.story_description || 'The author did not provide a description or story.';

            // Metadata
            const meta = data.film_metadata || {};
            this.metaFilmStock.textContent = meta.film_stock || 'Not provided';
            this.metaFilmIso.textContent = meta.film_iso ? `ISO ${meta.film_iso}` : 'Not provided';
            this.metaCamera.textContent = meta.camera_body || 'Not provided';
            this.metaLens.textContent = meta.lens || 'Not provided';
            this.metaLab.textContent = meta.lab_name || 'Not provided';
            this.metaScanner.textContent = meta.scanner_info || 'Not provided';
            this.metaProcess.textContent = meta.development_process || 'C-41 (Default)';
            this.metaLocation.textContent = meta.taken_at_location || 'Not provided';

            // Scores & Feedbacks
            this.renderScoresAndFeedbacks(data);

            // AI Authenticity Report
            this.renderAIReport(data);
        }

        renderScoresAndFeedbacks(data) {
            const scores = data.scores || [];
            const feedbacks = data.feedbacks || [];
            const finalScore = data.final_score;

            if (finalScore !== null && finalScore !== undefined) {
                this.finalScoreContainer.style.display = 'flex';
                this.finalScoreVal.textContent = Number(finalScore).toFixed(1);
            } else {
                this.finalScoreContainer.style.display = 'none';
            }

            if (scores.length === 0 && feedbacks.length === 0 && finalScore === null) {
                this.scoresContent.innerHTML = `
                    <div class="waiting-score-box">
                        <span>⏳</span>
                        <h4>Under Review</h4>
                        <p>This work is being evaluated by the judges. Scores and detailed feedback will appear here after judging ends.</p>
                    </div>
                `;
                return;
            }

            let html = '';

            // Criteria scores table
            if (scores.length > 0) {
                html += `
                    <table class="criteria-table">
                        <thead>
                            <tr>
                                <th>Criterion</th>
                                <th>Weight</th>
                                <th>Score</th>
                                <th>Judge Feedback</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${scores.map(s => `
                                <tr>
                                    <td><strong>${this.escapeHtml(s.criteria_name || 'Criterion')}</strong></td>
                                    <td>${(s.weight || 1.0) * 100}%</td>
                                    <td class="criteria-score-val">${Number(s.score_value || 0).toFixed(1)} / ${s.max_score || 100}</td>
                                    <td>${this.escapeHtml(s.comment || '—')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }

            // Feedbacks
            if (feedbacks.length > 0) {
                html += feedbacks.map(fb => `
                    <div class="feedback-card">
                        <h4>💬 Overall Judge Feedback</h4>
                        <p>${this.escapeHtml(fb.summary_feedback || fb.general_comment || '')}</p>
                          ${fb.final_recommendation ? `<p style="margin-top:6px; color:var(--accent-cyan); font-weight:600;">✨ Recommendation: ${this.escapeHtml(fb.final_recommendation)}</p>` : ''}
                    </div>
                `).join('');
            }

            this.scoresContent.innerHTML = html;
        }

        renderAIReport(data) {
            const aiFlag = data.ai_flag || {};
            const riskLevel = aiFlag.risk_level || 'safe';
            const aiScore = aiFlag.confidence_score !== undefined && aiFlag.confidence_score !== null
                ? aiFlag.confidence_score
                : (aiFlag.ai_score !== undefined && aiFlag.ai_score !== null ? aiFlag.ai_score : 0);
            let status = aiFlag.status || (data.status === 'submitted' ? 'pending' : 'completed');

            if (status === 'pending') {
                if (this.aiPollAttempts >= 12) {
                    status = 'failed';
                } else {
                    this.aiPollAttempts += 1;
                    if (this.aiPollTimer) window.clearTimeout(this.aiPollTimer);
                    this.aiPollTimer = window.setTimeout(() => {
                        this.aiPollTimer = null;
                        this.fetchDetail();
                    }, 2500);
                }
            } else if (this.aiPollTimer) {
                window.clearTimeout(this.aiPollTimer);
                this.aiPollTimer = null;
                this.aiPollAttempts = 0;
            }

            let badgeHtml = '';
            let explanation = '';

            if (status === 'pending') {
                badgeHtml = `<span class="ai-status-tag" style="background:rgba(100,116,139,0.2); color:var(--text-secondary);">⏳ AI Processing (Pending)...</span>`;
                explanation = 'The system is extracting EXIF data and running checks. Processing does not interrupt your submission.';
            } else if (status === 'failed') {
                badgeHtml = `<span class="ai-status-tag" style="background:rgba(220,38,38,0.15); color:#f87171;">❌ Processing Failed</span>`;
                explanation = 'The automated check failed. A judge will review the work manually.';
            } else if (riskLevel === 'safe' || aiScore < 30) {
                badgeHtml = `<span class="ai-status-tag safe">✓ Safe • Film Authenticity Confirmed</span>`;
                explanation = 'Camera and analog film metadata are valid. No signs of synthetic generation were detected.';
            } else if (riskLevel === 'high' || riskLevel === 'high_risk' || aiScore >= 70) {
                badgeHtml = `<span class="ai-status-tag high">⚠️ AI Alert (High Risk)</span>`;
                explanation = aiFlag.ai_message || 'The system detected unusual metadata or signs requiring manual review.';
            } else {
                badgeHtml = `<span class="ai-status-tag" style="background:rgba(245,158,11,0.15); color:var(--accent-amber);">🔍 Manual Judge Review Required</span>`;
                explanation = 'Some image metadata requires additional manual judge review.';
            }

            this.aiReportContent.innerHTML = `
                <div class="ai-summary-card">
                    <div>
                        <div style="margin-bottom:8px;">${badgeHtml}</div>
                        <p style="font-size:0.875rem; color:var(--text-secondary); line-height:1.6;">${explanation}</p>
                    </div>
                    <div style="text-align:right; flex-shrink:0;">
                        <span style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; display:block;">AI Risk Level</span>
                        <strong style="font-size:1.4rem; color:#ffffff; font-family:'Space Grotesk',sans-serif;">${status === 'pending' || status === 'failed' ? '-' : Number(aiScore).toFixed(0) + '%'}</strong>
                    </div>
                </div>
            `;
        }

        getStatusLabel(status) {
            switch (status) {
                case 'draft': return 'Draft';
                case 'submitted': return 'Submitted';
                case 'under_review': return 'Under Review';
                case 'graded': return 'Graded';
                case 'rejected': return 'Rejected';
                case 'flagged': return 'Needs Review';
                default: return status || 'Submitted';
            }
        }

        formatDate(isoString) {
            if (!isoString) return 'Not recorded';
            try {
                const date = new Date(isoString);
                return date.toLocaleString('vi-VN', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (e) {
                return isoString;
            }
        }

        formatFileSize(bytes) {
            if (!bytes || bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
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

        showError(message) {
            this.loadingState.style.display = 'none';
            this.detailContent.style.display = 'none';
            this.errorState.style.display = 'block';
            this.errorMessage.textContent = message;
        }
    }

    new SubmissionDetailApp();
});
