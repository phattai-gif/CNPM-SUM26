from flask import Blueprint, render_template, request, jsonify
from flask import flash, redirect, url_for
from datetime import datetime

# Ensure module is available under the `src.` package path used by tests
import sys
_alias = 'src.' + __name__
if _alias not in sys.modules:
    sys.modules[_alias] = sys.modules.get(__name__)

try:
    from infrastructure.repositories.contest_repository import ContestRepository
    from services.contest_service import ContestService
    from services.score_service import ScoreService
    from api.schemas.contest import (
        ContestCreateRequestSchema,
        ContestUpdateRequestSchema,
        ContestRulesUpdateRequestSchema,
        ContestConfigurationRequestSchema,
        ContestResponseSchema,
        RoundSchema,
        CriteriaSchema
    )
    from api.role_required import role_required
except ImportError:
    from infrastructure.repositories.contest_repository import ContestRepository
    from services.contest_service import ContestService
    from services.score_service import ScoreService
    from api.schemas.contest import (
        ContestCreateRequestSchema,
        ContestUpdateRequestSchema,
        ContestRulesUpdateRequestSchema,
        ContestConfigurationRequestSchema,
        ContestResponseSchema,
        RoundSchema,
        CriteriaSchema
    )
    from api.role_required import role_required


contest_bp = Blueprint('contest', __name__, url_prefix='/organizer')

# Public-facing contest pages (leaderboard, results) under /contest
public_bp = Blueprint('contest_public', __name__, url_prefix='/contest')


contest_service = ContestService(ContestRepository())
score_service = ScoreService()

from api.controllers.response_utils import safe_jsonify

contest_create_schema = ContestCreateRequestSchema()
contest_update_schema = ContestUpdateRequestSchema()
contest_rules_schema = ContestRulesUpdateRequestSchema()
contest_config_schema = ContestConfigurationRequestSchema()
contest_response_schema = ContestResponseSchema()
round_schema = RoundSchema()
criteria_schema = CriteriaSchema()


def _request_user():
    user = getattr(request, 'user', None)
    return user if isinstance(user, dict) else {}


def _serialize_model(model):
    if model is None:
        return None
    if isinstance(model, dict):
        return dict(model)
    to_dict_fn = getattr(model, 'to_dict', None)
    if callable(to_dict_fn):
        try:
            return to_dict_fn()
        except Exception:
            pass
    return safe_jsonify(model, status=200)[0].get_json() if model is not None else None


def _serialize_list(items):
    return [
        _serialize_model(item)
        for item in (items or [])
        if item is not None
    ]


# -------------------------------------------------------------------------
# Legacy HTML Dashboard Routes
# -------------------------------------------------------------------------

@contest_bp.route('/dashboard', methods=['GET'])
@role_required('organizer', 'admin')
def organizer_dashboard():
    """Render dashboard for organizers showing contests they manage.

    This route intentionally does not require Authorization header so the
    frontend can load the static HTML and then call protected APIs using the
    token stored in localStorage. If a server-side authenticated user is
    available (`request.user`), we include their contests; otherwise we
    render the page with an empty list and expose `organizer_id` as empty.
    """
    user = getattr(request, 'user', None)
    if user and isinstance(user, dict) and user.get('user_id'):
        user_id = user.get('user_id')
        try:
            contests = contest_service.list_organizer_contests(user_id)
            contests_data = [c.to_dict() for c in contests]
        except Exception:
            contests_data = []
    else:
        user_id = ''
        contests_data = []

    # Frontend JS will fetch live data using the token from localStorage.
    return render_template('organizer_dashboard.html', contests=contests_data, organizer_id=user_id, api_token='')


@contest_bp.route('/contest-detail', methods=['GET'])
@role_required('organizer', 'admin')
def organizer_contest_detail_page():
    """Render frontend contest detail page which will fetch contest details via API."""
    # Page itself doesn't require server-side authentication; JS will call protected API using token
    return render_template('organizer_contest_detail.html')


