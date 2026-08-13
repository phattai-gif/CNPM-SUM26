from flask import Blueprint, render_template

contest_bp = Blueprint('contest', __name__, url_prefix='/contest')


@contest_bp.route('/submission_review/<int:submission_id>', methods=['GET'])
def submission_review(submission_id):
    """
    Render submission review page with mock data (static for now).
    """
    # Mock submission data
    submission = {
        'id': submission_id,
        'title': 'Bài thi mẫu: Phân tích thuật toán',
        'author': 'Nguyễn Văn A',
        'submitted_at': '2026-08-13 10:32',
        'content': 'Đây là nội dung bài thi. Học sinh đã viết phần giải thích về thuật toán...',
        'attachments': ['answer.pdf', 'diagram.png'],
        'flagged': True,
    }

    # Mock AI warnings
    ai_warnings = [
        {
            'id': 1,
            'model_name': 'ai-detector',
            'model_version': '1.2',
            'label': 'AI Generated Text',
            'confidence': 0.92,
            'snippet': 'This paragraph shows high similarity to known AI patterns...',
            'details': {
                'summary': 'Detected high-level pattern matches to model signatures.'
            }
        },
        {
            'id': 2,
            'model_name': 'ai-detector',
            'model_version': '1.2',
            'label': 'Possible ChatGPT',
            'confidence': 0.68,
            'snippet': 'Another snippet with lower confidence...',
            'details': {
                'summary': 'Lower-confidence match; please review manually.'
            }
        }
    ]

    return render_template('submission_review.html', submission=submission, ai_warnings=ai_warnings)
