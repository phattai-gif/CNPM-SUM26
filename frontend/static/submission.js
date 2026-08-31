/**
 * Submission Form Handler
 * Handles file upload, form validation, and API submission
 */

class SubmissionForm {
    constructor() {
        this.form = document.getElementById('submissionForm');
        this.imageInput = document.getElementById('imageInput');
        this.dragDropZone = document.getElementById('dragDropZone');
        this.imageUploadArea = document.getElementById('imageUploadArea');
        this.imagePreview = document.getElementById('imagePreview');
        this.submitBtn = document.getElementById('submitBtn');
        this.draftBtn = document.getElementById('draftBtn');
        if (this.draftBtn) {
            this.draftBtn.style.position = 'relative';
            this.draftBtn.style.zIndex = '99999';
            this.draftBtn.style.pointerEvents = 'auto';
        }
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.successMessage = document.getElementById('successMessage');
        this.errorMessage = document.getElementById('errorMessage');
        this.progressContainer = document.getElementById('uploadProgress');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.draftStatus = document.getElementById('draftStatus');

        this.selectedImage = null;
        this.selectedImageFile = null;
        this.negativeFilmFile = null;
        this.contactSheetFile = null;
        this.roundsList = [];
        this.session = window.AuthSession.getSession();
        this.authToken = this.session.token;
        this.isSubmitting = false;
        this.draftId = new URLSearchParams(window.location.search).get('draft_id') || new URLSearchParams(window.location.search).get('id') || null;
        this.preferredContestId = new URLSearchParams(window.location.search).get('contest_id') || null;
        this.hasExistingImage = false;
        this.hasExistingNegativeFilm = false;
        this.hasExistingContactSheet = false;

        this.init();
    }

