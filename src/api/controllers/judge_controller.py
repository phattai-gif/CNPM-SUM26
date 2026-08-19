from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for

try:
    from infrastructure.repositories.contest_repository import ContestRepository
    from infrastructure.repositories.judge_assignment_repository import JudgeAssignmentRepository
    from services.judge_assignment_service import JudgeAssignmentService
    from api.schemas.judge import (
        AssignJudgeRequestSchema,
        JudgeAssignmentResponseSchema
    )
    from api.role_required import role_required
except ImportError:
    from infrastructure.repositories.contest_repository import ContestRepository
    from infrastructure.repositories.judge_assignment_repository import JudgeAssignmentRepository
    from services.judge_assignment_service import JudgeAssignmentService
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

assign_judge_schema = AssignJudgeRequestSchema()
assignment_response_schema = JudgeAssignmentResponseSchema()


@judge_bp.route('/organizer/judges', methods=['GET'])
@role_required('organizer', 'admin')
def list_available_judges():
    """API Láº¥y danh sÃ¡ch giÃ¡m kháº£o kháº£ dá»¥ng Ä‘á»ƒ phÃ¢n cÃ´ng."""
    try:
        judges = judge_service.get_available_judges()

        return jsonify({
            'message': 'Láº¥y danh sÃ¡ch giÃ¡m kháº£o thÃ nh cÃ´ng',
            'judges': judges
        }), 200

    except Exception as e:
        return jsonify({
            'message': 'Lá»—i khi láº¥y danh sÃ¡ch giÃ¡m kháº£o',
            'error': str(e)
        }), 500


@judge_bp.route(
    '/organizer/contests/<int:contest_id>/rounds/<int:round_id>/judges',
    methods=['POST']
)
@role_required('organizer', 'admin')
def assign_judge_to_round(contest_id, round_id):
    """API PhÃ¢n cÃ´ng giÃ¡m kháº£o vÃ o vÃ²ng thi hoáº·c bÃ i thi cá»¥ thá»ƒ."""
    
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

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

            return jsonify({
                'message': (
                    f'ÄÃ£ phÃ¢n cÃ´ng {len(assignments)} '
                    'giÃ¡m kháº£o vÃ o vÃ²ng thi thÃ nh cÃ´ng'
                ),
                'assignments': [
                    assignment.to_dict()
                    for assignment in assignments
                ]
            }), 201

        assignment = judge_service.assign_judge_to_round(
            contest_id=contest_id,
            round_id=round_id,
            judge_id=judge_id,
            submission_id=submission_id,
            user_id=user_id,
            user_role=user_role
        )

        return jsonify({
            'message': 'PhÃ¢n cÃ´ng giÃ¡m kháº£o thÃ nh cÃ´ng',
            'assignment': assignment.to_dict()
        }), 201

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
@role_required('organizer', 'admin')
def get_round_judges(contest_id, round_id):
    """API Láº¥y danh sÃ¡ch giÃ¡m kháº£o Ä‘Ã£ Ä‘Æ°á»£c phÃ¢n cÃ´ng trong vÃ²ng thi."""

    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

    try:
        assignments = judge_service.get_round_judges(
            contest_id=contest_id,
            round_id=round_id,
            user_id=user_id,
            user_role=user_role
        )

        return jsonify({
            'message': (
                'Láº¥y danh sÃ¡ch giÃ¡m kháº£o Ä‘Æ°á»£c '
                'phÃ¢n cÃ´ng thÃ nh cÃ´ng'
            ),
            'assignments': [
                assignment.to_dict()
                for assignment in assignments
            ]
        }), 200

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
@role_required('organizer', 'admin')
def remove_judge_from_round(contest_id, round_id, judge_id):
    """API Há»§y phÃ¢n cÃ´ng giÃ¡m kháº£o khá»i vÃ²ng thi."""

    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
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
@role_required('judge', 'admin')
def get_my_assignments():
    """API DÃ nh cho giÃ¡m kháº£o xem cÃ¡c nhiá»‡m vá»¥ cháº¥m thi."""

    user_id = request.user.get('user_id')

    try:
        assignments = judge_service.get_judge_assignments(
            judge_id=user_id
        )

        return jsonify({
            'message': (
                'Láº¥y danh sÃ¡ch nhiá»‡m vá»¥ cháº¥m thi thÃ nh cÃ´ng'
            ),
            'assignments': [
                assignment.to_dict()
                for assignment in assignments
            ]
        }), 200

    except Exception as e:
        return jsonify({
            'message': 'Lá»—i khi láº¥y danh sÃ¡ch nhiá»‡m vá»¥ cháº¥m thi',
            'error': str(e)
        }), 500


# Simple judge grading UI for direct testing at /judge/<id>
@judge_ui_bp.route('/<int:submission_id>', methods=['GET', 'POST'])
def judge_grading_ui(submission_id):
    """Render judge grading UI with mock data and safe error handling.
    This route is intended for local testing/demo when DB/services are unavailable.
    """
    try:
        # Mock submission
        submission = {
            'id': submission_id,
            'title': f'BÃ i máº«u #{submission_id}: BÃ¬nh minh trÃªn phá»‘ cá»•',
            'author': 'Nguyá»…n VÄƒn A',
            'image_url': 'https://images.unsplash.com/photo-1501785888041-af3ef285b470',
            'camera': 'Nikon F3',
            'film_stock': 'Kodak Portra 400',
            'prev_id': submission_id - 1 if submission_id > 1 else None,
            'next_id': submission_id + 1,
        }

        # Mock criteria
        criteria_list = [
            {'id': 1, 'name': 'Composition', 'max': 40},
            {'id': 2, 'name': 'Exposure', 'max': 30},
            {'id': 3, 'name': 'Creativity', 'max': 30},
        ]

        # Mock existing scores and comment (could be None)
        existing_scores = {str(c['id']): None for c in criteria_list}
        existing_comment = ''

        if request.method == 'POST':
            form = request.form.to_dict(flat=True)
            existing_comment = form.get('comment', '')
            submitted_scores = {}
            for crit in criteria_list:
                key = str(crit['id'])
                val = form.get(key)
                try:
                    submitted_scores[key] = int(val) if val is not None and val != '' else None
                except ValueError:
                    submitted_scores[key] = None

            # In demo mode, we don't persist; just flash and redirect to GET
            flash('Äiá»ƒm vÃ  nháº­n xÃ©t Ä‘Ã£ Ä‘Æ°á»£c nháº­n (demo).')
            return redirect(url_for('judge_ui.judge_grading_ui', submission_id=submission_id))

        return render_template('judge_grading.html', submission=submission, criteria_list=criteria_list, existing_scores=existing_scores, existing_comment=existing_comment)

    except Exception as e:
        # Safe fallback: render template with minimal data and show error message
        fallback_submission = {
            'id': submission_id,
            'title': 'KhÃ´ng thá»ƒ táº£i bÃ i dá»± thi',
            'author': 'N/A',
            'image_url': None,
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
        
