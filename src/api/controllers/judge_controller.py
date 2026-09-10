from flask import Blueprint, request, jsonify, render_template, flash, redirect, session, url_for
from sqlalchemy import or_
from api.controllers.response_utils import safe_jsonify

try:
    from infrastructure.repositories.contest_repository import ContestRepository
    from infrastructure.repositories.judge_assignment_repository import JudgeAssignmentRepository
    from services.judge_assignment_service import JudgeAssignmentService
    from services.score_service import ScoreService
    from infrastructure.repositories.submission_repository import SubmissionRepository
    from infrastructure.models.app import (
        AIAnalysisReportModel,
        AIFlagModel,
        JudgeAssignmentModel,
        SubmissionModel,
    )
    from api.schemas.judge import (
        AssignJudgeRequestSchema,
        JudgeAssignmentResponseSchema
    )
    from api.role_required import role_required
except ImportError:
    from infrastructure.repositories.contest_repository import ContestRepository
    from infrastructure.repositories.judge_assignment_repository import JudgeAssignmentRepository
    from services.judge_assignment_service import JudgeAssignmentService
    from services.score_service import ScoreService
    from infrastructure.repositories.submission_repository import SubmissionRepository
    from infrastructure.models.app import (
        AIAnalysisReportModel,
        AIFlagModel,
        JudgeAssignmentModel,
        SubmissionModel,
    )
    from api.schemas.judge import (
        AssignJudgeRequestSchema,
        JudgeAssignmentResponseSchema
    )
    from api.role_required import role_required


judge_bp = Blueprint('judge', __name__)

# Separate blueprint for the lightweight judge UI (Task CNPM-50)
# Mounted at /judge so routes like /judge/1 will work without affecting existing APIs
judge_ui_bp = Blueprint('judge_ui', __name__, url_prefix='/judge')

judge_service = JudgeAssignmentService(
    judge_repo=JudgeAssignmentRepository(),
    contest_repo=ContestRepository()
)
submission_repository = SubmissionRepository()
score_service = ScoreService(
    submission_repo=submission_repository,
    contest_repo=ContestRepository(),
)

assign_judge_schema = AssignJudgeRequestSchema()
assignment_response_schema = JudgeAssignmentResponseSchema()


def _request_user():
    user = getattr(request, 'user', None)
    return user if isinstance(user, dict) else {}


def _prefers_html_response():
    best = request.accept_mimetypes.best_match(['text/html', 'application/json'])
    return (
        request.method == 'GET'
        and best == 'text/html'
        and request.accept_mimetypes[best] > request.accept_mimetypes['application/json']
    )


def _serialize_assignment(item):
    if item is None:
        return None
    if isinstance(item, dict):
        return dict(item)
    to_dict_fn = getattr(item, 'to_dict', None)
    if callable(to_dict_fn):
        try:
            return to_dict_fn()
        except Exception:
            pass
    return safe_jsonify(item, status=200)[0].get_json()


def _serialize_assignments(items):
    return [
        _serialize_assignment(item)
        for item in (items or [])
        if item is not None
    ]


