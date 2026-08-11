try:
    from src.api.controllers.todo_controller import bp as todo_bp
    from src.api.controllers.auth_controller import auth_bp as auth_bp
    from src.api.controllers.ai_detection_controller import bp as ai_detection_bp
    from src.api.controllers.duplicate_detection_controller import bp as duplicate_detection_bp
except ImportError:
    from api.controllers.todo_controller import bp as todo_bp
    from api.controllers.auth_controller import auth_bp as auth_bp
    from api.controllers.ai_detection_controller import bp as ai_detection_bp
    from api.controllers.duplicate_detection_controller import bp as duplicate_detection_bp


def register_routes(app):
    app.register_blueprint(todo_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_detection_bp)
    app.register_blueprint(duplicate_detection_bp)