import os, sqlite3, base64, urllib.parse
from flask import Flask, request, redirect, session, send_from_directory, render_template_string, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'CEACGE-FOTO-IZQ-QR-DER-NOMBRE-GRANDE')

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, "fotos")
DB_PATH = os.path.join(basedir, "ceacge.db")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL and 'postgres' in DATABASE_URL

def get_conn():
    if USE_POSTGRES:
        import psycopg2, psycopg2.extras
        url = DATABASE_URL
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def adapt(q):
    return q.replace('?', '%s') if USE_POSTGRES else q

def init_db():
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellido TEXT, nivel TEXT, fecha_nacimiento TEXT, foto TEXT, qr TEXT)')
    else:
        c.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, nivel TEXT, fecha_nacimiento TEXT, foto TEXT, qr TEXT)')
    c.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not c.fetchone():
        c.execute(adapt('INSERT INTO usuarios (username, password) VALUES (?, ?)'), ('admin', generate_password_hash('ceacge2025')))
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(adapt("SELECT * FROM usuarios WHERE username=?"), (username,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = username
            return redirect('/')
        else:
            return render_template_string(LOGIN_HTML, error="Usuario o contrasena incorrecta")
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
@login_required
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alumnos ORDER BY id DESC")
    alumnos = cur.fetchall()
    conn.close()
    return render_template_string(INDEX_HTML, alumnos=alumnos)

@app.route('/fotos/<filename>')
def fotos_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

LOGIN_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CEACGE Login</title><style>body{font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5}.card{background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);width:300px}input{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px}button{width:100%;padding:10px;background:#007bff;color:white;border:none;border-radius:5px;cursor:pointer}.error{color:red;font-size:14px}</style></head>
<body><div class="card"><h2>CEACGE FINAL</h2>{% if error %}<p class="error">{{error}}</p>{% endif %}<form method="post"><input name="username" placeholder="Usuario" value="admin" required><input name="password" type="password" placeholder="Contrasena" required><button>ENTRAR</button></form><p style="font-size:12px;margin-top:15px">admin / ceacge2025</p></div></body></html>
"""

INDEX_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>CEACGE</title><style>body{font-family:Arial;padding:20px;background:#f5f5f5}.header{display:flex;justify-content:space-between;align-items:center}.card{background:white;padding:15px;margin:10px 0;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}a{color:#007bff;text-decoration:none}</style></head>
<body><div class="header"><h2>CEACGE - Alumnos ({{alumnos|length}})</h2><a href="/logout">Salir</a></div><div class="card">✓ Sistema funcionando en internet!<br>Link: ceacge-final.onrender.com<br>Base de datos: Postgres + SQLite compatible</div>{% for a in alumnos %}<div class="card">{{a['nombre']}} {{a['apellido']}} - {{a['nivel']}}</div>{% endfor %}{% if not alumnos %}<div class="card">No hay alumnos aun. La base de datos esta vacia pero funcionando.</div>{% endif %}</body></html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
