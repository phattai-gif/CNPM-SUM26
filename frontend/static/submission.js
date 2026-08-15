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
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.successMessage = document.getElementById('successMessage');
        this.errorMessage = document.getElementById('errorMessage');
        
        this.selectedImage = null;
        this.selectedImageFile = null;
        this.roundsList = [];
        this.session = window.AuthSession.getSession();
        this.authToken = this.session.token;

        this.init();
    }

    /**
     * Initialize form event listeners
     */
    init() {
        if (!this.authToken) {
            this.showError('Authentication Error', 'You must be logged in to submit. Please login first.');
            this.submitBtn.disabled = true;
            return;
        }

        // File input events
        this.imageInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.dragDropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dragDropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.dragDropZone.addEventListener('drop', (e) => this.handleFileDrop(e));

        // Form submission
        this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));

        // Remove image button
        document.getElementById('removeImageBtn').addEventListener('click', () => this.removeImage());

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

    /**
     * Load contest rounds from API
     */
    async loadRounds() {
        try {
            const data = await window.apiClient.get('/auth/contests');
            
            // Extract contests and their rounds
            const contests = data.contests || [];
            this.roundsList = [];
            
            contests.forEach(contest => {
                if (contest.rounds && Array.isArray(contest.rounds)) {
                    contest.rounds.forEach(round => {
                        this.roundsList.push({
                            id: round.id,
                            name: round.name,
                            deadline: round.deadline,
                            contest_name: contest.name || contest.title,
                            description: round.description
                        });
                    });
                }
            });
            
            this.populateRoundSelect();
        } catch (error) {
            console.warn('Could not load rounds:', error);
            // Continue anyway - user can manually enter round_id if needed
        }
    }

    /**
     * Populate round select dropdown
     */
    populateRoundSelect() {
        const roundSelect = document.getElementById('roundSelect');
        
        this.roundsList.forEach(round => {
            const option = document.createElement('option');
            option.value = round.id;
            const contestName = round.contest_name ? `[${round.contest_name}] ` : '';
            const deadline = round.deadline ? ` - Deadline: ${new Date(round.deadline).toLocaleDateString()}` : '';
            option.textContent = `${contestName}${round.name}${deadline}`;
            roundSelect.appendChild(option);
        });

        // Update round info when selection changes
        roundSelect.addEventListener('change', (e) => this.updateRoundInfo(e.target.value));
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
        this.imageInput.value = '';
        this.imageUploadArea.style.display = 'block';
        this.imagePreview.style.display = 'none';
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
        document.getElementById('titleCount').textContent = '0/200 characters';
        document.getElementById('descriptionCount').textContent = '0/1000 characters';
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

        // Check image
        if (!this.selectedImage) {
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
     * Handle form submission
     */
    async handleFormSubmit(event) {
        event.preventDefault();

        if (!this.validateForm()) {
            return;
        }

        this.submitBtn.disabled = true;
        this.loadingSpinner.style.display = 'flex';

        try {
            // Prepare form data
            const formData = new FormData(this.form);
            const submissionData = {
                round_id: parseInt(formData.get('round_id')),
                title: formData.get('title'),
                image_hd_url: this.selectedImage, // Base64 encoded or URL
                story_description: formData.get('story_description') || '',
                film_metadata: {
                    camera_body: formData.get('camera_body') || undefined,
                    lens: formData.get('lens') || undefined,
                    film_stock: formData.get('film_stock') || undefined,
                    film_iso: formData.get('film_iso') ? parseInt(formData.get('film_iso')) : undefined,
                    lab_name: formData.get('lab_name') || undefined,
                    scanner_info: formData.get('scanner_info') || undefined,
                    development_process: formData.get('development_process') || 'C-41',
                    taken_at_location: formData.get('taken_at_location') || undefined,
                }
            };

            // Remove undefined values from film_metadata
            Object.keys(submissionData.film_metadata).forEach(key =>
                submissionData.film_metadata[key] === undefined && delete submissionData.film_metadata[key]
            );

            // If no metadata provided, remove the empty object
            if (Object.keys(submissionData.film_metadata).length === 0) {
                delete submissionData.film_metadata;
            }

            // Call API
            const responseData = await window.apiClient.post('/submissions', submissionData);

            // Handle success
            this.handleSubmissionSuccess(responseData);

        } catch (error) {
            this.showError('Submission Failed', error.message || 'An unexpected error occurred');
        } finally {
            this.loadingSpinner.style.display = 'none';
            this.submitBtn.disabled = false;
        }
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
}

/**
 * Initialize form when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    new SubmissionForm();
});