@contest_bp.route('/dashboard/metrics', methods=['GET'])
@role_required('organizer', 'admin')
def organizer_dashboard_metrics():
    """Return simple aggregated metrics for the organizer dashboard."""
    try:
        user = getattr(request, 'user', None) or {}
        user_id = user.get('user_id')

        if not user_id:
            return jsonify({
                'message': 'Metrics fetched',
                'submissions': 0,
                'contests': 0,
                'judges': 0
            }), 200

        contests = contest_service.list_organizer_contests(user_id)
        total_contests = len(contests)
        # Use repository session to compute totals across contests' rounds
        session = contest_service.repository.session
        from infrastructure.models.app import SubmissionModel, JudgeAssignmentModel
        # gather round ids owned by this organizer
        all_round_ids = []
        for c in contests:
            for r in (c.rounds or []):
                if getattr(r, 'id', None):
                    all_round_ids.append(r.id)

        # default results
        submissions = 0
        judges = 0

        # safe COUNT queries using func.count and func.distinct
        from sqlalchemy import func
        try:
            if all_round_ids:
                submissions = int(session.query(func.count(SubmissionModel.id)).filter(SubmissionModel.round_id.in_(all_round_ids)).scalar() or 0)
                judges = int(session.query(func.count(func.distinct(JudgeAssignmentModel.judge_id))).filter(JudgeAssignmentModel.round_id.in_(all_round_ids)).scalar() or 0)
        except Exception:
            submissions = 0
            judges = 0

        return jsonify({
            'message': 'Metrics fetched',
            'submissions': submissions,
            'contests': total_contests,
            'judges': judges
        }), 200
    except Exception:
        # On any error, return zeroed metrics so frontend shows 0 instead of failing
        return jsonify({
            'message': 'Metrics fetched',
            'submissions': 0,
            'contests': 0,
            'judges': 0
        }), 200


@contest_bp.route('/dashboard/seed', methods=['POST'])
@role_required('organizer', 'admin')
def organizer_dashboard_seed():
    """Create a sample contest + round + submissions for the current organizer (for testing)."""
    user_id = request.user.get('user_id')
    try:
        # Create a sample contest
        contest_data = {
            'title': f'Sample Contest {datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
            'description': 'Auto-generated contest for dashboard testing',
            'status': 'published'
        }
        contest = contest_service.create_contest(contest_data, user_id=user_id)

        # Create a sample round
        round_data = {
            'title': 'Round 1',
            'round_number': 1,
            'status': 'open'
        }
        round_obj = contest_service.create_round(contest.id, round_data, user_id=user_id)

        # Create sample submissions using SubmissionService
        from services.submission_service import SubmissionService
        submission_service = SubmissionService()

        sample_image = 'https://images.unsplash.com/photo-1501785888041-af3ef285b470'
        created_submissions = []
        for i in range(3):
            title = f'Sample Submission {i+1}'
            # We use user_id as submitter to avoid FK issues
            try:
                sub = submission_service.create_submission(
                    round_id=round_obj.id,
                    user_id=user_id,
                    title=title,
                    image_hd_url=sample_image,
                    file_hash=f'samplehash-{datetime.utcnow().timestamp()}-{i}',
                    film_metadata={'film_stock': 'Kodak Portra 400'},
                    story_description='Auto-generated submission for UI testing',
                )
                created_submissions.append(sub.id)
            except Exception:
                # ignore individual submission errors
                continue

        return jsonify({
            'message': 'Seed created',
            'contest_id': contest.id,
            'round_id': round_obj.id,
            'submission_ids': created_submissions
        }), 201
    except Exception as e:
        return jsonify({'message': 'Failed to create seed data', 'error': str(e)}), 500

@contest_bp.route('/results', methods=['GET'])
@role_required('organizer', 'admin')
def results():
    """
    Render contest results / leaderboard (mock data).
    """
    # Mock leaderboard data
    leaderboard = [
        {'rank': 1, 'author': 'Nguyễn Thị C', 'title': 'Hoàng hôn trên sông', 'score': 97, 'image_url': 'https://images.unsplash.com/photo-1501785888041-af3ef285b470', 'camera': 'Leica M6', 'film_stock': 'Kodak Portra 400'},
        {'rank': 2, 'author': 'Trần Văn D', 'title': 'Bến cảng sớm mai', 'score': 92, 'image_url': 'https://images.unsplash.com/photo-1470770903676-69b98201ea1c', 'camera': 'Nikon F3', 'film_stock': 'Ilford HP5'},
        {'rank': 3, 'author': 'Lê Văn E', 'title': 'Mưa rơi phố nhỏ', 'score': 89, 'image_url': 'https://images.unsplash.com/photo-1506744038136-46273834b3fb', 'camera': 'Canon AE-1', 'film_stock': 'Fuji Pro 400H'},
        {'rank': 4, 'author': 'Nguyễn Văn A', 'title': 'Bình minh trên phố cổ', 'score': 85},
        {'rank': 5, 'author': 'Phạm Thị B', 'title': 'Ánh đèn đêm', 'score': 82},
    ]

    # Top 3 winners for highlighted section
    winners = leaderboard[:3]

    return render_template('results.html', leaderboard=leaderboard, winners=winners)


