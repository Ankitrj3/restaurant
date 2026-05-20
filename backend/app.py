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
from routes.platform_routes import platform_bp

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend'),
            static_url_path='')

CORS(app)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Register blueprints
app.register_blueprint(restaurant_bp)
app.register_blueprint(comparison_bp)
app.register_blueprint(platform_bp)


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
    from services.gemini_service import gemini_service
    warnings = Config.validate()
    return jsonify({
        "status": "ok",
        "gemini_available": gemini_service.is_available(),
        "warnings": warnings,
    })


if __name__ == '__main__':
    warnings = Config.validate()
    for w in warnings:
        print(f"[WARNING] {w}")
        
    # Start APScheduler background jobs
    from services.background_jobs import background_jobs
    background_jobs.start()
    
    print(f"\n[STARTING] Server on http://localhost:{Config.FLASK_PORT}")
    print(f"[CLIENT] {Config.CLIENT_RESTAURANT_NAME}")
    print(f"[ADDRESS] {Config.CLIENT_RESTAURANT_ADDRESS}\n")
    app.run(host='0.0.0.0', port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
