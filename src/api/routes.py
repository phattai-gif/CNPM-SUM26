from api.controllers.auth_controller import auth_bp as auth_bp
from api.controllers.ai_detection_controller import bp as ai_detection_bp
from api.controllers.duplicate_detection_controller import bp as duplicate_detection_bp
from api.controllers.submission_controller import submission_bp
from api.controllers.submission_review_controller import bp as submission_review_bp
from api.controllers.contest_controller import contest_bp, public_bp as contest_public_bp
from api.controllers.judge_controller import judge_bp
from api.controllers.notification_controller import notification_bp
from api.controllers.contest_settings_controller import contest_settings_bp


def register_routes(app):
    # Core app blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_detection_bp)
    app.register_blueprint(duplicate_detection_bp)
    app.register_blueprint(submission_bp)
    app.register_blueprint(submission_review_bp)
    app.register_blueprint(contest_bp)
    app.register_blueprint(contest_public_bp)
    app.register_blueprint(judge_bp)
    
    # Business domain blueprints
    app.register_blueprint(notification_bp)
    app.register_blueprint(contest_settings_bp)
    
    # Public UI routes and SPA fallback
    from flask import redirect, url_for, render_template, jsonify, request

    # root -> public results / contests landing
    try:
        app.add_url_rule('/', 'root', lambda: redirect('/contests'))
    except Exception:
        app.add_url_rule('/', 'root_fallback', lambda: redirect('/contests'))

    # Common public routes
    try:
        app.add_url_rule('/contests', 'contests', lambda: render_template('contests.html'))
    except Exception:
        pass
    try:
        app.add_url_rule('/organizer/contest-config', 'organizer_contest_config_page', lambda: render_template('create_contest.html'))
    except Exception:
        pass
    try:
        app.add_url_rule('/login', 'login', lambda: render_template('login.html'))
    except Exception:
        pass
    try:
        app.add_url_rule('/register', 'register', lambda: render_template('register.html'))
    except Exception:
        pass

    # redirect legacy /explore to /contests
    try:
        app.add_url_rule('/explore', 'explore', lambda: redirect('/contests'))
    except Exception:
        pass

    # Serve contest public detail page
    try:
        app.add_url_rule('/contest/<int:contest_id>', 'public_contest_page', lambda contest_id: render_template('contest_public_detail.html'))
    except Exception:
        pass

    # Public API: list published/active contests and contest detail
    try:
        from infrastructure.models.app import ContestModel
        def api_list_contests():
            try:
                session = None
                try:
                    session = __import__('api.controllers.contest_controller', fromlist=['']).contest_service.repository.session
                except Exception:
                    from infrastructure.databases.factory_database import FactoryDatabase as db_factory
                    session = db_factory.get_database('POSTGREE').session
                qs = session.query(ContestModel).filter(ContestModel.status.in_(['published','active'])).order_by(ContestModel.created_at.desc()).all()
                out = []
                for m in qs:
                    out.append({
                        'id': m.id,
                        'title': m.title,
                        'description': m.description,
                        'status': m.status,
                        'start_date': str(m.start_date) if m.start_date else None,
                        'end_date': str(m.end_date) if m.end_date else None,
                        'banner_url': m.banner_url
                    })
                return jsonify({'contests': out}), 200
            except Exception as e:
                return jsonify({'message': 'Error', 'error': str(e), 'contests': []}), 500
        app.add_url_rule('/api/contests', 'api_contests', api_list_contests, methods=['GET'])

        def api_get_contest(contest_id):
            try:
                session = None
                try:
                    session = __import__('api.controllers.contest_controller', fromlist=['']).contest_service.repository.session
                except Exception:
                    from infrastructure.databases.factory_database import FactoryDatabase as db_factory
                    session = db_factory.get_database('POSTGREE').session
                m = session.query(ContestModel).filter_by(id=contest_id).first()
                if not m:
                    return jsonify({'message': 'Not found'}), 404
                
                rounds = []
                try:
                    from infrastructure.models.app import RoundModel
                    round_qs = session.query(RoundModel).filter_by(contest_id=m.id).order_by(RoundModel.round_number.asc()).all()
                    for r in round_qs:
                        rounds.append({
                            'id': r.id,
                            'title': r.title,
                            'round_number': r.round_number,
                            'status': r.status,
                        })
                except Exception:
                    rounds = []

                return jsonify({'contest': {
                    'id': m.id,
                    'title': m.title,
                    'description': m.description,
                    'status': m.status,
                    'start_date': str(m.start_date) if m.start_date else None,
                    'end_date': str(m.end_date) if m.end_date else None,
                    'banner_url': m.banner_url,
                    'rounds': rounds
                }}), 200
            except Exception as e:
                return jsonify({'message': 'Error', 'error': str(e)}), 500
        app.add_url_rule('/api/contests/<int:contest_id>', 'api_get_contest', api_get_contest, methods=['GET'])

        # API TRẢ VỀ CẢ 2 DẠNG (ARRAY & OBJECT) + ĐẦY ĐỦ THUỘC TÍNH PHÙ HỢP CẢ FRONTEND
        def api_get_contest_submissions_organizer(contest_id):
            try:
                session = None
                try:
                    session = __import__('api.controllers.contest_controller', fromlist=['']).contest_service.repository.session
                except Exception:
                    from infrastructure.databases.factory_database import FactoryDatabase as db_factory
                    session = db_factory.get_database('POSTGREE').session

                from infrastructure.models.app import SubmissionModel, SubmissionFileModel, RoundModel

                # Submission không có contest_id trực tiếp, cần join qua rounds.
                all_rows = (
                    session
                    .query(SubmissionModel, RoundModel, SubmissionFileModel)
                    .outerjoin(RoundModel, SubmissionModel.round_id == RoundModel.id)
                    .outerjoin(SubmissionFileModel, SubmissionFileModel.submission_id == SubmissionModel.id)
                    .order_by(SubmissionModel.submitted_at.desc(), SubmissionModel.id.desc())
                    .all()
                )

                contest_rows = [
                    row for row in all_rows
                    if row[1] is not None and row[1].contest_id == contest_id
                ]

                print(f"[OrganizerSubmissions] requested_contest_id={contest_id} total_submissions_in_db={len(all_rows)} contest_submissions={len(contest_rows)}")

                # In toàn bộ submission để debug mismatch contest_id hoặc thiếu dữ liệu.
                for submission, round_model, submission_file in all_rows:
                    resolved_contest_id = round_model.contest_id if round_model else None
                    missing_fields = []
                    if not submission.title:
                        missing_fields.append('title')
                    if not submission.status:
                        missing_fields.append('status')
                    if submission_file is None or not submission_file.image_hd_url:
                        missing_fields.append('image_hd_url')

                    exclusion_reason = None
                    if round_model is None:
                        exclusion_reason = 'missing_round'
                    elif resolved_contest_id != contest_id:
                        exclusion_reason = 'contest_id_mismatch'

                    print(
                        "[OrganizerSubmissions][ROW] "
                        f"submission_id={submission.id} "
                        f"round_id={submission.round_id} "
                        f"contest_id={resolved_contest_id} "
                        f"status={submission.status} "
                        f"has_file={'yes' if submission_file else 'no'} "
                        f"missing_fields={missing_fields if missing_fields else 'none'} "
                        f"excluded_from_requested_contest={exclusion_reason if exclusion_reason else 'no'}"
                    )

                def serialize_rows(rows):
                    out = []
                    for submission, round_model, submission_file in rows:
                        resolved_contest_id = round_model.contest_id if round_model else None
                        item_id = submission.id
                        item_title = submission.title or f'Bài dự thi #{item_id}'
                        item_url = submission_file.image_hd_url if submission_file else ''
                        item_status = submission.status or 'submitted'

                        out.append({
                            'id': item_id,
                            'submission_id': item_id,
                            'round_id': submission.round_id,
                            'contest_id': resolved_contest_id,
                            'title': item_title,
                            'submission_name': item_title,
                            'name': item_title,
                            'submission_url': item_url,
                            'image_hd_url': item_url,
                            'link': item_url,
                            'file_url': item_url,
                            'url': item_url,
                            'status': item_status
                        })
                    return out

                all_out = serialize_rows(all_rows)
                contest_out = serialize_rows(contest_rows)

                # Trả toàn bộ submissions cho giao diện để tránh bỏ sót bài nộp mới.
                out = all_out

                for submission, round_model, submission_file in all_rows:
                    item_id = submission.id
                    if round_model is None:
                        print(f"[OrganizerSubmissions][WARN] submission_id={item_id} has no round relation.")
                    elif round_model.contest_id != contest_id:
                        print(f"[OrganizerSubmissions][INFO] submission_id={item_id} belongs_to_contest_id={round_model.contest_id}, not requested_contest_id={contest_id}.")
                    if submission_file is None:
                        print(f"[OrganizerSubmissions][INFO] submission_id={item_id} has no submission_file row.")
                    elif not submission_file.image_hd_url:
                        print(f"[OrganizerSubmissions][INFO] submission_id={item_id} has empty image_hd_url.")

                return jsonify({
                    'contest_id': contest_id,
                    'contest_submissions': contest_out,
                    'submissions': out,
                    'data': out,
                    'items': out,
                    'counts': {
                        'total_submissions': len(all_out),
                        'requested_contest_submissions': len(contest_out)
                    }
                }), 200
            except Exception as e:
                print("Lỗi truy vấn Submissions:", e)
                return jsonify({'message': 'Error', 'error': str(e), 'submissions': []}), 500

        app.add_url_rule('/organizer/contests/<int:contest_id>/submissions', 'org_contest_submissions', api_get_contest_submissions_organizer, methods=['GET'])
        app.add_url_rule('/api/contests/<int:contest_id>/submissions', 'api_contest_submissions', api_get_contest_submissions_organizer, methods=['GET'])

    except Exception:
        pass

    # SPA fallback
    def spa_fallback(path):
        if path.startswith('static') or path.startswith('api') or '.' in path:
            from flask import abort
            return abort(404)
        return render_template('results.html')

    try:
        app.add_url_rule('/<path:path>', 'spa_fallback', spa_fallback)
    except Exception:
        pass