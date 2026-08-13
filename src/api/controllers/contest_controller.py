from flask import Blueprint, render_template

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