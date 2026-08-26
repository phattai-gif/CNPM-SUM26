# Middleware functions for processing requests and responses

from flask import request, jsonify


UTF8_CHARSET = "charset=UTF-8"


def _should_set_utf8_charset(response):
    content_type = response.headers.get('Content-Type', '')
    if not content_type or 'charset=' in content_type.lower():
        return False

    mimetype = (response.mimetype or '').lower()
    return mimetype.startswith('text/') or mimetype in {
        'application/json',
        'application/javascript',
        'application/xml',
        'application/xhtml+xml',
    }


def log_request_info(app):
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())


def handle_options_request():
    return jsonify({'message': 'CORS preflight response'}), 200


def error_handling_middleware(error):
    response = jsonify({'error': str(error)})
    response.status_code = 500
    return response


def add_custom_headers(response):
    response.headers['X-Custom-Header'] = 'Value'
    if _should_set_utf8_charset(response):
        response.headers['Content-Type'] = f"{response.mimetype}; {UTF8_CHARSET}"
    return response


def middleware(app):
    @app.before_request
    def before_request():
        log_request_info(app)

    @app.after_request
    def after_request(response):
        return add_custom_headers(response)

    @app.errorhandler(Exception)
    def handle_exception(error):
        return error_handling_middleware(error)

    @app.route('/options', methods=['OPTIONS'])
    def options_route():
        return handle_options_request()


# Compatibility alias used by the application factory.
def setup_middleware(app):
    middleware(app)
