from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import re

try:
    from src.infrastructure.models.contest_model import ContestModel
    from src.infrastructure.databases.postgres import session
    from src.api.role_required import role_required
except ImportError:
    from infrastructure.models.contest_model import ContestModel
    from infrastructure.databases.postgres import session
    from api.role_required import role_required


contest_bp = Blueprint('contest', __name__, url_prefix='/organizer')


@contest_bp.route('/dashboard', methods=['GET'])
@role_required('organizer', 'admin')
def organizer_dashboard():
    """Render a simple dashboard for organizers showing contests they manage."""
    user_id = request.user.get('user_id')
    try:
        contests = session.query(ContestModel).filter(ContestModel.created_by == user_id).all()
    except Exception:
        # If DB isn't configured, return empty list gracefully
        contests = []

    contests_data = []
    for c in contests:
        contests_data.append({
            'id': c.id,
            'title': c.title,
            'slug': getattr(c, 'slug', None),
            'status': getattr(c, 'status', None),
            'start_date': c.start_date.isoformat() if getattr(c, 'start_date', None) else None,
            'end_date': c.end_date.isoformat() if getattr(c, 'end_date', None) else None,
            'created_at': c.created_at.isoformat() if getattr(c, 'created_at', None) else None,
        })

    return render_template('organizer_dashboard.html', contests=contests_data)



@contest_bp.route('/create-contest', methods=['GET'])
@role_required('organizer', 'admin')
def create_contest_page():
    return render_template('create_contest.html')


@contest_bp.route('/create-contest', methods=['POST'])
@role_required('organizer', 'admin')
def create_contest():
    data = request.form or {}
    title = data.get('title')
    description = data.get('description')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if not title:
        return jsonify({'message': 'Title is required'}), 400

    # simple slug generator
    base_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    slug = f"{base_slug}-{int(datetime.utcnow().timestamp())}"

    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
    except Exception:
        start_dt = None

    try:
        end_dt = datetime.fromisoformat(end_date) if end_date else None
    except Exception:
        end_dt = None

    user_id = request.user.get('user_id')

    # insert directly via SQLAlchemy session
    try:
        new = ContestModel(
            title=title,
            slug=slug,
            description=description,
            created_by=user_id,
            status='draft',
            start_date=start_dt,
            end_date=end_dt
        )
        session.add(new)
        session.commit()
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        return jsonify({'message': 'Failed to create contest', 'error': str(e)}), 500

    return jsonify({'message': 'Contest created', 'contest': {'id': new.id, 'title': new.title, 'slug': new.slug}}), 201
