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
    # Core app blueprints (photo contest domain)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_detection_bp)
    app.register_blueprint(duplicate_detection_bp)
    app.register_blueprint(submission_bp)
    app.register_blueprint(submission_review_bp)
    app.register_blueprint(contest_bp)
    app.register_blueprint(contest_public_bp)
    app.register_blueprint(judge_bp)
    
    # Business domain blueprints (newly added)
    app.register_blueprint(notification_bp)
    app.register_blueprint(contest_settings_bp)
