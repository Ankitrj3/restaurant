"""
Main Flask application — Restaurant Competitor Intelligence Platform.
Registers all route blueprints and serves the frontend.
"""

import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from config import Config
from routes.restaurant_routes import restaurant_bp
from routes.comparison_routes import comparison_bp

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend'),
            static_url_path='')

CORS(app)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Register blueprints
app.register_blueprint(restaurant_bp)
app.register_blueprint(comparison_bp)


# ── Frontend serving ───────────────────────────────────
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/css/<path:path>')
def serve_css(path):
    return send_from_directory(os.path.join(app.static_folder, 'css'), path)


@app.route('/js/<path:path>')
def serve_js(path):
    return send_from_directory(os.path.join(app.static_folder, 'js'), path)


# ── Health check ───────────────────────────────────────
@app.route('/api/health')
def health():
    from services.claude_service import claude_service
    warnings = Config.validate()
    return jsonify({
        "status": "ok",
        "claude_available": claude_service.is_available(),
        "warnings": warnings,
    })


if __name__ == '__main__':
    warnings = Config.validate()
    for w in warnings:
        print(f"⚠️  {w}")
    print(f"\n🚀 Starting server on http://localhost:{Config.FLASK_PORT}")
    print(f"📍 Client: {Config.CLIENT_RESTAURANT_NAME}")
    print(f"📌 Address: {Config.CLIENT_RESTAURANT_ADDRESS}\n")
    app.run(host='0.0.0.0', port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