@public_bp.route('/results', methods=['GET'])
def public_results():
    """
    Public route for contest results (accessible at /contest/results).
    Uses the same mock leaderboard data as organizer results.
    """
    leaderboard = [
        {'rank': 1, 'author': 'Nguyễn Thị C', 'title': 'Hoàng hôn trên sông', 'score': 97, 'image_url': 'https://images.unsplash.com/photo-1501785888041-af3ef285b470', 'camera': 'Leica M6', 'film_stock': 'Kodak Portra 400'},
        {'rank': 2, 'author': 'Trần Văn D', 'title': 'Bến cảng sớm mai', 'score': 92, 'image_url': 'https://images.unsplash.com/photo-1470770903676-69b98201ea1c', 'camera': 'Nikon F3', 'film_stock': 'Ilford HP5'},
        {'rank': 3, 'author': 'Lê Văn E', 'title': 'Mưa rơi phố nhỏ', 'score': 89, 'image_url': 'https://images.unsplash.com/photo-1506744038136-46273834b3fb', 'camera': 'Canon AE-1', 'film_stock': 'Fuji Pro 400H'},
        {'rank': 4, 'author': 'Nguyễn Văn A', 'title': 'Bình minh trên phố cổ', 'score': 85},
        {'rank': 5, 'author': 'Phạm Thị B', 'title': 'Ánh đèn đêm', 'score': 82},
    ]
    winners = leaderboard[:3]
    return render_template('results.html', leaderboard=leaderboard, winners=winners)


@public_bp.route('/leaderboard', methods=['GET'])
def public_leaderboard():
    """Alias route for leaderboard; reuses same mock data as public_results."""
    return public_results()


# -------------------------------------------------------------------------
# Additional Organizer APIs for CNPM-98: leaderboard, winner actions,
# publishing to digital archive, and listing published/archive exhibits.
# -------------------------------------------------------------------------


@contest_bp.route('/rounds/<int:round_id>/leaderboard', methods=['GET'])
@role_required('organizer', 'admin')
def get_round_leaderboard(round_id):
    """Return finalized leaderboard for a round. This will call finalize
    which computes and returns leaderboard data (it is idempotent in the
    sense it will mark the round FINALIZED)."""
    try:
        data, error = score_service.finalize_round(round_id)

    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400

    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403

    except Exception as exc:
        return jsonify({'message': 'Failed to compute leaderboard', 'error': str(exc)}), 500

    if error == 'round_not_found':
        return jsonify({'message': 'Round not found'}), 404
    if error == 'round_already_finalized' and data is None:
        return jsonify({'message': 'Round already finalized and no data available'}), 409

    return safe_jsonify(data, status=200)


@contest_bp.route('/submissions/<int:submission_id>/approve-winner', methods=['POST'])
@role_required('organizer', 'admin')
def approve_winner(submission_id):
    try:
        # Mark submission as winner_approved
        from infrastructure.models.app import SubmissionModel
        session = contest_service.repository.session
        sub = session.query(SubmissionModel).filter(SubmissionModel.id == submission_id).first()
        if not sub:
            return jsonify({'message': 'Submission not found'}), 404
        sub.status = 'winner_approved'
        session.commit()
        session.refresh(sub)
        return jsonify({'message': 'Winner approved', 'submission_status': sub.status}), 200
    except Exception as exc:
        return jsonify({'message': 'Failed to approve winner', 'error': str(exc)}), 500


@contest_bp.route('/submissions/<int:submission_id>/reject-winner', methods=['POST'])
@role_required('organizer', 'admin')
def reject_winner(submission_id):
    try:
        from infrastructure.models.app import SubmissionModel
        session = contest_service.repository.session
        sub = session.query(SubmissionModel).filter(SubmissionModel.id == submission_id).first()
        if not sub:
            return jsonify({'message': 'Submission not found'}), 404
        sub.status = 'winner_rejected'
        session.commit()
        session.refresh(sub)
        return jsonify({'message': 'Winner rejected', 'submission_status': sub.status}), 200
    except Exception as exc:
        return jsonify({'message': 'Failed to reject winner', 'error': str(exc)}), 500


