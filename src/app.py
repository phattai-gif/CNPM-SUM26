from pathlib import Path

from flask import Flask, jsonify, redirect, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
from api.routes import register_routes
from api.swagger import spec
from api.middleware import middleware
from api.responses import success_response
from infrastructure.databases import init_db
from config import Config
from flasgger import Swagger
from config import SwaggerConfig
from flask_swagger_ui import get_swaggerui_blueprint


def create_app():
    frontend_dir = Path(__file__).resolve().parent.parent / 'frontend'
    app = Flask(
        __name__,
        template_folder=str(frontend_dir / 'templates'),
        static_folder=str(frontend_dir / 'static'),
        static_url_path='/static',
    )
    app.config.from_object(Config)
    Swagger(app)
    # Ensure templates in `src/templates` are also discoverable (fallback)
    try:
        src_templates = str(Path(__file__).resolve().parent / 'templates')
        # Use ChoiceLoader to combine existing loader with src/templates
        existing_loader = getattr(app, 'jinja_loader', None)
        loaders = []
        # Prepend src/templates so it takes precedence
        loaders.append(FileSystemLoader(src_templates))
        if existing_loader:
            loaders.append(existing_loader)
        app.jinja_loader = ChoiceLoader(loaders)
    except Exception:
        # non-fatal: if jinja loaders not available, continue
        pass
    
    # Đăng ký tất cả các route/blueprint
    register_routes(app)

    # Ensure judge blueprint is registered (safe-guard if routes.py didn't register it)
    try:
        try:
            from src.api.controllers.judge_controller import judge_bp as _judge_bp
        except Exception:
            from api.controllers.judge_controller import judge_bp as _judge_bp

        if _judge_bp.name not in app.blueprints:
            app.register_blueprint(_judge_bp)
    except Exception:
        # non-fatal: if import fails, continue; routes may already be registered
        pass

    # Ensure judge UI blueprint is registered so /judge/<id> is available
    try:
        try:
            from src.api.controllers.judge_controller import judge_ui_bp as _judge_ui_bp
        except Exception:
            from api.controllers.judge_controller import judge_ui_bp as _judge_ui_bp

        if _judge_ui_bp.name not in app.blueprints:
            app.register_blueprint(_judge_ui_bp)
    except Exception:
        pass
     # Thêm Swagger UI blueprint
    SWAGGER_URL = '/docs'
    API_URL = '/swagger.json'
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={'app_name': "Todo API"}
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    try:
        init_db(app)
    except Exception as e:
        print(f"Error initializing database: {e}")

    # Register middleware
    middleware(app)

    # Register routes
    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            # Thêm các endpoint khác nếu cần
            if rule.endpoint.startswith(('todo.', 'course.', 'user.', 'auth.', 'ai_detection.')):
                view_func = app.view_functions[rule.endpoint]
                print(f"Adding path: {rule.rule} -> {view_func}")
                spec.path(view=view_func)
            
    @app.route("/swagger.json")
    def swagger_json():
        return jsonify(spec.to_dict())


    # Short URL for judge grading UI -> redirect to public judge grading route
    @app.route('/judge/<int:submission_id>')
    def judge_short_link(submission_id):
        return redirect(url_for('contest_public.public_judge_grading', submission_id=submission_id))

    return app
# Run the application

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=9999, debug=True)
