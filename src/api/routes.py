from src.api.controllers.todo_controller import bp as todo_bp
from src.api.controllers.auth_controller import auth_bp as auth_bp
from src.api.controllers.contest_controller import contest_bp as contest_bp

def register_routes(app):
    app.register_blueprint(todo_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(contest_bp)