@contest_bp.route('/submissions/<int:submission_id>/publish', methods=['POST'])
@role_required('organizer', 'admin')
def publish_submission(submission_id):
    try:
        from infrastructure.models.app import SubmissionModel, RoundModel, DigitalArchiveExhibitModel
        session = contest_service.repository.session
        sub = session.query(SubmissionModel).filter(SubmissionModel.id == submission_id).first()
        if not sub:
            return jsonify({'message': 'Submission not found'}), 404

        # determine contest
        rnd = session.query(RoundModel).filter(RoundModel.id == sub.round_id).first()
        contest_id = rnd.contest_id if rnd else None

        # create or ignore existing exhibit
        existing = session.query(DigitalArchiveExhibitModel).filter(
            DigitalArchiveExhibitModel.submission_id == submission_id,
            DigitalArchiveExhibitModel.contest_id == contest_id,
        ).first()

        if existing:
            return jsonify({'message': 'Already published', 'exhibit_id': existing.id}), 200

        exhibit = DigitalArchiveExhibitModel(contest_id=contest_id or 0, submission_id=submission_id)
        session.add(exhibit)
        # Optionally mark submission as published
        sub.status = 'published'
        session.commit()
        session.refresh(exhibit)

        # Try to include a representative image_url for the frontend to show
        try:
            from infrastructure.models.app import SubmissionFileModel
            file_row = session.query(SubmissionFileModel).filter(SubmissionFileModel.submission_id == submission_id).order_by(SubmissionFileModel.id.asc()).first()
            image_url = None
            if file_row is not None:
                image_url = getattr(file_row, 'thumbnail_url', None) or getattr(file_row, 'image_hd_url', None) or None
        except Exception:
            image_url = None

        return jsonify({'message': 'Published to gallery', 'exhibit_id': exhibit.id, 'image_url': image_url}), 201
    except Exception as exc:
        return jsonify({'message': 'Failed to publish submission', 'error': str(exc)}), 500


@contest_bp.route('/submissions/<int:submission_id>/archive', methods=['POST'])
@role_required('organizer', 'admin')
def archive_submission(submission_id):
    try:
        from infrastructure.models.app import SubmissionModel
        session = contest_service.repository.session
        sub = session.query(SubmissionModel).filter(SubmissionModel.id == submission_id).first()
        if not sub:
            return jsonify({'message': 'Submission not found'}), 404

        sub.status = 'archived'
        session.commit()
        session.refresh(sub)
        return jsonify({'message': 'Submission archived', 'submission_status': sub.status}), 200
    except Exception as exc:
        return jsonify({'message': 'Failed to archive submission', 'error': str(exc)}), 500


@contest_bp.route('/exhibits', methods=['GET'])
@role_required('organizer', 'admin')
def list_exhibits():
    try:
        from infrastructure.models.app import DigitalArchiveExhibitModel
        session = contest_service.repository.session
        contest_id = request.args.get('contest_id', type=int)
        query = session.query(DigitalArchiveExhibitModel)
        if contest_id:
            query = query.filter(DigitalArchiveExhibitModel.contest_id == contest_id)
        exhibits = query.order_by(DigitalArchiveExhibitModel.published_at.desc()).all()
        result = [
            {
                'id': e.id,
                'contest_id': e.contest_id,
                'submission_id': e.submission_id,
                'published_at': e.published_at.isoformat() if e.published_at else None,
                # include a representative image if available
                'image_url': None,
            }
            for e in exhibits
        ]
        # enrich exhibits with image urls
        try:
            from infrastructure.models.app import SubmissionFileModel
            for item in result:
                try:
                    file_row = session.query(SubmissionFileModel).filter(SubmissionFileModel.submission_id == item['submission_id']).order_by(SubmissionFileModel.id.asc()).first()
                    if file_row is not None:
                        item['image_url'] = getattr(file_row, 'thumbnail_url', None) or getattr(file_row, 'image_hd_url', None) or None
                except Exception:
                    item['image_url'] = None
        except Exception:
            pass
        return jsonify({'exhibits': result}), 200
    except Exception as exc:
        return jsonify({'message': 'Failed to list exhibits', 'error': str(exc)}), 500
