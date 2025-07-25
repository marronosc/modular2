from flask import Flask, render_template, request, session, redirect, url_for, flash
from context_processors import inject_tools
import os

# Agrega ESTAS LÍNEAS de debug después del import:
print("=== DEBUG ===")
tools_data = inject_tools()
print("Active tools:", list(tools_data['active_tools'].keys()))
print("Coming soon tools:", list(tools_data['coming_soon_tools'].keys()))
print("=== END DEBUG ===")

# Importar los blueprints
from routes.extractor import extractor_bp
from routes.seo import seo_bp
from routes.keyword_position import keyword_position_bp
from routes.thumbnail_comparison import thumbnail_comparison_bp
from routes.video_activity import video_activity_bp
from routes.keyword_research import keyword_research_bp  # Nuevo
from routes.recent_videos import recent_videos_bp
from routes.top_videos import top_videos_bp
from routes.test_top_videos import test_top_videos_bp

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tu-clave-secreta-muy-segura-aqui')
app.context_processor(inject_tools)

# Credenciales de login (en producción esto debería estar en una base de datos)
VALID_USERS = {
    'admin': 'admin123',
    'tubetools': 'youtube2024'
}

# Decorador para requerir login
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Middleware para proteger todas las rutas excepto login
@app.before_request
def require_login():
    # Rutas que no requieren login
    allowed_routes = ['login', 'static']
    
    if request.endpoint and request.endpoint not in allowed_routes:
        if 'logged_in' not in session:
            return redirect(url_for('login'))

# Registrar los blueprints
app.register_blueprint(extractor_bp)
app.register_blueprint(seo_bp)
app.register_blueprint(keyword_position_bp)
app.register_blueprint(thumbnail_comparison_bp)
app.register_blueprint(video_activity_bp)
app.register_blueprint(keyword_research_bp)  # Nuevo
app.register_blueprint(recent_videos_bp)
app.register_blueprint(top_videos_bp)
app.register_blueprint(test_top_videos_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in VALID_USERS and VALID_USERS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Usuario o contraseña incorrectos')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)