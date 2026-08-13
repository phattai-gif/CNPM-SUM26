from flask import Blueprint, render_template, request, redirect, url_for, flash

contest_bp = Blueprint('contest', __name__, url_prefix='/contest')


@contest_bp.route('/submission_review/<int:submission_id>', methods=['GET'])
def submission_review(submission_id):
    """
    Render submission review page with mock data for Film Photography Contest.
    """
    # Mock submission data cho bài thi Nhiếp ảnh Phim
    submission = {
        'id': submission_id,
        'title': 'Bình minh trên phố cổ - Film Kodak Ultramax 400',
        'author': 'Nguyễn Văn A',
        'submitted_at': '2026-08-13 10:32',
        'camera': 'Canon AE-1 Program',
        'film_stock': 'Kodak Ultramax 400',
        'lab': 'Laphoto Lab (Tráng & Scan)',
        'image_url': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32',
        'attachments': ['frame_01_scanned.jpg', 'negative_contact_sheet.jpg'],
        'flagged': True,
    }

    # Mock AI warnings phù hợp với nhận diện Ảnh AI / Ảnh Trùng Lặp
    ai_warnings = [
        {
            'id': 1,
            'model_name': 'image-ai-detector',
            'model_version': '2.1',
            'label': 'AI Generated Image',
            'confidence': 0.92,
            'snippet': 'Detected synthetic film grain and AI-generated pattern artifacts matching Midjourney v6 signatures.',
            'details': {
                'summary': 'Phát hiện hạt phim (film grain) giả lập và đường nét bất thường từ mô hình AI.'
            }
        },
        {
            'id': 2,
            'model_name': 'image-similarity-detector',
            'model_version': '1.0',
            'label': 'Duplicate Submission',
            'confidence': 0.68,
            'snippet': 'High visual similarity detected with frame #1048 stored in the digital archive.',
            'details': {
                'summary': 'Tác phẩm có độ tương đồng cao với ảnh đã nộp trong dữ liệu lưu trữ.'
            }
        }
    ]

    return render_template('submission_review.html', submission=submission, ai_warnings=ai_warnings)
# ==================== CNPM-50: Judge Grading UI ====================
@contest_bp.route('/judge_grading/<int:submission_id>', methods=['GET', 'POST'])
def judge_grading(submission_id):
    """
    Render Judge Grading interface for Ticket CNPM-50
    """
    if request.method == 'POST':
        # Read submitted scores and comment from form (mock save)
        scores = {
            'composition': request.form.get('composition'),
            'color_film': request.form.get('color_film'),
            'story': request.form.get('story')
        }
        comment = request.form.get('comment')

        # For now we mock-save by flashing a message; in real app persist to DB
        flash(f"Đã lưu điểm: {scores} và nhận xét: {comment}")
        return redirect(url_for('contest.judge_grading', submission_id=submission_id))
    submission = {
        'id': submission_id,
        'title': f'Bài dự thi #{submission_id} - Hoàng hôn Phố Cổ',
        'author': 'Nguyễn Văn B',
        'submitted_at': '2026-08-13 14:20',
        'camera': 'Leica M3',
        'film_stock': 'Kodak Portra 400',
        'image_url': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32',
        'prev_id': submission_id - 1 if submission_id > 1 else None,
        'next_id': submission_id + 1
    }

    criteria_list = [
        {'id': 'composition', 'name': 'Bố cục & Ánh sáng', 'max': 30},
        {'id': 'color_film', 'name': 'Màu sắc & Chất phim (Grain)', 'max': 30},
        {'id': 'story', 'name': 'Cảm xúc & Câu chuyện tác phẩm', 'max': 40}
    ]

    return render_template('judge_grading.html', submission=submission, criteria_list=criteria_list)