    /**
     * Initialize form event listeners
     */
    init() {
        if (!this.authToken) {
            this.showError('Authentication Error', 'You must be logged in to submit. Please login first.');
            this.submitBtn.disabled = true;
            this.draftBtn.disabled = true;
            return;
        }

        if (this.draftId) {
            this.setupDraftMode();
        }

        // File input events
        this.imageInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.dragDropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dragDropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.dragDropZone.addEventListener('drop', (e) => this.handleFileDrop(e));

        // Form submission
        this.form.addEventListener('submit', (e) => this.handleFormSubmit(e, 'submitted'));
        this.draftBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.handleFormSubmit(e, 'draft');
        });
        // Remove image button
        document.getElementById('removeImageBtn').addEventListener('click', () => this.removeImage());

        // Proof attachment event listeners
        const negativeFilmInput = document.getElementById('negativeFilmInput');
        const contactSheetInput = document.getElementById('contactSheetInput');
        const negativeFilmZone = document.getElementById('negativeFilmZone');
        const contactSheetZone = document.getElementById('contactSheetZone');

        if (negativeFilmInput) {
            negativeFilmInput.addEventListener('change', (e) => this.handleProofFileSelect('negative', e));
        }
        if (contactSheetInput) {
            contactSheetInput.addEventListener('change', (e) => this.handleProofFileSelect('contact_sheet', e));
        }
        if (negativeFilmZone) {
            negativeFilmZone.addEventListener('dragover', (e) => { e.preventDefault(); negativeFilmZone.classList.add('drag-over'); });
            negativeFilmZone.addEventListener('dragleave', () => negativeFilmZone.classList.remove('drag-over'));
            negativeFilmZone.addEventListener('drop', (e) => {
                e.preventDefault();
                negativeFilmZone.classList.remove('drag-over');
                if (e.dataTransfer.files.length > 0) this.processProofFile('negative', e.dataTransfer.files[0]);
            });
        }
        if (contactSheetZone) {
            contactSheetZone.addEventListener('dragover', (e) => { e.preventDefault(); contactSheetZone.classList.add('drag-over'); });
            contactSheetZone.addEventListener('dragleave', () => contactSheetZone.classList.remove('drag-over'));
            contactSheetZone.addEventListener('drop', (e) => {
                e.preventDefault();
                contactSheetZone.classList.remove('drag-over');
                if (e.dataTransfer.files.length > 0) this.processProofFile('contact_sheet', e.dataTransfer.files[0]);
            });
        }
        document.getElementById('removeNegativeFilmBtn')?.addEventListener('click', () => this.removeProofFile('negative'));
        document.getElementById('removeContactSheetBtn')?.addEventListener('click', () => this.removeProofFile('contact_sheet'));

        // Character count
        document.getElementById('titleInput').addEventListener('input', (e) => this.updateCharCount(e, 'titleCount'));
        document.getElementById('descriptionInput').addEventListener('input', (e) => this.updateCharCount(e, 'descriptionCount'));

        // Form reset
        document.getElementById('resetBtn').addEventListener('click', () => this.resetForm());

        // Success/Error actions
        document.getElementById('viewSubmissionBtn')?.addEventListener('click', () => this.viewSubmission());
        document.getElementById('submitAnotherBtn')?.addEventListener('click', () => this.submitAnother());
        document.getElementById('dismissErrorBtn')?.addEventListener('click', () => this.dismissError());

        // Load rounds on page load
        this.loadRounds();
    }

    setupDraftMode() {
        const header = document.querySelector('.submission-header');
        if (header) {
            const banner = document.createElement('div');
            banner.className = 'draft-edit-notice';
            banner.style.cssText = 'background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #f8fafc; padding: 14px 20px; border-radius: 12px; margin-top: 16px; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between;';
            banner.innerHTML = `
                <div>
                    <strong>📝 Đang chỉnh sửa bản nháp #${this.draftId}</strong>
                    <div style="font-size: 0.85rem; color: #cbd5e1; margin-top: 4px;">Bạn có thể cập nhật thông số hoặc nộp bài thi chính thức.</div>
                </div>
                <a href="/my-submissions" style="color: #f59e0b; font-weight: 700; text-decoration: underline; font-size: 0.85rem;">Quay lại danh sách</a>
            `;
            header.appendChild(banner);
        }

        if (this.submitBtn) this.submitBtn.textContent = '✓ Cập Nhật & Nộp Bài';
        if (this.draftBtn) this.draftBtn.textContent = '💾 Cập Nhật Bản Nháp';
        if (this.imageInput) this.imageInput.removeAttribute('required');
    }

    /**
  * Load contest rounds from API
  */
    async loadRounds() {
    const roundSelect = document.getElementById('roundSelect');

    try {
        console.log('[Submission] Loading contests...');

        const tokenKey = 'authToken';
        const token = localStorage.getItem(tokenKey);

        const headers = {
            'Accept': 'application/json'
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch('/auth/contests', {
            method: 'GET',
            headers: headers,
            credentials: 'same-origin'
        });

        console.log(
            '[Submission] /auth/contests status:',
            response.status
        );

        if (!response.ok) {
            throw new Error(
                `Failed to load contests: HTTP ${response.status}`
            );
        }

        const data = await response.json();

        console.log(
            '[Submission] /auth/contests response:',
            data
        );

        const contests = Array.isArray(data.contests)
            ? data.contests
            : [];

        this.roundsList = [];

        contests.forEach((contest) => {
            if (!Array.isArray(contest.rounds)) {
                return;
            }

            contest.rounds.forEach((round) => {
                if (!round || !round.id) {
                    return;
                }

                this.roundsList.push({
                    id: round.id,

                    name:
                        round.name ||
                        round.title ||
                        `Round ${round.round_number || round.id}`,

                    title:
                        round.title ||
                        round.name ||
                        `Round ${round.round_number || round.id}`,

                    deadline: round.deadline || null,

                    status: round.status || '',

                    contest_id: contest.id,

                    contest_name:
                        contest.name ||
                        contest.title ||
                        '',

                    description:
                        round.description || ''
                });
            });
        });

        console.log(
            '[Submission] Loaded rounds:',
            this.roundsList
        );

        this.populateRoundSelect();

        this.showRoundLoadState();

        if (this.draftId) {
            await this.loadDraftData();
        } else {
            this.preselectRoundFromContext();
        }

        if (roundSelect) {
            console.log(
                '[Submission] Round options:',
                roundSelect.options.length
            );
        }

    } catch (error) {
        console.error(
            '[Submission] Could not load rounds:',
            error
        );

        this.roundsList = [];

        this.showRoundLoadState(
            'Không tải được danh sách vòng thi. Vui lòng thử lại sau.'
        );
    }
}

    /**
 * Populate round select dropdown
 */
    populateRoundSelect() {
        const roundSelect = document.getElementById('roundSelect');

        if (!roundSelect) {
            console.warn(
                '[Submission] #roundSelect not found'
            );
            return;
        }

        roundSelect.innerHTML =
            '<option value="">-- Select a round --</option>';

        if (!Array.isArray(this.roundsList)) {
            this.roundsList = [];
        }

        this.roundsList.forEach((round) => {
            const option = document.createElement('option');

            option.value = String(round.id);

            const contestName = round.contest_name
                ? `[${round.contest_name}] `
                : '';

            const deadline = round.deadline
                ? ` - Deadline: ${new Date(
                    round.deadline
                ).toLocaleDateString()}`
                : '';

            option.textContent =
                `${contestName}` +
                `${round.name || round.title || 'Round'}` +
                `${deadline}`;

            roundSelect.appendChild(option);
        });

        console.log(
            `[Submission] Round select populated: ${roundSelect.options.length} options`
        );

        roundSelect.addEventListener(
            'change',
            (event) => {
                this.updateRoundInfo(event.target.value);
            }
        );
    }
    /**
     * Update round info display
     */
    updateRoundInfo(roundId) {
        const roundInfo = document.getElementById('roundInfo');
        const round = this.roundsList.find(r => r.id == roundId);

        if (round) {
            let infoHtml = `<div class="round-detail">`;
            if (round.contest_name) {
                infoHtml += `<strong>Contest:</strong> ${round.contest_name}<br>`;
            }
            infoHtml += `<strong>Deadline:</strong> ${round.deadline ? new Date(round.deadline).toLocaleString() : 'Not specified'}`;
            if (round.description) {
                infoHtml += `<br><strong>Description:</strong> ${round.description}`;
            }
            infoHtml += `</div>`;
            roundInfo.innerHTML = infoHtml;
        } else {
            roundInfo.innerHTML = '';
        }
    }

    /**
     * Handle file selection from input
     */
    handleFileSelect(event) {
        const files = event.target.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    /**
     * Handle drag over event
     */
    handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dragDropZone.classList.add('drag-over');
    }

    /**
     * Handle drag leave event
     */
    handleDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dragDropZone.classList.remove('drag-over');
    }

    /**
     * Handle file drop event
     */
    handleFileDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dragDropZone.classList.remove('drag-over');

        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    /**
     * Process selected image file
     */
    processFile(file) {
        // Validate file
        const validTypes = ['image/jpeg', 'image/png', 'image/tiff', 'image/bmp', 'image/gif'];
        const maxSize = 20 * 1024 * 1024; // 20MB

        if (!validTypes.includes(file.type)) {
            this.showError('Invalid File Type', `File type "${file.type}" is not supported. Please use JPG, PNG, TIFF, BMP, or GIF.`);
            return;
        }

        if (file.size > maxSize) {
            this.showError('File Too Large', `File size (${this.formatFileSize(file.size)}) exceeds 20MB limit.`);
            return;
        }

        this.selectedImageFile = file;

        // Read and display file
        const reader = new FileReader();
        reader.onload = (e) => {
            this.selectedImage = e.target.result;
            this.displayImagePreview(file);
        };
        reader.readAsDataURL(file);
    }

    /**
     * Display image preview and metadata
     */
    displayImagePreview(file) {
        const previewImage = document.getElementById('previewImage');
        const infoFileName = document.getElementById('infoFileName');
        const infoFileSize = document.getElementById('infoFileSize');
        const infoDimensions = document.getElementById('infoDimensions');

        previewImage.src = this.selectedImage;
        infoFileName.textContent = file.name;
        infoFileSize.textContent = this.formatFileSize(file.size);

        // Get image dimensions
        const img = new Image();
        img.onload = () => {
            infoDimensions.textContent = `${img.width} × ${img.height} px`;

            // Try to extract EXIF data
            this.extractAndDisplayExif(file);
        };
        img.src = this.selectedImage;

        // Show preview, hide upload area
        this.imageUploadArea.style.display = 'none';
        this.imagePreview.style.display = 'block';
    }

    /**
     * Extract EXIF data from image
     */
    extractAndDisplayExif(file) {
        const infoExifStatus = document.getElementById('infoExifStatus');

        // Use FileReader to get binary data
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                // Simple EXIF detection - check for EXIF marker (FFE1)
                const arr = new Uint8Array(e.target.result).subarray(0, 4);
                let isExif = false;

                if (arr[0] === 0xFF && arr[1] === 0xD8) {
                    isExif = true;
                }

                if (isExif) {
                    infoExifStatus.textContent = '✓ EXIF data detected (will be analyzed on server)';
                    infoExifStatus.style.color = '#27ae60';
                } else {
                    infoExifStatus.textContent = '⚠ No EXIF data detected';
                    infoExifStatus.style.color = '#f39c12';
                }
            } catch (error) {
                infoExifStatus.textContent = 'Unable to read EXIF data';
            }
        };
        reader.readAsArrayBuffer(file);
    }

    /**
     * Remove selected image
     */
    removeImage() {
        this.selectedImage = null;
        this.selectedImageFile = null;
        this.hasExistingImage = false;
        this.imageInput.value = '';
        this.imageUploadArea.style.display = 'block';
        this.imagePreview.style.display = 'none';
        if (!this.draftId) {
            this.imageInput.setAttribute('required', 'required');
        }
    }

    /**
     * Update character count display
     */
    updateCharCount(event, countElementId) {
        const element = document.getElementById(countElementId);
        const maxLength = event.target.maxLength;
        const currentLength = event.target.value.length;
        element.textContent = `${currentLength}/${maxLength} characters`;
    }

    /**
     * Reset form
     */
    resetForm() {
        this.form.reset();
        this.removeImage();
        this.resetProofFiles();
        document.getElementById('titleCount').textContent = '0/200 characters';
        document.getElementById('descriptionCount').textContent = '0/1000 characters';
        this.draftStatus.style.display = 'none';
        this.dismissError();
        this.successMessage.style.display = 'none';
    }

    /**
     * Validate form
     */
    validateForm() {
        const errors = [];

        // Check round selection
        const roundId = document.getElementById('roundSelect').value;
        if (!roundId) {
            errors.push('Please select a competition round');
        }

        // Check image (allow existing image when editing a draft)
        if (!this.selectedImage && !this.hasExistingImage) {
            errors.push('Please upload an image');
        }

        // Check title
        const title = document.getElementById('titleInput').value.trim();
        if (!title) {
            errors.push('Please enter a title for your photograph');
        }

        // Check terms
        if (!document.getElementById('agreeTerms').checked) {
            errors.push('Please confirm you have the rights to submit this photograph');
        }

        if (errors.length > 0) {
            this.showError('Validation Error', errors.join('<br>'));
            return false;
        }

        return true;
    }

    /**
     * Handle form submission and draft save
     */
    async handleFormSubmit(event, mode = 'submitted') {
        event.preventDefault();

        if (this.isSubmitting) {
            return;
        }

        if (mode !== 'draft' && !this.validateForm()) {
            return;
        }

        if (mode === 'draft') {
            const hasDraftData = Boolean(
                this.selectedImageFile ||
                this.hasExistingImage ||
                document.getElementById('roundSelect').value ||
                document.getElementById('titleInput').value.trim() ||
                document.getElementById('descriptionInput').value.trim()
            );

            if (!hasDraftData) {
                this.showError('Draft Empty', 'Please add a title, image, or contest round before saving a draft.');
                return;
            }
        }

        this.isSubmitting = true;
        this.submitBtn.disabled = true;
        this.draftBtn.disabled = true;
        this.loadingSpinner.style.display = 'flex';
        this.draftStatus.style.display = 'none';

        try {
            const formData = this.buildSubmissionFormData(mode);
            const url = this.draftId ? `/submissions/${this.draftId}` : '/submissions';
            const method = this.draftId ? 'PUT' : 'POST';

            const responseData = await window.apiClient.uploadFormData(url, formData, {
                method,
                onProgress: ({ percent }) => {
                    const label = mode === 'draft' ? 'Saving draft' : 'Uploading submission';
                    this.showProgress(label, percent);
                }
            });

            if (mode === 'draft') {
                this.handleDraftSuccess(responseData);
            } else {
                this.handleSubmissionSuccess(responseData);
            }

        } catch (error) {
            this.showError(mode === 'draft' ? 'Draft Save Failed' : 'Submission Failed', error.message || 'An unexpected error occurred');
        } finally {
            this.loadingSpinner.style.display = 'none';
            this.isSubmitting = false;
            this.submitBtn.disabled = false;
            this.draftBtn.disabled = false;
            this.hideProgress();
        }
    }

    buildSubmissionFormData(mode = 'submitted') {
        const formData = new FormData();
        const title = document.getElementById('titleInput').value.trim();
        const description = document.getElementById('descriptionInput').value.trim();
        const roundId = document.getElementById('roundSelect').value;

        if (roundId) {
            formData.append('round_id', roundId);
        }

        if (title) {
            formData.append('title', title);
        }

        if (description) {
            formData.append('story_description', description);
        }

        const metadataFields = {
            camera_body: document.getElementById('cameraBodies').value.trim() || '',
            lens: document.getElementById('lensInput').value.trim() || '',
            film_stock: document.getElementById('filmStockInput').value.trim() || '',
            film_iso: document.getElementById('filmIsoInput').value.trim() || '',
            lab_name: document.getElementById('labNameInput').value.trim() || '',
            scanner_info: document.getElementById('scannerInfoInput').value.trim() || '',
            development_process: document.getElementById('developmentProcessSelect').value || 'C-41',
            taken_at_location: document.getElementById('locationInput').value.trim() || ''
        };

        Object.entries(metadataFields).forEach(([key, value]) => {
            if (value !== '') {
                formData.append(key, value);
            }
        });

        if (this.selectedImageFile) {
            formData.append('file', this.selectedImageFile, this.selectedImageFile.name);
        }

        // Append proof attachment files
        if (this.negativeFilmFile) {
            formData.append('negative_film', this.negativeFilmFile, this.negativeFilmFile.name);
        }
        if (this.contactSheetFile) {
            formData.append('contact_sheet', this.contactSheetFile, this.contactSheetFile.name);
        }

        formData.append('status', mode === 'draft' ? 'draft' : 'submitted');
        return formData;
    }

    showProgress(label, percent = 0) {
        this.progressContainer.style.display = 'block';
        this.progressFill.style.width = `${percent}%`;
        this.progressText.textContent = `${label}: ${percent}%`;
    }

    hideProgress() {
        this.progressContainer.style.display = 'none';
        this.progressFill.style.width = '0%';
        this.progressText.textContent = '0% uploaded';
    }

    /**
     * Handle successful submission
     */
    handleSubmissionSuccess(data) {
        const submission = data.submission || {};
        const aiWarning = data.ai_warning || {};
        const duplicateWarning = data.duplicate_warning || {};

        // Hide form and show success message
        this.form.style.display = 'none';
        this.successMessage.style.display = 'block';

        // Build success message
        let successText = `
            <strong>Submission ID:</strong> #${submission.id}<br>
            <strong>Title:</strong> ${submission.title}<br>
            <strong>Status:</strong> ${submission.status}
        `;

        // Add AI detection result
        if (aiWarning && aiWarning.ai_score !== undefined) {
            const aiScore = aiWarning.ai_score;
            const aiLevel = aiScore <= 15 ? 'Low Risk' : aiScore <= 50 ? 'Medium Risk' : 'High Risk';
            successText += `<br><br><strong>🤖 AI Detection Result:</strong><br>Score: ${aiScore}/100 (${aiLevel})<br>${aiWarning.ai_message || ''}`;
        }

        // Add duplicate detection result
        if (duplicateWarning) {
            const similarity = Math.round((duplicateWarning.similarity_score || 0) * 100);
            successText += `<br><br><strong>🔍 Duplicate Check:</strong><br>Similarity: ${similarity}%${duplicateWarning.is_duplicate ? ' ⚠️ (Possible duplicate)' : ' ✓ (Unique)'}`;
        }

        document.getElementById('successText').innerHTML = successText;

        // Store submission ID for later reference
        this.currentSubmissionId = submission.id;
    }

    /**
     * Handle draft save success
     */
    handleDraftSuccess(data) {
        const submission = data.submission || {};
        const statusText = submission.status || 'draft';

        this.draftStatus.textContent = `Draft saved successfully • Status: ${statusText}`;
        this.draftStatus.style.display = 'block';
        this.draftStatus.classList.add('status-success');
        this.draftStatus.classList.remove('status-error');
        this.form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    /**
     * View submission details
     */
    viewSubmission() {
        if (this.currentSubmissionId) {
            window.location.href = `/submissions/${this.currentSubmissionId}`;
        }
    }

    /**
     * Submit another photograph
     */
    submitAnother() {
        this.form.style.display = 'block';
        this.successMessage.style.display = 'none';
        this.resetForm();
        window.scrollTo(0, 0);
    }

    /**
     * Show error message
     */
    showError(title, message) {
        document.getElementById('errorMessage').style.display = 'block';
        document.querySelector('#errorMessage h3').textContent = title || '✕ Error';
        document.getElementById('errorText').innerHTML = message || 'An error occurred';
    }

    /**
     * Dismiss error message
     */
    dismissError() {
        this.errorMessage.style.display = 'none';
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    }

    // ============================================================
    // PROOF ATTACHMENT HANDLERS
    // ============================================================

    /**
     * Handle proof file input change event
     */
    handleProofFileSelect(type, event) {
        const files = event.target.files;
        if (files && files.length > 0) {
            this.processProofFile(type, files[0]);
        }
    }

    /**
     * Validate and read a proof file, then display its preview
     */
    processProofFile(type, file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
        const maxSize = 20 * 1024 * 1024; // 20MB

        if (!validTypes.includes(file.type)) {
            this.showError('Invalid File Type', `Proof file type "${file.type}" is not supported. Please use JPG, PNG, or WEBP.`);
            return;
        }
        if (file.size > maxSize) {
            this.showError('File Too Large', `Proof file size (${this.formatFileSize(file.size)}) exceeds 20MB limit.`);
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            if (type === 'negative') {
                this.negativeFilmFile = file;
            } else if (type === 'contact_sheet') {
                this.contactSheetFile = file;
            }
            this.displayProofPreview(type, file, e.target.result);
        };
        reader.readAsDataURL(file);
    }

    /**
     * Display proof file thumbnail preview and file info
     */
    displayProofPreview(type, file, dataUrl) {
        if (type === 'negative') {
            const thumb = document.getElementById('negativeFilmThumb');
            const name = document.getElementById('negativeFilmName');
            const size = document.getElementById('negativeFilmSize');
            const preview = document.getElementById('negativeFilmPreview');
            const zone = document.getElementById('negativeFilmZone');

            if (thumb) thumb.src = dataUrl;
            if (name) name.textContent = file.name;
            if (size) size.textContent = this.formatFileSize(file.size);
            if (zone) zone.style.display = 'none';
            if (preview) preview.style.display = 'flex';

        } else if (type === 'contact_sheet') {
            const thumb = document.getElementById('contactSheetThumb');
            const name = document.getElementById('contactSheetName');
            const size = document.getElementById('contactSheetSize');
            const preview = document.getElementById('contactSheetPreview');
            const zone = document.getElementById('contactSheetZone');

            if (thumb) thumb.src = dataUrl;
            if (name) name.textContent = file.name;
            if (size) size.textContent = this.formatFileSize(file.size);
            if (zone) zone.style.display = 'none';
            if (preview) preview.style.display = 'flex';
        }
    }

    /**
     * Show a read-only proof preview for an existing file URL (from draft)
     */
    _showExistingProofPreview(type, src, label) {
        if (type === 'negative') {
            const thumb = document.getElementById('negativeFilmThumb');
            const name = document.getElementById('negativeFilmName');
            const size = document.getElementById('negativeFilmSize');
            const preview = document.getElementById('negativeFilmPreview');
            const zone = document.getElementById('negativeFilmZone');

            if (thumb) thumb.src = src;
            if (name) name.textContent = label;
            if (size) size.textContent = '';
            if (zone) zone.style.display = 'none';
            if (preview) preview.style.display = 'flex';

        } else if (type === 'contact_sheet') {
            const thumb = document.getElementById('contactSheetThumb');
            const name = document.getElementById('contactSheetName');
            const size = document.getElementById('contactSheetSize');
            const preview = document.getElementById('contactSheetPreview');
            const zone = document.getElementById('contactSheetZone');

            if (thumb) thumb.src = src;
            if (name) name.textContent = label;
            if (size) size.textContent = '';
            if (zone) zone.style.display = 'none';
            if (preview) preview.style.display = 'flex';
        }
    }

    /**
     * Remove a selected proof file and reset its input + preview
     */
    removeProofFile(type) {
        if (type === 'negative') {
            this.negativeFilmFile = null;
            this.hasExistingNegativeFilm = false;
            const input = document.getElementById('negativeFilmInput');
            if (input) input.value = '';
            const preview = document.getElementById('negativeFilmPreview');
            const zone = document.getElementById('negativeFilmZone');
            if (preview) preview.style.display = 'none';
            if (zone) zone.style.display = 'block';

        } else if (type === 'contact_sheet') {
            this.contactSheetFile = null;
            this.hasExistingContactSheet = false;
            const input = document.getElementById('contactSheetInput');
            if (input) input.value = '';
            const preview = document.getElementById('contactSheetPreview');
            const zone = document.getElementById('contactSheetZone');
            if (preview) preview.style.display = 'none';
            if (zone) zone.style.display = 'block';
        }
    }

    /**
     * Reset all proof attachment fields
     */
    resetProofFiles() {
        this.removeProofFile('negative');
        this.removeProofFile('contact_sheet');
    }
}

/**
 * Initialize form when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    new SubmissionForm();
});
document.addEventListener('DOMContentLoaded', () => {
    const draftBtn = document.getElementById('draftBtn');

    if (draftBtn) {
        draftBtn.style.position = 'relative';
        draftBtn.style.zIndex = '99999';
        draftBtn.style.pointerEvents = 'auto';
    }
});