# Public judge grading UI (Task CNPM-50)
@public_bp.route('/judge/grading/<int:submission_id>', methods=['GET', 'POST'])
def public_judge_grading(submission_id):
    """
    Public-facing judge grading UI for testing and demos.
    Provides mock submission data and mock criteria when DB/services are unavailable.
    Handles POST to receive scores and comment (stores nothing; flashes success).
    """
    # Mock submission data
    submission = {
        'id': submission_id,
        'title': 'Bài mẫu: Bình minh trên phố cổ',
        'author': 'Nguyễn Văn A',
        'image_url': 'https://images.unsplash.com/photo-1501785888041-af3ef285b470',
        'camera': 'Nikon F3',
        'film_stock': 'Kodak Portra 400',
        'prev_id': submission_id - 1 if submission_id > 1 else None,
        'next_id': submission_id + 1,
    }

    # Mock criteria list
    criteria_list = [
        {'id': 1, 'name': 'Composition', 'max': 40},
        {'id': 2, 'name': 'Exposure', 'max': 30},
        {'id': 3, 'name': 'Creativity', 'max': 30},
    ]

    if request.method == 'POST':
        # Collect scores from form
        form = request.form.to_dict(flat=True)
        comment = form.pop('comment', '')
        scores = {}
        for crit in criteria_list:
            key = str(crit['id'])
            val = form.get(key)
            try:
                scores[key] = int(val) if val is not None and val != '' else None
            except ValueError:
                scores[key] = None

        # In a real app we'd persist scores via ScoreService; here we just flash
        flash('Điểm và nhận xét đã được lưu (demo).')
        return redirect(url_for('contest_public.public_judge_grading', submission_id=submission_id))

    return render_template('judge_grading.html', submission=submission, criteria_list=criteria_list)


@contest_bp.route('/create-contest', methods=['GET'])
@role_required('organizer', 'admin')
def create_contest_page():
    # Serve the create contest HTML page without requiring Authorization header.
    # The frontend will call the POST API with the token in Authorization header.
    return render_template('create_contest.html')


# -------------------------------------------------------------------------
# Contest Management APIs
# -------------------------------------------------------------------------

@contest_bp.route('/contests', methods=['POST'])
@contest_bp.route('/create-contest', methods=['POST'])
@role_required('organizer', 'admin')
def create_contest():
    """API Táº¡o cuá»™c thi má»›i."""
    user_id = _request_user().get('user_id')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = contest_create_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dá»¯ liá»‡u khÃ´ng há»£p lá»‡', 'errors': errors}), 400

    try:
        contest = contest_service.create_contest(data, user_id=user_id)
        return safe_jsonify({
            'message': 'Táº¡o cuá»™c thi thÃ nh cÃ´ng',
            'contest': _serialize_model(contest) or {}
        }, status=201)
    except ValueError as ve:
        return safe_jsonify({'message': str(ve)}, status=400)
    except Exception as e:
        return safe_jsonify({'message': 'Lá»—i khi táº¡o cuá»™c thi', 'error': str(e)}, status=500)


@contest_bp.route('/contests', methods=['GET'])
@role_required('organizer', 'admin')
def list_contests():
    """API Liá»‡t kÃª danh sÃ¡ch cuá»™c thi cá»§a Organizer."""
    user_id = _request_user().get('user_id')
    contests = contest_service.list_organizer_contests(user_id)
    # Enhance with submissions_count and judges_count per contest
    try:
        session = contest_service.repository.session
        from infrastructure.models.app import SubmissionModel, JudgeAssignmentModel

        contests_out = []
        for c in contests:
            cdict = _serialize_model(c) or {}
            round_ids = [r.id for r in (c.rounds or []) if getattr(r, 'id', None)]
            submissions_count = 0
            judges_count = 0
            if round_ids:
                try:
                    submissions_count = int(session.query(SubmissionModel).filter(SubmissionModel.round_id.in_(round_ids)).count())
                except Exception:
                    submissions_count = 0
                try:
                    judges_count = int(session.query(JudgeAssignmentModel.judge_id).filter(JudgeAssignmentModel.round_id.in_(round_ids)).distinct().count())
                except Exception:
                    judges_count = 0

            cdict['submissions_count'] = submissions_count
            cdict['judges_count'] = judges_count
            contests_out.append(cdict)

        return safe_jsonify({
            'message': 'Láº¥y danh sÃ¡ch cuá»™c thi thÃ nh cÃ´ng',
            'contests': contests_out
        }, status=200)
    except Exception:
        return safe_jsonify({
            'message': 'Láº¥y danh sÃ¡ch cuá»™c thi thÃ nh cÃ´ng',
            'contests': _serialize_list(contests)
        }, status=200)


