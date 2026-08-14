from flask import Blueprint, render_template

bp = Blueprint('submission_review', __name__, url_prefix='')


@bp.route('/submission_review/<int:submission_id>', methods=['GET'])
def submission_review(submission_id):
    """Render submission review page (Task CNPM-49) with mock data.
    This file only contains Task 49 logic and does not touch Judge/Results routes.
    """
    submission = {
        'id': submission_id,
        'title': 'Bài mẫu: Bình minh trên phố cổ',
        'author': 'Nguyễn Văn A',
        'submitted_at': '2026-08-14 09:00',
        'content': 'Đây là nội dung bài dự thi mẫu. Nội dung mô tả ý tưởng và kỹ thuật.',
        'attachments': ['answer.pdf'],
        'flagged': True,
        'image_url': None,
    }

    ai_warnings = [
        {
            'id': 1,
            'model_name': 'text-ai-detector',
            'model_version': '1.0',
            'label': 'AI Generated Text',
            'confidence': 0.87,
            'snippet': 'This paragraph shows high similarity to known AI patterns...',
            'details': {'summary': 'Detected phrasing patterns consistent with synthetic text.'},
        }
    ]

    return render_template('submission_review.html', submission=submission, ai_warnings=ai_warnings)
