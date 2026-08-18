from flask import Blueprint, render_template, request, jsonify
from api.role_required import token_required, role_required
from services.submission_review_service import SubmissionReviewService
from infrastructure.repositories.submission_review_repository import SubmissionReviewRepository

bp = Blueprint('submission_review', __name__, url_prefix='')
submission_review_service = SubmissionReviewService(SubmissionReviewRepository())


# UI Rendering - Task CNPM-49
@bp.route('/submission_review/<int:submission_id>', methods=['GET'])
def submission_review(submission_id):
    """Render submission review page (Task CNPM-49) with mock data.
    This file only contains Task 49 logic and does not touch Judge/Results routes.
    """
    submission = {
        'id': submission_id,
        'title': 'BÃ i máº«u: BÃ¬nh minh trÃªn phá»‘ cá»•',
        'author': 'Nguyá»…n VÄƒn A',
        'submitted_at': '2026-08-14 09:00',
        'content': 'ÄÃ¢y lÃ  ná»™i dung bÃ i dá»± thi máº«u. Ná»™i dung mÃ´ táº£ Ã½ tÆ°á»Ÿng vÃ  ká»¹ thuáº­t.',
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


# API Routes for Submission Review CRUD
@bp.route('/api/submissions/<int:submission_id>/reviews', methods=['POST'])
@token_required
@role_required(['judge', 'admin', 'organizer'])
def create_submission_review(current_user, submission_id):
    """
    Create a review for a submission
    ---
    post:
      summary: Create a new submission review
      tags:
        - Submission Reviews
      security:
        - Bearer: []
      parameters:
        - in: path
          name: submission_id
          schema:
            type: integer
          required: true
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                review_status:
                  type: string
                  enum: [pending, in_progress, approved, rejected]
                  example: in_progress
                review_notes:
                  type: string
                  example: "Great submission, technically sound"
                decision_reason:
                  type: string
                  example: "Meets all contest requirements"
      responses:
        201:
          description: Review created successfully
    """
    data = request.get_json() or {}
    review_status = data.get('review_status', 'pending')
    review_notes = data.get('review_notes')
    decision_reason = data.get('decision_reason')
    
    review = submission_review_service.create_review(
        submission_id=submission_id,
        reviewer_id=current_user.id,
        review_status=review_status,
        review_notes=review_notes,
        decision_reason=decision_reason
    )
    
    return jsonify({
        'id': review.id,
        'submission_id': review.submission_id,
        'reviewer_id': review.reviewer_id,
        'review_status': review.review_status,
        'review_notes': review.review_notes,
        'decision_reason': review.decision_reason,
        'created_at': review.created_at.isoformat() if review.created_at else None,
        'message': 'Review created successfully'
    }), 201


@bp.route('/api/submissions/<int:submission_id>/reviews', methods=['GET'])
@token_required
def get_submission_reviews(current_user, submission_id):
    """
    Get all reviews for a submission
    ---
    get:
      summary: Retrieve all reviews for a submission
      tags:
        - Submission Reviews
      security:
        - Bearer: []
      parameters:
        - in: path
          name: submission_id
          schema:
            type: integer
          required: true
      responses:
        200:
          description: List of reviews
    """
    reviews = submission_review_service.repository.list_by_submission(submission_id)
    
    return jsonify({
        'count': len(reviews),
        'reviews': [
            {
                'id': r.id,
                'submission_id': r.submission_id,
                'reviewer_id': r.reviewer_id,
                'review_status': r.review_status,
                'review_notes': r.review_notes,
                'decision_reason': r.decision_reason,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in reviews
        ]
    }), 200


@bp.route('/api/reviews/<int:review_id>', methods=['GET'])
@token_required
def get_review(current_user, review_id):
    """
    Get a specific review
    ---
    get:
      summary: Retrieve a single review by ID
      tags:
        - Submission Reviews
      security:
        - Bearer: []
      parameters:
        - in: path
          name: review_id
          schema:
            type: integer
          required: true
      responses:
        200:
          description: Review details
        404:
          description: Review not found
    """
    review = submission_review_service.repository.session.query(SubmissionReviewRepository.__bases__[0].__subclasses__()[0]).filter_by(id=review_id).first()
    # Simplified: just get from session
    from infrastructure.models.app import SubmissionReviewModel
    review = submission_review_service.repository.session.query(SubmissionReviewModel).filter_by(id=review_id).first()
    
    if not review:
        return jsonify({'message': 'Review not found'}), 404
    
    return jsonify({
        'id': review.id,
        'submission_id': review.submission_id,
        'reviewer_id': review.reviewer_id,
        'review_status': review.review_status,
        'review_notes': review.review_notes,
        'decision_reason': review.decision_reason,
        'created_at': review.created_at.isoformat() if review.created_at else None,
        'updated_at': review.updated_at.isoformat() if review.updated_at else None,
    }), 200


@bp.route('/api/reviews/<int:review_id>', methods=['PUT'])
@token_required
@role_required(['judge', 'admin', 'organizer'])
def update_review(current_user, review_id):
    """
    Update a review
    ---
    put:
      summary: Update an existing review
      tags:
        - Submission Reviews
      security:
        - Bearer: []
      parameters:
        - in: path
          name: review_id
          schema:
            type: integer
          required: true
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                review_status:
                  type: string
                  enum: [pending, in_progress, approved, rejected]
                review_notes:
                  type: string
                decision_reason:
                  type: string
      responses:
        200:
          description: Review updated successfully
        404:
          description: Review not found
    """
    data = request.get_json() or {}
    review_status = data.get('review_status')
    review_notes = data.get('review_notes')
    decision_reason = data.get('decision_reason')
    
    updated = submission_review_service.update_review_status(
        review_id=review_id,
        review_status=review_status,
        review_notes=review_notes,
        decision_reason=decision_reason
    )
    
    if not updated:
        return jsonify({'message': 'Review not found'}), 404
    
    return jsonify({
        'id': updated.id,
        'submission_id': updated.submission_id,
        'reviewer_id': updated.reviewer_id,
        'review_status': updated.review_status,
        'review_notes': updated.review_notes,
        'decision_reason': updated.decision_reason,
        'created_at': updated.created_at.isoformat() if updated.created_at else None,
        'updated_at': updated.updated_at.isoformat() if updated.updated_at else None,
        'message': 'Review updated successfully'
    }), 200
