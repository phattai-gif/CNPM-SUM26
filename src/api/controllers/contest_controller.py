from flask import Blueprint, render_template, request, jsonify
from datetime import datetime

try:
    from src.infrastructure.repositories.contest_repository import ContestRepository
    from src.services.contest_service import ContestService
    from src.api.schemas.contest import (
        ContestCreateRequestSchema,
        ContestUpdateRequestSchema,
        ContestRulesUpdateRequestSchema,
        ContestConfigurationRequestSchema,
        ContestResponseSchema,
        RoundSchema,
        CriteriaSchema
    )
    from src.api.role_required import role_required
except ImportError:
    from infrastructure.repositories.contest_repository import ContestRepository
    from services.contest_service import ContestService
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

contest_service = ContestService(ContestRepository())

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
@role_required('organizer', 'admin')
def organizer_dashboard():
    """Render dashboard for organizers showing contests they manage."""
    user_id = request.user.get('user_id')
    contests = contest_service.list_organizer_contests(user_id)
    contests_data = [c.to_dict() for c in contests]
    return render_template('organizer_dashboard.html', contests=contests_data)


@contest_bp.route('/create-contest', methods=['GET'])
@role_required('organizer', 'admin')
def create_contest_page():
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
