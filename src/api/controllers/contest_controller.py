from flask import Blueprint, render_template, request, jsonify
from flask import flash, redirect, url_for
from datetime import datetime

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

contest_create_schema = ContestCreateRequestSchema()
contest_update_schema = ContestUpdateRequestSchema()
contest_rules_schema = ContestRulesUpdateRequestSchema()
contest_config_schema = ContestConfigurationRequestSchema()
contest_response_schema = ContestResponseSchema()
round_schema = RoundSchema()
criteria_schema = CriteriaSchema()


# -------------------------------------------------------------------------
# Legacy HTML Dashboard Routes
# -------------------------------------------------------------------------

@contest_bp.route('/dashboard', methods=['GET'])
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
def organizer_contest_detail_page():
    """Render frontend contest detail page which will fetch contest details via API."""
    # Page itself doesn't require server-side authentication; JS will call protected API using token
    return render_template('organizer_contest_detail.html')


@contest_bp.route('/dashboard/metrics', methods=['GET'])
@role_required('organizer', 'admin')
def organizer_dashboard_metrics():
    """Return simple aggregated metrics for the organizer dashboard."""
    user_id = request.user.get('user_id')
    try:
        contests = contest_service.list_organizer_contests(user_id)
        total_contests = len(contests)
        # Use repository session to compute totals across contests' rounds
        session = contest_service.repository.session
        try:
            from src.infrastructure.models.submission_model import SubmissionModel
            from src.infrastructure.models.judge_assignment_model import JudgeAssignmentModel
        except Exception:
            from infrastructure.models.submission_model import SubmissionModel
            from infrastructure.models.judge_assignment_model import JudgeAssignmentModel
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
        from src.services.submission_service import SubmissionService
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
    """API Tạo cuộc thi mới."""
    user_id = request.user.get('user_id')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = contest_create_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dữ liệu không hợp lệ', 'errors': errors}), 400

    try:
        contest = contest_service.create_contest(data, user_id=user_id)
        return jsonify({
            'message': 'Tạo cuộc thi thành công',
            'contest': contest.to_dict()
        }), 201
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except Exception as e:
        return jsonify({'message': 'Lỗi khi tạo cuộc thi', 'error': str(e)}), 500


@contest_bp.route('/contests', methods=['GET'])
@role_required('organizer', 'admin')
def list_contests():
    """API Liệt kê danh sách cuộc thi của Organizer."""
    user_id = request.user.get('user_id')
    contests = contest_service.list_organizer_contests(user_id)
    # Enhance with submissions_count and judges_count per contest
    try:
        session = contest_service.repository.session
        # import models with fallback
        try:
            from src.infrastructure.models.submission_model import SubmissionModel
            from src.infrastructure.models.judge_assignment_model import JudgeAssignmentModel
        except Exception:
            from infrastructure.models.submission_model import SubmissionModel
            from infrastructure.models.judge_assignment_model import JudgeAssignmentModel

        contests_out = []
        for c in contests:
            cdict = c.to_dict()
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

        return jsonify({
            'message': 'Lấy danh sách cuộc thi thành công',
            'contests': contests_out
        }), 200
    except Exception:
        return jsonify({
            'message': 'Lấy danh sách cuộc thi thành công',
            'contests': [c.to_dict() for c in contests]
        }), 200