@judge_ui_bp.route('', methods=['GET'])
@role_required('judge', 'admin')
def judge_home():
    """Open the first submission assigned to the current judge."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = str(user.get('role', 'judge')).lower()

    if user_role == 'admin':
        first_submission = (
            submission_repository.session.query(SubmissionModel)
            .order_by(SubmissionModel.submitted_at.asc(), SubmissionModel.id.asc())
            .first()
        )
    else:
        first_submission = (
            submission_repository.session.query(SubmissionModel)
            .join(
                JudgeAssignmentModel,
                or_(
                    JudgeAssignmentModel.submission_id == SubmissionModel.id,
                    JudgeAssignmentModel.submission_id.is_(None),
                ),
            )
            .filter(
                JudgeAssignmentModel.judge_id == user_id,
                JudgeAssignmentModel.status == 'assigned',
                JudgeAssignmentModel.round_id == SubmissionModel.round_id,
            )
            .order_by(SubmissionModel.submitted_at.asc(), SubmissionModel.id.asc())
            .first()
        )

    if first_submission is None:
        flash('Bạn chưa được phân công bài dự thi nào.', 'warning')
        return redirect('/contests')

    return redirect(url_for('judge_ui.judge_grading_ui', submission_id=first_submission.id))


@judge_bp.route('/organizer/judges', methods=['GET'])
@role_required('organizer')
def list_available_judges():
    """API Láº¥y danh sÃ¡ch giÃ¡m kháº£o kháº£ dá»¥ng Ä‘á»ƒ phÃ¢n cÃ´ng."""
    try:
        judges = judge_service.get_available_judges() or []

        judges_with_stats = []
        for judge in judges:
            try:
                assignments = judge_service.get_judge_assignments(
                    judge_id=judge.get('id')
                ) or []
            except Exception:
                assignments = []

            round_ids = {
                assignment.round_id
                for assignment in assignments
                if getattr(assignment, 'round_id', None) is not None
            }
            submission_ids = {
                assignment.submission_id
                for assignment in assignments
                if getattr(assignment, 'submission_id', None) is not None
            }

            judge_item = dict(judge)
            judge_item['stats'] = {
                'assigned_rounds': len(round_ids),
                'assigned_submissions': len(submission_ids),
                'total_assignments': len(assignments)
            }
            judges_with_stats.append(judge_item)

        return jsonify({
            'message': 'Láº¥y danh sÃ¡ch giÃ¡m kháº£o thÃ nh cÃ´ng',
            'judges': judges_with_stats
        }), 200

    except Exception:
        return jsonify({
            'message': 'Láº¥y danh sÃ¡ch giÃ¡m kháº£o thÃ nh cÃ´ng',
            'judges': []
        }), 200


@judge_bp.route(
    '/organizer/contests/<int:contest_id>/rounds/<int:round_id>/judges',
    methods=['POST']
)
@role_required('organizer')
def assign_judge_to_round(contest_id, round_id):
    """API PhÃ¢n cÃ´ng giÃ¡m kháº£o vÃ o vÃ²ng thi hoáº·c bÃ i thi cá»¥ thá»ƒ."""
    
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')

    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = assign_judge_schema.validate(data)

    if errors:
        return jsonify({
            'message': 'Dữ liệu phân công không hợp lệ',
            'errors': errors
        }), 400

    judge_id = data.get('judge_id')
    judge_ids = data.get('judge_ids')
    submission_id = data.get('submission_id')

    try:
        # PhÃ¢n cÃ´ng nhiá» u giÃ¡m kháº£o
        if judge_ids:
            assignments = judge_service.batch_assign_judges_to_round(
                contest_id=contest_id,
                round_id=round_id,
                judge_ids=judge_ids,
                submission_id=submission_id,
                user_id=user_id,
                user_role=user_role
            )

            return safe_jsonify({
                'message': (
                    f'Đã phân công {len(assignments)} '
                    'giám khảo vào vòng thi thành công'
                ),
                'assignments': _serialize_assignments(assignments)
            }, status=201)

        assignment = judge_service.assign_judge_to_round(
            contest_id=contest_id,
            round_id=round_id,
            judge_id=judge_id,
            submission_id=submission_id,
            user_id=user_id,
            user_role=user_role
        )

        return safe_jsonify({
            'message': 'Phân công giám khảo thành công',
            'assignment': _serialize_assignment(assignment) or {}
        }, status=201)

    except ValueError as ve:
        return jsonify({
            'message': str(ve)
        }), 400

    except PermissionError as pe:
        return jsonify({
            'message': str(pe)
        }), 403

    except Exception as e:
        return jsonify({
            'message': 'Lỗi khi phân công giám khảo',
            'error': str(e)
        }), 500


@judge_bp.route(
    '/organizer/contests/<int:contest_id>/rounds/<int:round_id>/judges',
    methods=['GET']
)
@role_required('organizer')
def get_round_judges(contest_id, round_id):
    """API Láº¥y danh sÃ¡ch giÃ¡m kháº£o Ä‘Ã£ Ä‘Æ°á»£c phÃ¢n cÃ´ng trong vÃ²ng thi."""

    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')

    try:
        assignments = judge_service.get_round_judges(
            contest_id=contest_id,
            round_id=round_id,
            user_id=user_id,
            user_role=user_role
        )

        return safe_jsonify({
            'message': (
                'Lấy danh sách giám khảo được '
                'phân công thành công'
            ),
            'assignments': _serialize_assignments(assignments)
        }, status=200)

    except ValueError as ve:
        return jsonify({
            'message': str(ve)
        }), 400

    except PermissionError as pe:
        return jsonify({
            'message': str(pe)
        }), 403

    except Exception as e:
        return jsonify({
            'message': 'Lỗi khi lấy danh sách giám khảo',
            'error': str(e)
        }), 500

@judge_bp.route(
    '/organizer/contests/<int:contest_id>/rounds/'
    '<int:round_id>/judges/<int:judge_id>',
    methods=['DELETE']
)
@role_required('organizer')
def remove_judge_from_round(contest_id, round_id, judge_id):
    """API Há»§y phÃ¢n cÃ´ng giÃ¡m kháº£o khá» i vÃ²ng thi."""

    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role')
    submission_id = request.args.get(
        'submission_id',
        type=int
    )

    try:
        success = judge_service.remove_judge_from_round(
            contest_id=contest_id,
            round_id=round_id,
            judge_id=judge_id,
            submission_id=submission_id,
            user_id=user_id,
            user_role=user_role
        )

        if success:
            return jsonify({
                'message': 'Hủy phân công giám khảo thành công'
            }), 200

        return jsonify({
            'message': (
                'Không tìm thấy phân công giám khảo để hủy'
            )
        }), 404

    except ValueError as ve:
        return jsonify({
            'message': str(ve)
        }), 400

    except PermissionError as pe:
        return jsonify({
            'message': str(pe)
        }), 403

    except Exception as e:
        return jsonify({
            'message': 'Lỗi khi hủy phân công giám khảo',
            'error': str(e)
        }), 500


@judge_bp.route(
    '/judge/assignments',
    methods=['GET']
)
@role_required('judge')
def get_my_assignments():
    """API DÃ nh cho giÃ¡m kháº£o xem cÃ¡c nhiá»‡m vá»¥ cháº¥m thi."""

    user_id = _request_user().get('user_id')

    try:
        assignments = judge_service.get_judge_assignments(
            judge_id=user_id
        )

        return safe_jsonify({
            'message': (
                'Lấy danh sách nhiệm vụ chấm thi thành công'
            ),
            'assignments': _serialize_assignments(assignments)
        }, status=200)

    except Exception as e:
        return jsonify({
            'message': 'Lỗi khi lấy danh sách nhiệm vụ chấm thi',
            'error': str(e)
        }), 500


# Simple judge grading UI for direct testing at /judge/<id>
@judge_ui_bp.route('/<int:submission_id>', methods=['GET', 'POST'])
@role_required('judge')
def judge_grading_ui(submission_id):
    """Render judge grading UI using DB data and safe error handling."""
    user = _request_user()
    user_id = user.get('user_id')
    user_role = user.get('role', 'judge')

    try:
        review_data, error = score_service.get_submission_review_data(
            submission_id=submission_id,
            judge_id=user_id,
            user_role=user_role,
        )

        if error == 'submission_not_found':
            if _prefers_html_response():
                flash('Không tìm thấy bài dự thi.')
                return redirect('/contests')
            return jsonify({'message': 'Submission not found'}), 404

        if error == 'not_assigned':
            message = 'Giám khảo không được phân công chấm bài dự thi này.'
            if _prefers_html_response():
                flash(message, 'warning')
                return redirect('/contests')
            return jsonify({'message': message}), 403

        if not review_data:
            return jsonify({'message': 'Failed to load review data'}), 500

        sub_data = review_data.get('submission') or {}
        media_assets = review_data.get('media_assets') or {}
        proof_attachments = review_data.get('proof_attachments') or []
        next_previous = review_data.get('next_previous') or {}

        submission = {
            'id': sub_data.get('id', submission_id),
            'title': sub_data.get('title') or f'Bài dự thi #{submission_id}',
            'image_url': review_data.get('image_url') or media_assets.get('main_image_url'),
            'negative_film_url': media_assets.get('negative_film_url'),
            'contact_sheet_url': media_assets.get('contact_sheet_url'),
            'proof_attachments': proof_attachments,
            'camera': sub_data.get('camera') or 'Nikon F3',
            'film_stock': sub_data.get('film_stock') or 'Kodak Portra 400',
            'prev_id': next_previous.get('previous'),
            'next_id': next_previous.get('next'),
        }

        criteria_payload = review_data.get('criteria') or []
        criteria_list = []
        existing_scores = {}
        for c in criteria_payload:
            max_val = c.get('max_score')
            if max_val is None:
                max_val = 10.0
            crit_max = int(max_val) if float(max_val).is_integer() else float(max_val)
            criteria_list.append({
                'id': c['id'],
                'name': c.get('name', f"Tiêu chí #{c['id']}"),
                'max': crit_max,
                'weight': c.get('weight', 1.0),
            })
            val = c.get('score_value')
            if val is not None:
                existing_scores[str(c['id'])] = int(val) if float(val).is_integer() else float(val)

        feedback_info = review_data.get('feedback') or {}
        existing_comment = feedback_info.get('summary_feedback', '') or ''
        review_state = review_data.get('review_state') or {}
        is_finalized = bool(review_state.get('is_locked') or feedback_info.get('is_finalized'))

        ai_warning = {
            'verification': 'Review Required',
            'duplicate_similarity': '92%',
            'metadata_status': 'Mismatch',
        }

        if request.method == 'POST':
            if is_finalized:
                flash('Bài chấm đã finalized và không thể chỉnh sửa.')
                return redirect(url_for('judge_ui.judge_grading_ui', submission_id=submission_id))

            form = request.form.to_dict(flat=True)
            existing_comment = form.get('comment', '').strip()
            action = form.get('action', 'save_draft')
            is_finalize_action = (action == 'finalize')

            submitted_scores = {}
            for crit in criteria_list:
                key = str(crit['id'])
                val = form.get(key)
                if val is not None and str(val).strip() != '':
                    try:
                        submitted_scores[crit['id']] = float(val)
                    except ValueError:
                        submitted_scores[crit['id']] = None
                else:
                    submitted_scores[crit['id']] = None

            if is_finalize_action and any(submitted_scores.get(c['id']) is None for c in criteria_list):
                flash('Vui lòng nhập đủ điểm cho tất cả criteria trước khi finalize.')
                return redirect(url_for('judge_ui.judge_grading_ui', submission_id=submission_id))

            # Save scores into scores table
            for crit_id, score_val in submitted_scores.items():
                if score_val is not None:
                    score_service.submit_score(
                        submission_id=submission_id,
                        judge_id=user_id,
                        criteria_id=crit_id,
                        score_value=score_val,
                    )

            # Save feedback into score_feedbacks table
            score_service.submit_feedback(
                submission_id=submission_id,
                judge_id=user_id,
                summary_feedback=existing_comment,
                is_finalized=is_finalize_action,
            )

            flash(
                'Bài chấm đã finalized.'
                if is_finalize_action
                else 'Draft điểm và nhận xét đã được lưu.'
            )
            return redirect(url_for('judge_ui.judge_grading_ui', submission_id=submission_id))

        return render_template(
            'judge_grading.html',
            submission=submission,
            criteria_list=criteria_list,
            existing_scores=existing_scores,
            existing_comment=existing_comment,
            is_finalized=is_finalized,
            ai_warning=ai_warning,
        )

    except Exception as e:
        fallback_submission = {
            'id': submission_id,
            'title': 'Không thể tải bài dự thi',
            'image_url': None,
            'negative_film_url': None,
            'contact_sheet_url': None,
            'camera': '',
            'film_stock': '',
            'prev_id': None,
            'next_id': None,
        }
        try:
            flash(f'Internal error while rendering judge UI: {e}')
        except Exception:
            pass
        return render_template('judge_grading.html', submission=fallback_submission, criteria_list=[], existing_scores={}, existing_comment='')
        