@contest_bp.route('/contests/<int:contest_id>', methods=['GET'])
@role_required('organizer', 'admin')
def get_contest(contest_id):
    """API Láº¥y thÃ´ng tin chi tiáº¿t cuá»™c thi (bao gá»“m thá»ƒ lá»‡, vÃ²ng thi, tiÃªu chÃ­)."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')

    contest = contest_service.get_contest(contest_id)
    if not contest:
        return jsonify({'message': 'KhÃ´ng tÃ¬m tháº¥y cuá»™c thi'}), 404

    try:
        owner_id = int(contest.created_by)
    except (TypeError, ValueError):
        owner_id = contest.created_by
    try:
        actor_id = int(user_id)
    except (TypeError, ValueError):
        actor_id = user_id

    if user_role != 'admin' and owner_id != actor_id:
        return jsonify({'message': 'Báº¡n khÃ´ng cÃ³ quyá»n xem cuá»™c thi nÃ y'}), 403

    return safe_jsonify({
        'message': 'Láº¥y thÃ´ng tin cuá»™c thi thÃ nh cÃ´ng',
        'contest': _serialize_model(contest) or {}
    }, status=200)


@contest_bp.route('/contests/<int:contest_id>', methods=['PUT'])
@role_required('organizer', 'admin')
def update_contest(contest_id):
    """API Cáº­p nháº­t thÃ´ng tin cuá»™c thi."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = contest_update_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dá»¯ liá»‡u khÃ´ng há»£p lá»‡', 'errors': errors}), 400

    try:
        contest = contest_service.update_contest(contest_id, data, user_id=user_id, user_role=user_role)
        return safe_jsonify({
            'message': 'Cáº­p nháº­t cuá»™c thi thÃ nh cÃ´ng',
            'contest': _serialize_model(contest) or {}
        }, status=200)
    except ValueError as ve:
        return safe_jsonify({'message': str(ve)}, status=400)
    except PermissionError as pe:
        return safe_jsonify({'message': str(pe)}, status=403)
    except Exception as e:
        return safe_jsonify({'message': 'Lá»—i khi cáº­p nháº­t cuá»™c thi', 'error': str(e)}, status=500)


