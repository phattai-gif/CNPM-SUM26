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
            'message': 'Dá»¯ liá»‡u phÃ¢n cÃ´ng khÃ´ng há»£p lá»‡',
            'errors': errors
        }), 400

    judge_id = data.get('judge_id')
    judge_ids = data.get('judge_ids')
    submission_id = data.get('submission_id')

    try:
        # PhÃ¢n cÃ´ng nhiá»u giÃ¡m kháº£o
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
                    f'ÄÃ£ phÃ¢n cÃ´ng {len(assignments)} '
                    'giÃ¡m kháº£o vÃ o vÃ²ng thi thÃ nh cÃ´ng'
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
            'message': 'PhÃ¢n cÃ´ng giÃ¡m kháº£o thÃ nh cÃ´ng',
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
            'message': 'Lá»—i khi phÃ¢n cÃ´ng giÃ¡m kháº£o',
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
                'Láº¥y danh sÃ¡ch giÃ¡m kháº£o Ä‘Æ°á»£c '
                'phÃ¢n cÃ´ng thÃ nh cÃ´ng'
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
            'message': 'Lá»—i khi láº¥y danh sÃ¡ch giÃ¡m kháº£o',
            'error': str(e)
        }), 500

@judge_bp.route(
    '/organizer/contests/<int:contest_id>/rounds/'
    '<int:round_id>/judges/<int:judge_id>',
    methods=['DELETE']
)
@role_required('organizer')
def remove_judge_from_round(contest_id, round_id, judge_id):
    """API Há»§y phÃ¢n cÃ´ng giÃ¡m kháº£o khá»i vÃ²ng thi."""

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
                'message': 'Há»§y phÃ¢n cÃ´ng giÃ¡m kháº£o thÃ nh cÃ´ng'
            }), 200

        return jsonify({
            'message': (
                'KhÃ´ng tÃ¬m tháº¥y phÃ¢n cÃ´ng giÃ¡m kháº£o Ä‘á»ƒ há»§y'
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
            'message': 'Lá»—i khi há»§y phÃ¢n cÃ´ng giÃ¡m kháº£o',
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
                'Láº¥y danh sÃ¡ch nhiá»‡m vá»¥ cháº¥m thi thÃ nh cÃ´ng'
            ),
            'assignments': _serialize_assignments(assignments)
        }, status=200)

    except Exception as e:
        return jsonify({
            'message': 'Lá»—i khi láº¥y danh sÃ¡ch nhiá»‡m vá»¥ cháº¥m thi',
            'error': str(e)
        }), 500


