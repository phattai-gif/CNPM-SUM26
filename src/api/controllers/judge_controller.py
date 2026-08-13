from flask import Blueprint, request, jsonify

try:
    from src.infrastructure.repositories.contest_repository import ContestRepository
    from src.infrastructure.repositories.judge_assignment_repository import JudgeAssignmentRepository
    from src.services.judge_assignment_service import JudgeAssignmentService
    from src.services.score_service import ScoreService
    from src.api.schemas.judge import AssignJudgeRequestSchema, JudgeAssignmentResponseSchema
    from src.api.role_required import role_required, token_required
except ImportError:
    from infrastructure.repositories.contest_repository import ContestRepository
    from infrastructure.repositories.judge_assignment_repository import JudgeAssignmentRepository
    from services.judge_assignment_service import JudgeAssignmentService
    from services.score_service import ScoreService
    from api.schemas.judge import AssignJudgeRequestSchema, JudgeAssignmentResponseSchema
    from api.role_required import role_required, token_required


judge_bp = Blueprint('judge', __name__)

judge_service = JudgeAssignmentService(
    judge_repo=JudgeAssignmentRepository(),
    contest_repo=ContestRepository()
)
score_service = ScoreService()

assign_judge_schema = AssignJudgeRequestSchema()
assignment_response_schema = JudgeAssignmentResponseSchema()


# -------------------------------------------------------------------------
# Organizer API: Candidate Judges List
# -------------------------------------------------------------------------
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
        return jsonify({'message': 'Lỗi khi lấy danh sách giám khảo', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Organizer API: Assign Judge to Round
# -------------------------------------------------------------------------
@judge_bp.route('/organizer/contests/<int:contest_id>/rounds/<int:round_id>/judges', methods=['POST'])
@role_required('organizer', 'admin')
def assign_judge_to_round(contest_id, round_id):
    """API Phân công giám khảo vào vòng thi (hoặc bài thi cụ thể trong vòng)."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    errors = assign_judge_schema.validate(data)
    if errors:
        return jsonify({'message': 'Dữ liệu phân công không hợp lệ', 'errors': errors}), 400

    judge_id = data.get('judge_id')
    judge_ids = data.get('judge_ids')
    submission_id = data.get('submission_id')

    try:
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
                'message': f'Đã phân công {len(assignments)} giám khảo vào vòng thi thành công',
                'assignments': [a.to_dict() for a in assignments]
            }), 201
        else:
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
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi phân công giám khảo', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Organizer API: List Assigned Judges for a Round
# -------------------------------------------------------------------------
@judge_bp.route('/organizer/contests/<int:contest_id>/rounds/<int:round_id>/judges', methods=['GET'])
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
            'message': 'Lấy danh sách giám khảo được phân công thành công',
            'assignments': [a.to_dict() for a in assignments]
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi lấy danh sách giám khảo', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Organizer API: Remove Judge Assignment from Round
# -------------------------------------------------------------------------
@judge_bp.route('/organizer/contests/<int:contest_id>/rounds/<int:round_id>/judges/<int:judge_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def remove_judge_from_round(contest_id, round_id, judge_id):
    """API Hủy phân công giám khảo khỏi vòng thi."""
    user_id = request.user.get('user_id')
    user_role = request.user.get('role')
    submission_id = request.args.get('submission_id', type=int)

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
            return jsonify({'message': 'Hủy phân công giám khảo thành công'}), 200
        else:
            return jsonify({'message': 'Không tìm thấy phân công giám khảo để hủy'}), 404
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except PermissionError as pe:
        return jsonify({'message': str(pe)}), 403
    except Exception as e:
        return jsonify({'message': 'Lỗi khi hủy phân công giám khảo', 'error': str(e)}), 500


# -------------------------------------------------------------------------
# Judge API: List My Assignments
# -------------------------------------------------------------------------
@judge_bp.route('/judge/assignments', methods=['GET'])
@role_required('judge', 'admin')
def get_my_assignments():
    """API Dành cho Giám khảo xem danh sách các vòng thi/bài thi mình được phân công."""
    user_id = request.user.get('user_id')

    try:
        assignments = judge_service.get_judge_assignments(judge_id=user_id)
        return jsonify({
            'message': 'Lấy danh sách nhiệm vụ chấm thi thành công',
            'assignments': [a.to_dict() for a in assignments]
        }), 200
    except Exception as e:
        return jsonify({'message': 'Lỗi khi lấy danh sách nhiệm vụ chấm thi', 'error': str(e)}), 500


@judge_bp.route('/rounds/<int:round_id>/finalize', methods=['POST'])
@role_required('organizer', 'admin')
def finalize_round_root(round_id):
    """API Chốt điểm vòng thi (Root route /rounds/<round_id>/finalize)."""
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

