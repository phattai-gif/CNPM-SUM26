"""API Controller for public voting on submissions."""

from flask import Blueprint, request, jsonify

from api.role_required import token_required
from services.vote_service import VoteService

vote_bp = Blueprint('vote', __name__, url_prefix='/api/votes')
vote_service = VoteService()


@vote_bp.route('/<int:submission_id>', methods=['POST'])
@token_required
def vote_submission(submission_id):
    """
    User votes on a public submission.
    
    POST /api/votes/<submission_id>
    
    Returns:
        201: Vote created successfully
        400: Validation error (submission not public, already voted)
        401: Unauthorized
        404: Submission not found
        500: Server error
    """
    user_id = request.user.get('user_id')
    
    if not user_id:
        return jsonify({'message': 'User ID not found'}), 401
    
    vote_dict, error = vote_service.vote_submission(user_id, submission_id)
    
    if error == "submission_not_found":
        return jsonify({
            'success': False,
            'message': 'Submission not found',
            'error': error
        }), 404
    
    if error == "submission_not_public":
        return jsonify({
            'success': False,
            'message': 'Only public (approved) submissions can be voted on',
            'error': error
        }), 400
    
    if error == "already_voted":
        return jsonify({
            'success': False,
            'message': 'You have already voted on this submission',
            'error': error
        }), 400
    
    if error == "database_error":
        return jsonify({
            'success': False,
            'message': 'Database error occurred',
            'error': error
        }), 500
    
    if vote_dict is None:
        return jsonify({
            'success': False,
            'message': 'Failed to create vote',
            'error': error or 'unknown_error'
        }), 500
    
    return jsonify({
        'success': True,
        'message': 'Vote recorded successfully',
        'vote': vote_dict
    }), 201


@vote_bp.route('/<int:submission_id>', methods=['DELETE'])
@token_required
def unvote_submission(submission_id):
    """
    User removes their vote from a submission.
    
    DELETE /api/votes/<submission_id>
    
    Returns:
        200: Vote removed successfully
        401: Unauthorized
        404: Vote not found
        500: Server error
    """
    user_id = request.user.get('user_id')
    
    if not user_id:
        return jsonify({'message': 'User ID not found'}), 401
    
    success, error = vote_service.unvote_submission(user_id, submission_id)
    
    if not success:
        if error == "vote_not_found":
            return jsonify({
                'success': False,
                'message': 'You have not voted on this submission',
                'error': error
            }), 404
        
        if error == "database_error":
            return jsonify({
                'success': False,
                'message': 'Database error occurred',
                'error': error
            }), 500
        
        return jsonify({
            'success': False,
            'message': 'Failed to remove vote',
            'error': error or 'unknown_error'
        }), 500
    
    return jsonify({
        'success': True,
        'message': 'Vote removed successfully'
    }), 200


@vote_bp.route('/<int:submission_id>/count', methods=['GET'])
def get_submission_vote_count(submission_id):
    """
    Get total number of votes for a submission (public endpoint).
    
    GET /api/votes/<submission_id>/count
    
    Returns:
        200: Vote count
        404: Submission not found
    """
    from infrastructure.repositories.submission_repository import SubmissionRepository
    
    submission_repo = SubmissionRepository()
    submission = submission_repo.get_by_id(submission_id)
    
    if submission is None:
        return jsonify({
            'success': False,
            'message': 'Submission not found',
            'error': 'submission_not_found'
        }), 404
    
    vote_count = vote_service.get_submission_vote_count(submission_id)
    
    return jsonify({
        'success': True,
        'submission_id': submission_id,
        'vote_count': vote_count
    }), 200


@vote_bp.route('/<int:submission_id>/status', methods=['GET'])
@token_required
def get_vote_status(submission_id):
    """
    Check if current user has voted on this submission.
    
    GET /api/votes/<submission_id>/status
    
    Returns:
        200: Vote status
        401: Unauthorized
        404: Submission not found
    """
    user_id = request.user.get('user_id')
    
    if not user_id:
        return jsonify({'message': 'User ID not found'}), 401
    
    from infrastructure.repositories.submission_repository import SubmissionRepository
    
    submission_repo = SubmissionRepository()
    submission = submission_repo.get_by_id(submission_id)
    
    if submission is None:
        return jsonify({
            'success': False,
            'message': 'Submission not found',
            'error': 'submission_not_found'
        }), 404
    
    has_voted = vote_service.has_user_voted(user_id, submission_id)
    vote_count = vote_service.get_submission_vote_count(submission_id)
    
    return jsonify({
        'success': True,
        'submission_id': submission_id,
        'user_has_voted': has_voted,
        'total_votes': vote_count
    }), 200


@vote_bp.route('/my-votes', methods=['GET'])
@token_required
def get_my_votes():
    """
    Get list of submissions current user has voted on.
    
    GET /api/votes/my-votes
    
    Returns:
        200: List of votes
        401: Unauthorized
    """
    user_id = request.user.get('user_id')
    
    if not user_id:
        return jsonify({'message': 'User ID not found'}), 401
    
    votes = vote_service.get_user_votes(user_id)
    
    return jsonify({
        'success': True,
        'votes': votes,
        'count': len(votes)
    }), 200
