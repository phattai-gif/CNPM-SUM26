from flask import Blueprint, request, jsonify

try:
    from src.infrastructure.repositories.contest_repository import ContestRepository
    from src.infrastructure.repositories.judge_assignment_repository import JudgeAssignmentRepository
    from src.services.judge_assignment_service import JudgeAssignmentService
    from src.api.schemas.judge import (
        AssignJudgeRequestSchema,
        JudgeAssignmentResponseSchema
    )
    from src.api.role_required import role_required
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

judge_service = JudgeAssignmentService(
    judge_repo=JudgeAssignmentRepository(),
    contest_repo=ContestRepository()
)

assign_judge_schema = AssignJudgeRequestSchema()
assignment_response_schema = JudgeAssignmentResponseSchema()


@judge_bp.route('/organizer/judges', methods=['GET'])
@role_required('organizer', 'admin')
def list_available_judges():
    """API Lấy danh sách giám khảo khả dụng để phân công."""
    try:
        judges = judge_service.get_available_judges()

        return jsonify({
            'message': 'Lấy danh sách giám khảo thành công',
            'judges': judges
        }), 200

    except Exception as e:
        return jsonify({
            'message': 'Lỗi khi lấy danh sách giám khảo',
            'error': str(e)
        }), 500


@judge_bp.route(
    '/organizer/contests/<int:contest_id>/rounds/<int:round_id>/judges',
    methods=['POST']
)
@role_required('organizer', 'admin')
def assign_judge_to_round(contest_id, round_id):
    """API Phân công giám khảo vào vòng thi hoặc bài thi cụ thể."""
    
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')

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
        # Phân công nhiều giám khảo
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
                    f'Đã phân công {len(assignments)} '
                    'giám khảo vào vòng thi thành công'
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
            'message': 'Phân công giám khảo thành công',
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
            'message': 'Lỗi khi phân công giám khảo',
            'error': str(e)
        }), 500


@judge_bp.route(
    '/organizer/contests/<int:contest_id>/rounds/<int:round_id>/judges',
    methods=['GET']
)
@role_required('organizer', 'admin')
def get_round_judges(contest_id, round_id):
    """API Lấy danh sách giám khảo đã được phân công trong vòng thi."""

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
                'Lấy danh sách giám khảo được '
                'phân công thành công'
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
            'message': 'Lỗi khi lấy danh sách giám khảo',
            'error': str(e)
        }), 500

@judge_bp.route(
    '/organizer/contests/<int:contest_id>/rounds/'
    '<int:round_id>/judges/<int:judge_id>',
    methods=['DELETE']
)
@role_required('organizer', 'admin')
def remove_judge_from_round(contest_id, round_id, judge_id):
    """API Hủy phân công giám khảo khỏi vòng thi."""

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
@role_required('judge', 'admin')
def get_my_assignments():
    """API Dành cho giám khảo xem các nhiệm vụ chấm thi."""

    user_id = request.user.get('user_id')

    try:
        assignments = judge_service.get_judge_assignments(
            judge_id=user_id
        )

        return jsonify({
            'message': (
                'Lấy danh sách nhiệm vụ chấm thi thành công'
            ),
            'assignments': [
                assignment.to_dict()
                for assignment in assignments
            ]
        }), 200

    except Exception as e:
        return jsonify({
            'message': 'Lỗi khi lấy danh sách nhiệm vụ chấm thi',
            'error': str(e)
        }), 500
        