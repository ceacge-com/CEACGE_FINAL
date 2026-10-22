import os
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'CEACGE-FIX-FINAL-2026'
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, "fotos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL and 'postgres' in DATABASE_URL

def get_conn():
    if USE_POSTGRES:
        import psycopg2, psycopg2.extras
        url = DATABASE_URL.replace('postgres://','postgresql://',1) if DATABASE_URL.startswith('postgres://') else DATABASE_URL
        return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        import sqlite3
        conn = sqlite3.connect(os.path.join(basedir, "ceacge.db"))
        conn.row_factory = sqlite3.Row
        return conn

def adapt(q):
    return q.replace('?','%s') if USE_POSTGRES else q

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    try:
        # AUTO-REPARACIÓN: si usuarios está rota, la borra
        try:
            cur.execute("SELECT usuario FROM usuarios LIMIT 1")
        except:
            try:
                conn.rollback()
            except:
                pass
            cur.execute("DROP TABLE IF EXISTS usuarios")
            conn.commit()
            print("Tabla usuarios rota borrada, recreando...")

        if USE_POSTGRES:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, centro TEXT, foto TEXT, anio TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, centro TEXT, foto TEXT, anio TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT, localidad TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, centro TEXT, foto TEXT, anio TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, centro TEXT, foto TEXT, anio TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT, localidad TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")

        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
        if not cur.fetchone():
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
            print("Admin creado: admin / ceacge2025")
        conn.commit()
    except Exception as e:
        print(f"init_db error: {e}")
        try:
            conn.rollback()
        except:
            pass
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

init_db()

LOGIN_HTML = """
<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CEACGE</title>
<style>
body{font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5;margin:0}
.box{background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.1);width:320px}
input{width:100%;padding:10px;margin:8px 0;border:1px solid #ddd;border-radius:5px;box-sizing:border-box}
button{width:100%;padding:10px;background:#1a73e8;color:white;border:none;border-radius:5px;cursor:pointer;font-weight:bold}
h2{text-align:center;margin-top:0}
</style></head><body><div class='box'><h2>CEACGE FINAL</h2>
{% if error %}<p style='color:red;text-align:center'>{{error}}</p>{% endif %}
<form method='post'><input name='usuario' placeholder='Usuario' required><input name='password' type='password' placeholder='Contraseña' required><button>Entrar</button></form>
<p style='font-size:12px;color:#666;text-align:center;margin-bottom:0'>admin / ceacge2025</p></div></body></html>
"""

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        usuario=request.form.get('usuario','').strip()
        password=request.form.get('password','')
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), (usuario,))
            u=cur.fetchone()
            if not u:
                error="Usuario o contraseña incorrectos"
            else:
                pw = u['password'] if isinstance(u, dict) else u[2]
                rol = u['rol'] if isinstance(u, dict) else u[3]
                if check_password_hash(pw, password):
                    session['usuario']=usuario
                    session['rol']=rol
                    return redirect('/dashboard')
                else:
                    error="Usuario o contraseña incorrectos"
        except Exception as e:
            error=f"Error DB: {e}"
        finally:
            try: cur.close()
            except: pass
            try: conn.close()
            except: pass
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect('/login')
    return f"""
    <div style='font-family:Arial;padding:20px'>
    <h1 style='color:green'>✅ Login Arreglado - Bienvenido {session['usuario']}</h1>
    <p>La tabla usuarios rota ya fue borrada y recreada.</p>
    <p>Ahora ya podemos restaurar tu V18 completo con fotos, alumnos, etc.</p>
    <hr>
    <a href='/login'>Cerrar sesión</a>
    </div>
    """

@app.route('/fotos/<path:filename>')
def fotos(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
