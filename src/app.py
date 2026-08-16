from pathlib import Path

from flask import Flask, jsonify, redirect, url_for, render_template
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

    # Default home route
    @app.route('/')
    def home():
        return jsonify({
            'message': 'AI-powered Film Photography Contest Management API',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'docs': '/docs',
                'swagger': '/swagger.json',
                'auth': '/auth',
                'contests': '/contest',
                'submissions': '/submission',
                'ai_detection': '/ai-detection',
                'judge': '/judge'
            }
        })

    # Ensure judge UI blueprint is registered so /judge/<id> is available
    try:
        try:
            from api.controllers.judge_controller import judge_ui_bp as _judge_ui_bp
        except Exception:
            from api.controllers.judge_controller import judge_ui_bp as _judge_ui_bp

        if _judge_ui_bp.name not in app.blueprints:
            app.register_blueprint(_judge_ui_bp)
    except Exception:
        pass

    # Ensure contest public blueprint is registered so /contest/results and /contest/leaderboard are available
    try:
        try:
            from api.controllers.contest_controller import public_bp as _public_bp
        except Exception:
            from api.controllers.contest_controller import public_bp as _public_bp

        if _public_bp.name not in app.blueprints:
            app.register_blueprint(_public_bp)
    except Exception:
        pass

    # Short redirects for convenience
    @app.route('/leaderboard')
    def leaderboard_short():
        return redirect(url_for('contest_public.public_leaderboard'))

    @app.route('/results')
    def results_short():
        return redirect(url_for('contest_public.public_results'))

    # Direct leaderboard route with mock data to guarantee registration
    @app.route('/leaderboard-demo')
    def leaderboard_demo():
        # Mock winners
        winners = [
            {'rank': 1, 'author': 'Nguyễn Thị C', 'title': 'Hoàng hôn trên sông', 'score': 97, 'image_url': 'https://images.unsplash.com/photo-1501785888041-af3ef285b470', 'camera': 'Leica M6', 'film_stock': 'Kodak Portra 400'},
            {'rank': 2, 'author': 'Trần Văn D', 'title': 'Bến cảng sớm mai', 'score': 92, 'image_url': 'https://images.unsplash.com/photo-1470770903676-69b98201ea1c', 'camera': 'Nikon F3', 'film_stock': 'Ilford HP5'},
            {'rank': 3, 'author': 'Lê Văn E', 'title': 'Mưa rơi phố nhỏ', 'score': 89, 'image_url': 'https://images.unsplash.com/photo-1506744038136-46273834b3fb', 'camera': 'Canon AE-1', 'film_stock': 'Fuji Pro 400H'},
        ]

        # Mock leaderboard rows
        leaderboard = [
            {'rank': 1, 'author': 'Nguyễn Thị C', 'title': 'Hoàng hôn trên sông', 'score': 97},
            {'rank': 2, 'author': 'Trần Văn D', 'title': 'Bến cảng sớm mai', 'score': 92},
            {'rank': 3, 'author': 'Lê Văn E', 'title': 'Mưa rơi phố nhỏ', 'score': 89},
            {'rank': 4, 'author': 'Nguyễn Văn A', 'title': 'Bình minh trên phố cổ', 'score': 85},
            {'rank': 5, 'author': 'Phạm Thị B', 'title': 'Ánh đèn đêm', 'score': 82},
        ]

        return render_template('leaderboard.html', winners=winners, leaderboard=leaderboard)
    # Ensure judge blueprint is registered (safe-guard if routes.py didn't register it)
    try:
        try:
            from api.controllers.judge_controller import judge_bp as _judge_bp
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
            from api.controllers.judge_controller import judge_ui_bp as _judge_ui_bp
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