# Simple judge grading UI for direct testing at /judge/<id>
@judge_ui_bp.route('/<int:submission_id>', methods=['GET', 'POST'])
@role_required('judge', 'admin')
def judge_grading_ui(submission_id):
    """Render the assigned submission with its real files and film metadata."""
    try:
        user = _request_user()
        user_id = user.get('user_id')
        user_role = user.get('role', 'judge')
        result = submission_repository.get_by_id_with_details(submission_id)
        if not result:
            return jsonify({'message': 'Submission not found'}), 404

        submission_model, file_models, film_metadata = result
        assignment_query = submission_repository.session.query(JudgeAssignmentModel).filter(
            JudgeAssignmentModel.round_id == submission_model.round_id,
            JudgeAssignmentModel.judge_id == user_id,
            JudgeAssignmentModel.status == 'assigned',
        )
        assignments = assignment_query.all()
        is_assigned = str(user_role).lower() == 'admin' or any(
            assignment.submission_id is None
            or assignment.submission_id == submission_id
            for assignment in assignments
        )
        if not is_assigned:
            return jsonify({'message': 'Judge is not assigned to this submission'}), 403

        files_by_type = {}
        for file_model in file_models or []:
            file_type = getattr(file_model, 'file_type', 'main_image')
            files_by_type.setdefault(file_type, file_model)
        main_file = (
            files_by_type.get('main_image')
            or files_by_type.get('main')
            or (file_models or [None])[0]
        )
        negative_file = files_by_type.get('negative') or files_by_type.get('negative_film')
        contact_file = files_by_type.get('contact_sheet')

        submission = {
            'id': submission_model.id,
            'title': submission_model.title,
            'image_url': getattr(main_file, 'image_hd_url', None),
            'image_hd_url': getattr(main_file, 'image_hd_url', None),
            'negative_film_url': getattr(negative_file, 'image_hd_url', None),
            'contact_sheet_url': getattr(contact_file, 'image_hd_url', None),
            'proof_attachments': [
                {
                    'label': getattr(file_model, 'file_type', 'Attachment'),
                    'url': file_model.image_hd_url,
                }
                for file_model in (file_models or [])
                if getattr(file_model, 'file_type', 'main_image') not in {
                    'main_image', 'main', 'negative', 'negative_film', 'contact_sheet'
                }
            ],
            'camera': getattr(film_metadata, 'camera_body', None) or 'Not provided',
            'film_stock': getattr(film_metadata, 'film_stock', None) or 'Not provided',
            'prev_id': None,
            'next_id': None,
        }

        assigned_submissions = (
            submission_repository.session
            .query(SubmissionModel)
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
            .order_by(
                SubmissionModel.submitted_at.asc(),
                SubmissionModel.id.asc(),
            )
            .distinct()
            .all()
        )
        assigned_ids = [item.id for item in assigned_submissions]
        if submission_id in assigned_ids:
            current_index = assigned_ids.index(submission_id)
            submission['prev_id'] = (
                assigned_ids[current_index - 1]
                if current_index > 0 else None
            )
            submission['next_id'] = (
                assigned_ids[current_index + 1]
                if current_index < len(assigned_ids) - 1 else None
            )

        # Criteria and AI flags belong to the real submission round.
        criteria_models = score_service.contest_repo.get_criteria_by_round_id(
            submission_model.round_id
        ) or []
        criteria_list = [
            {
                'id': criterion.id,
                'name': criterion.name,
                'max': criterion.max_score,
                'weight': criterion.weight,
            }
            for criterion in criteria_models
        ]

        ai_session = submission_repository.session
        ai_flags = (
            ai_session.query(AIFlagModel)
            .filter(AIFlagModel.submission_id == submission_id)
            .order_by(AIFlagModel.id.asc())
            .all()
        )
        ai_reports = (
            ai_session.query(AIAnalysisReportModel)
            .filter(AIAnalysisReportModel.submission_id == submission_id)
            .order_by(AIAnalysisReportModel.created_at.asc(), AIAnalysisReportModel.id.asc())
            .all()
        )
        reports_by_flag = {
            report.ai_flag_id: report
            for report in ai_reports
            if report.ai_flag_id is not None
        }
        duplicate_flag = next(
            (flag for flag in ai_flags if 'duplicate' in flag.flag_type.lower()),
            None,
        )
        metadata_flag = next(
            (flag for flag in ai_flags if 'metadata' in flag.flag_type.lower()),
            None,
        )
        duplicate_report = reports_by_flag.get(
            getattr(duplicate_flag, 'id', None)
        )
        duplicate_details = (
            duplicate_report.raw_details
            if duplicate_report is not None and isinstance(duplicate_report.raw_details, dict)
            else {}
        )
        similarity_value = (
            duplicate_details.get('duplicate_similarity')
            or duplicate_details.get('similarity_score')
            or duplicate_details.get('similarity')
            or getattr(duplicate_flag, 'confidence_score', None)
            or getattr(duplicate_report, 'ai_confidence_score', None)
        )
        risk_levels = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        risk_flag = max(
            ai_flags,
            key=lambda flag: risk_levels.get(str(flag.risk_level).lower(), 0),
            default=None,
        )
        review_statuses = [str(flag.status).replace('_', ' ').title() for flag in ai_flags]
        metadata_details = (
            reports_by_flag.get(getattr(metadata_flag, 'id', None))
            if metadata_flag is not None else None
        )
        metadata_raw = (
            metadata_details.raw_details
            if metadata_details is not None and isinstance(metadata_details.raw_details, dict)
            else {}
        )
        try:
            numeric_similarity = float(similarity_value) if similarity_value is not None else None
        except (TypeError, ValueError):
            numeric_similarity = None
        if numeric_similarity is not None and numeric_similarity <= 1:
            numeric_similarity *= 100
        metadata_status = (
            metadata_raw.get('metadata_status')
            or metadata_raw.get('comparison_status')
            or ('Mismatch' if metadata_flag is not None else None)
        )
        ai_warning = {
            'verification': (
                'Pending' if not ai_flags and not ai_reports
                else 'Review Required' if any(flag.status == 'pending' for flag in ai_flags)
                else 'Completed'
            ),
            'risk': getattr(risk_flag, 'risk_level', None) or 'Pending',
            'duplicate_similarity': (
                f'{numeric_similarity:.0f}%'
                if numeric_similarity is not None else 'Pending'
            ),
            'metadata_status': metadata_status or 'Pending',
            'review_status': ', '.join(review_statuses) if review_statuses else 'Pending',
        }

        grading_state = session.get('judge_grading', {}).get(str(submission_id), {})
        existing_scores = grading_state.get(
            'scores',
            {str(c['id']): None for c in criteria_list},
        )
        existing_comment = grading_state.get('comment', '')
        is_finalized = bool(grading_state.get('is_finalized', False))

        if request.method == 'POST':
            form = request.form.to_dict(flat=True)
            existing_comment = form.get('comment', '')
            action = form.get('action', 'save_draft')
            submitted_scores = {}
            for crit in criteria_list:
                key = str(crit['id'])
                val = form.get(key)
                try:
                    submitted_scores[key] = int(val) if val is not None and val != '' else None
                except ValueError:
                    submitted_scores[key] = None

            if is_finalized:
                flash('Bài chấm đã finalized và không thể chỉnh sửa.')
                return redirect(url_for('judge_ui.judge_grading_ui', submission_id=submission_id))

            if action == 'finalize' and any(
                submitted_scores.get(str(criterion['id'])) is None
                for criterion in criteria_list
            ):
                flash('Vui lòng nhập đủ điểm cho tất cả criteria trước khi finalize.')
                return redirect(url_for('judge_ui.judge_grading_ui', submission_id=submission_id))

            grading_states = dict(session.get('judge_grading', {}))
            grading_states[str(submission_id)] = {
                'scores': submitted_scores,
                'comment': existing_comment,
                'is_finalized': action == 'finalize',
            }
            session['judge_grading'] = grading_states
            flash(
                'Bài chấm đã finalized.'
                if action == 'finalize'
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
        return jsonify({'message': 'Failed to load submission', 'error': str(e)}), 500
        