@contest_bp.route('/contests/<int:contest_id>', methods=['GET'])
@role_required('organizer', 'admin')
def get_contest(contest_id):
    """API Lấy thông tin chi tiết cuộc thi (bao gồm thể lệ, vòng thi, tiêu chí)."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    contest = contest_service.get_contest(contest_id)
    if not contest:
        return jsonify({'message': 'Không tìm thấy cuộc thi'}), 404

    if user_role != 'admin' and contest.created_by != user_id:
        return jsonify({'message': 'Bạn không có quyền xem cuộc thi này'}), 403

    return jsonify({
        'message': 'Lấy thông tin cuộc thi thành công',
        'contest': contest.to_dict()
    }), 200


@contest_bp.route('/contests/<int:contest_id>', methods=['PUT'])
@role_required('organizer', 'admin')
def update_contest(contest_id):
    """API Cập nhật thông tin cuộc thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = contest_update_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dữ liệu không hợp lệ', 'errors': errors}), 400

    try:
        contest = contest_service.update_contest(contest_id, data, user_id=user_id, user_role=user_role)
        return jsonify({
            'message': 'Cập nhật cuộc thi thành công',
            'contest': contest.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi cập nhật cuộc thi', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def delete_contest(contest_id):
    """API Xóa cuộc thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        contest_service.delete_contest(contest_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Xóa cuộc thi thành công'}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 404
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi xóa cuộc thi', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Contest Rules (Thể lệ cuộc thi) APIs
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/rules', methods=['PUT'])
@role_required('organizer', 'admin')
def update_contest_rules(contest_id):
    """API Cập nhật thể lệ cuộc thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = contest_rules_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dữ liệu thể lệ không hợp lệ', 'errors': errors}), 400

    try:
        contest = contest_service.update_rules(contest_id, rules=data.get('rules', ''), user_id=user_id, user_role=user_role)
        return jsonify({
            'message': 'Cập nhật thể lệ cuộc thi thành công',
            'contest': contest.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi cập nhật thể lệ', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Contest Round (Vòng thi) APIs
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/rounds', methods=['POST'])
@role_required('organizer', 'admin')
def create_round(contest_id):
    """API Thêm vòng thi mới cho cuộc thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = round_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dữ liệu vòng thi không hợp lệ', 'errors': errors}), 400

    try:
        round_obj = contest_service.create_round(contest_id, data, user_id=user_id, user_role=user_role)
        return jsonify({
            'message': 'Tạo vòng thi thành công',
            'round': round_obj.to_dict()
        }), 201
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi tạo vòng thi', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>', methods=['PUT'])
@role_required('organizer', 'admin')
def update_round(contest_id, round_id):
    """API Cập nhật thông tin vòng thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    try:
        round_obj = contest_service.update_round(contest_id, round_id, data, user_id=user_id, user_role=user_role)
        return jsonify({
            'message': 'Cập nhật vòng thi thành công',
            'round': round_obj.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi cập nhật vòng thi', 'error': str(e)}), 500


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
        return jsonify({'message': 'Lỗi khi xóa vòng thi', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Criteria (Tiêu chí chấm điểm) APIs
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/criteria', methods=['POST'])
@role_required('organizer', 'admin')
def create_criteria(contest_id, round_id):
    """API Thêm tiêu chí chấm điểm cho vòng thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = criteria_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dữ liệu tiêu chí không hợp lệ', 'errors': errors}), 400

    try:
        crit = contest_service.create_criteria(contest_id, round_id, data, user_id=user_id, user_role=user_role)
        return jsonify({
            'message': 'Tạo tiêu chí chấm điểm thành công',
            'criteria': crit.to_dict()
        }), 201
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi tạo tiêu chí chấm điểm', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/criteria/<int:criteria_id>', methods=['PUT'])
@role_required('organizer', 'admin')
def update_criteria(contest_id, round_id, criteria_id):
    """API Cập nhật tiêu chí chấm điểm."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    try:
        crit = contest_service.update_criteria(contest_id, round_id, criteria_id, data, user_id=user_id, user_role=user_role)
        return jsonify({
            'message': 'Cập nhật tiêu chí chấm điểm thành công',
            'criteria': crit.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi cập nhật tiêu chí chấm điểm', 'error': str(e)}), 500


@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/criteria/<int:criteria_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def delete_criteria(contest_id, round_id, criteria_id):
    """API Xóa tiêu chí chấm điểm."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        contest_service.delete_criteria(contest_id, round_id, criteria_id, user_id=user_id, user_role=user_role)
        return jsonify({'message': 'Xóa tiêu chí chấm điểm thành công'}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi xóa tiêu chí chấm điểm', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Bulk Contest Configuration API (Đồng bộ Thể lệ, Vòng thi & Tiêu chí)
# -------------------------------------------------------------------------

@contest_bp.route('/contests/<int:contest_id>/configuration', methods=['PUT'])
@role_required('organizer', 'admin')
def update_contest_configuration(contest_id):
    """API Cấu hình toàn bộ cuộc thi (thể lệ, vòng thi và các tiêu chí chấm điểm)."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or {}

    errors = contest_config_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dữ liệu cấu hình không hợp lệ', 'errors': errors}), 400

    try:
        contest = contest_service.update_contest_configuration(contest_id, data, user_id=user_id, user_role=user_role)
        return jsonify({
            'message': 'Cập nhật cấu hình cuộc thi thành công',
            'contest': contest.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi cập nhật cấu hình cuộc thi', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Finalize Round Scores API (Chốt điểm vòng thi)
# -------------------------------------------------------------------------

@contest_bp.route('/rounds/<int:round_id>/finalize', methods=['POST'])
@contest_bp.route('/contests/<int:contest_id>/rounds/<int:round_id>/finalize', methods=['POST'])
@role_required('organizer', 'admin')
def finalize_round(round_id, contest_id=None):
    """API Chốt điểm một vòng thi."""
    try:
        data, error = score_service.finalize_round(round_id)
        if error == 'round_not_found':
            return jsonify({'message': 'Không tìm thấy vòng thi'}), 404
        if error == 'round_already_finalized':
            return jsonify({'message': 'Vòng thi đã được chốt trước đó'}), 400

        if error:
            return jsonify({'message': f'Lỗi chốt điểm: {error}'}), 400

        return jsonify(data), 200
    except Exception as e:
        return jsonify({'message': 'Lỗi hệ thống khi chốt điểm vòng thi', 'error': str(e)}), 500