@contest_bp.route('/contests/<int:contest_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def delete_contest(contest_id):
    """API XÃ³a cuá»™c thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        contest_service.delete_contest(contest_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'XÃ³a cuá»™c thi thÃ nh cÃ´ng'}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 404
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi xÃ³a cuá»™c thi', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Categories & Awards (Task CNPM-95) APIs
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/categories', methods=['GET'])
@role_required('organizer', 'admin')
def list_contest_categories(contest_id):
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        categories = contest_service.list_categories(contest_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Lấy danh mục thành công', 'categories': categories}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 404
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi láº¥y danh má»¥c', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/categories', methods=['POST'])
@role_required('organizer', 'admin')
def create_contest_category(contest_id):
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    try:
        categories = contest_service.create_category(contest_id, data, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Tạo danh mục thành công', 'categories': categories}), 201
    except ValueError as ve:
        message = str(ve)
        status_code = 404 if 'KhÃ´ng tÃ¬m tháº¥y cuá»™c thi' in message else 400
        return jsonify({'message': message}), status_code
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi táº¡o danh má»¥c', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/categories/<int:category_id>', methods=['PUT'])
@role_required('organizer', 'admin')
def update_contest_category(contest_id, category_id):
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    try:
        categories = contest_service.update_category(contest_id, category_id, data, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Cập nhật danh mục thành công', 'categories': categories}), 200
    except ValueError as ve:
        message = str(ve)
        status_code = 404 if 'Không tìm thấy' in message else 400
        return jsonify({'message': message}), status_code
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi cáº­p nháº­t danh má»¥c', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/categories/<int:category_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def delete_contest_category(contest_id, category_id):
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        categories = contest_service.delete_category(contest_id, category_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Xóa danh mục thành công', 'categories': categories}), 200
    except ValueError as ve:
        message = str(ve)
        status_code = 404 if 'Không tìm thấy' in message else 400
        return jsonify({'message': message}), status_code
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi xÃ³a danh má»¥c', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/awards', methods=['GET'])
@role_required('organizer', 'admin')
def list_contest_awards(contest_id):
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        awards = contest_service.list_awards(contest_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Láº¥y giáº£i thÆ°á»Ÿng thÃ nh cÃ´ng', 'awards': awards}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 404
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi láº¥y giáº£i thÆ°á»Ÿng', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/awards', methods=['POST'])
@role_required('organizer', 'admin')
def create_contest_award(contest_id):
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    try:
        awards = contest_service.create_award(contest_id, data, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Táº¡o giáº£i thÆ°á»Ÿng thÃ nh cÃ´ng', 'awards': awards}), 201
    except ValueError as ve:
        message = str(ve)
        status_code = 404 if 'KhÃ´ng tÃ¬m tháº¥y cuá»™c thi' in message else 400
        return jsonify({'message': message}), status_code
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi táº¡o giáº£i thÆ°á»Ÿng', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/awards/<int:award_id>', methods=['PUT'])
@role_required('organizer', 'admin')
def update_contest_award(contest_id, award_id):
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    try:
        awards = contest_service.update_award(contest_id, award_id, data, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Cáº­p nháº­t giáº£i thÆ°á»Ÿng thÃ nh cÃ´ng', 'awards': awards}), 200
    except ValueError as ve:
        message = str(ve)
        status_code = 404 if 'Không tìm thấy' in message else 400
        return jsonify({'message': message}), status_code
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi cáº­p nháº­t giáº£i thÆ°á»Ÿng', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/awards/<int:award_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def delete_contest_award(contest_id, award_id):
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        awards = contest_service.delete_award(contest_id, award_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'XÃ³a giáº£i thÆ°á»Ÿng thÃ nh cÃ´ng', 'awards': awards}), 200
    except ValueError as ve:
        message = str(ve)
        status_code = 404 if 'Không tìm thấy' in message else 400
        return jsonify({'message': message}), status_code
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi xÃ³a giáº£i thÆ°á»Ÿng', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Contest Rules (Thá»ƒ lá»‡ cuá»™c thi) APIs
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/rules', methods=['PUT'])
@role_required('organizer', 'admin')
def update_contest_rules(contest_id):
    """API Cáº­p nháº­t thá»ƒ lá»‡ cuá»™c thi."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = contest_rules_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dá»¯ liá»‡u thá»ƒ lá»‡ khÃ´ng há»£p lá»‡', 'errors': errors}), 400

    try:
        contest = contest_service.update_rules(contest_id, rules=data.get('rules', ''), user_id=user_id, user_role=user_role)
        return safe_jsonify({
            'message': 'Cáº­p nháº­t thá»ƒ lá»‡ cuá»™c thi thÃ nh cÃ´ng',
            'contest': _serialize_model(contest) or {}
        }, status=200)
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi cáº­p nháº­t thá»ƒ lá»‡', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Contest Round (Vòng thi) APIs
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/rounds', methods=['POST'])
@role_required('organizer', 'admin')
def create_round(contest_id):
    """API ThÃªm vÃ²ng thi má»›i cho cuá»™c thi."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = round_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dá»¯ liá»‡u vÃ²ng thi khÃ´ng há»£p lá»‡', 'errors': errors}), 400

    try:
        round_obj = contest_service.create_round(contest_id, data, user_id=user_id, user_role=user_role)
        return safe_jsonify({
            'message': 'Tạo vòng thi thành công',
            'round': _serialize_model(round_obj) or {}
        }, status=201)
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi táº¡o vÃ²ng thi', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>', methods=['PUT'])
@role_required('organizer', 'admin')
def update_round(contest_id, round_id):
    """API Cập nhật thông tin vòng thi."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    try:
        round_obj = contest_service.update_round(contest_id, round_id, data, user_id=user_id, user_role=user_role)
        return safe_jsonify({
            'message': 'Cập nhật vòng thi thành công',
            'round': _serialize_model(round_obj) or {}
        }, status=200)
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi cáº­p nháº­t vÃ²ng thi', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def delete_round(contest_id, round_id):
    """API Xóa vòng thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        contest_service.delete_round(contest_id, round_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Xóa vòng thi thành công'}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi xÃ³a vÃ²ng thi', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Criteria (TiÃªu chÃ­ cháº¥m Ä‘iá»ƒm) APIs
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/criteria', methods=['POST'])
@role_required('organizer', 'admin')
def create_criteria(contest_id, round_id):
    """API ThÃªm tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm cho vÃ²ng thi."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = criteria_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dá»¯ liá»‡u tiÃªu chÃ­ khÃ´ng há»£p lá»‡', 'errors': errors}), 400

    try:
        crit = contest_service.create_criteria(contest_id, round_id, data, user_id=user_id, user_role=user_role)
        return safe_jsonify({
            'message': 'Táº¡o tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm thÃ nh cÃ´ng',
            'criteria': _serialize_model(crit) or {}
        }, status=201)
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi táº¡o tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/criteria/<int:criteria_id>', methods=['PUT'])
@role_required('organizer', 'admin')
def update_criteria(contest_id, round_id, criteria_id):
    """API Cáº­p nháº­t tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    try:
        crit = contest_service.update_criteria(contest_id, round_id, criteria_id, data, user_id=user_id, user_role=user_role)
        return safe_jsonify({
            'message': 'Cáº­p nháº­t tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm thÃ nh cÃ´ng',
            'criteria': _serialize_model(crit) or {}
        }, status=200)
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi cáº­p nháº­t tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/criteria/<int:criteria_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def delete_criteria(contest_id, round_id, criteria_id):
    """API XÃ³a tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        contest_service.delete_criteria(contest_id, round_id, criteria_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'XÃ³a tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm thÃ nh cÃ´ng'}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi xÃ³a tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Bulk Contest Configuration API (Äá»“ng bá»™ Thá»ƒ lá»‡, VÃ²ng thi & TiÃªu chÃ­)
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/configuration', methods=['PUT'])
@role_required('organizer', 'admin')
def update_contest_configuration(contest_id):
    """API Cáº¥u hÃ¬nh toÃ n bá»™ cuá»™c thi (thá»ƒ lá»‡, vÃ²ng thi vÃ  cÃ¡c tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm)."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')
    data = request.get_json(silent=True) or {}

    errors = contest_config_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dá»¯ liá»‡u cáº¥u hÃ¬nh khÃ´ng há»£p lá»‡', 'errors': errors}), 400

    try:
        contest = contest_service.update_contest_configuration(contest_id, data, user_id=user_id, user_role=user_role)
        return safe_jsonify({
            'message': 'Cáº­p nháº­t cáº¥u hÃ¬nh cuá»™c thi thÃ nh cÃ´ng',
            'contest': _serialize_model(contest) or {}
        }, status=200)
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lá»—i khi cáº­p nháº­t cáº¥u hÃ¬nh cuá»™c thi', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Finalize Round Scores API (Chá»‘t Ä‘iá»ƒm vÃ²ng thi)
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/winners', methods=['GET'])
@role_required('organizer', 'admin')
def get_round_winners(contest_id, round_id):
    """Return leaderboard candidates for organizer winner approval."""
    try:
        data, error = score_service.get_winner_candidates(contest_id, round_id)
        if error == 'contest_not_found':
            return jsonify({'success': False, 'message': 'Contest not found'}), 404
        if error == 'round_not_found':
            return jsonify({'success': False, 'message': 'Round not found'}), 404
        if error == 'round_not_in_contest':
            return jsonify({'success': False, 'message': 'Round does not belong to this contest'}), 400
        if error:
            return jsonify({'success': False, 'message': f'Unable to load winner candidates: {error}'}), 400

        return jsonify({**data, 'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': 'System error while loading winner candidates', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/winners/<int:submission_id>', methods=['PATCH'])
@role_required('organizer', 'admin')
def decide_winner(contest_id, round_id, submission_id):
    """Approve or reject a winner candidate and publish to the archive when approved."""
    payload = request.get_json(silent=True) or {}
    decision = str(payload.get('decision', '')).strip().lower()
    award_title = payload.get('award_title')
    reason = payload.get('reason')

    try:
        result, error = score_service.handle_winner_decision(
            contest_id=contest_id,
            round_id=round_id,
            submission_id=submission_id,
            decision=decision,
            award_title=award_title,
            reason=reason,
        )

        if error == 'invalid_decision':
            return jsonify({'success': False, 'message': 'Decision must be approve or reject'}), 400
        if error == 'contest_not_found':
            return jsonify({'success': False, 'message': 'Contest not found'}), 404
        if error == 'round_not_found':
            return jsonify({'success': False, 'message': 'Round not found'}), 404
        if error == 'round_not_in_contest':
            return jsonify({'success': False, 'message': 'Round does not belong to this contest'}), 400
        if error == 'submission_not_found':
            return jsonify({'success': False, 'message': 'Submission not found'}), 404
        if error == 'submission_not_in_round':
            return jsonify({'success': False, 'message': 'Submission does not belong to this round'}), 400
        if error:
            return jsonify({'success': False, 'message': f'Unable to update winner status: {error}'}), 400

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'message': 'System error while processing winner decision', 'error': str(e)}), 500


@contest_bp.route('/rounds/<int:round_id>/finalize', methods=['POST'])
@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/finalize', methods=['POST'])
@role_required('organizer', 'admin')
def finalize_round(round_id, contest_id=None):
    """API Chá»‘t Ä‘iá»ƒm má»™t vÃ²ng thi."""
    try:
        data, error = score_service.finalize_round(round_id)
        if error == 'round_not_found':
            return jsonify({'message': 'Không tìm thấy vòng thi'}), 404
        if error == 'round_already_finalized':
            return jsonify({'message': 'Vòng thi đã được chốt trước đó'}), 400

        if error:
            return jsonify({'message': f'Lá»—i chá»‘t Ä‘iá»ƒm: {error}'}), 400

        return jsonify(data), 200
    except Exception as e:
        return jsonify({'message': 'Lá»—i há»‡ thá»‘ng khi chá»‘t Ä‘iá»ƒm vÃ²ng thi', 'error': str(e)}), 500


