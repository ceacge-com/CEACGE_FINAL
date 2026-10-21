import os, sqlite3
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'V18-FIXED-AUTO-2026'
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
        conn = sqlite3.connect(os.path.join(basedir, "ceacge.db"))
        conn.row_factory = sqlite3.Row
        return conn

def adapt(q): return q.replace('?','%s') if USE_POSTGRES else q

def init_db():
    conn = get_conn(); cur = conn.cursor()
    try:
        # Primero intentamos ver si usuarios está rota
        try:
            cur.execute("SELECT * FROM usuarios LIMIT 1")
        except:
            print("Tabla usuarios rota, borrando y recreando...")
            try:
                conn.rollback()
                cur.execute("DROP TABLE IF EXISTS usuarios")
                conn.commit()
            except:
                try: conn.rollback()
                except: pass

        if USE_POSTGRES:
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY)")
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
            for tbl, cols in [
                ("alumnos", ["nombre TEXT","apellidos TEXT","natural_de TEXT","distrito TEXT","provincia TEXT","centro TEXT","foto TEXT","anio TEXT","contacto TEXT","email TEXT","centro_nombre TEXT","centro_codigo TEXT","centro_localidad TEXT","centro_contacto TEXT"]),
                ("alumnos_primaria", ["nombre TEXT","apellidos TEXT","hijo_de TEXT","y_de TEXT","fecha_nacimiento TEXT","centro TEXT","localidad TEXT","codigo TEXT","foto TEXT","anio TEXT","centro_codigo TEXT"]),
                ("centros", ["nombre TEXT","codigo TEXT","localidad TEXT","contacto TEXT","email TEXT","codigo_acceso TEXT"]),
                ("usuarios", ["usuario TEXT","password TEXT","rol TEXT","centro_codigo TEXT"])
            ]:
                for col in cols:
                    try: cur.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col}")
                    except: pass
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")

        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
        if not cur.fetchone():
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
            print("Admin creado")
        conn.commit()
    except Exception as e:
        print(f"init_db error final: {e}")
        try: conn.rollback()
        except: pass
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

init_db()

LOGIN_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>CEACGE</title>
<style>body{font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5}
.box{background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.1);width:320px}
input{width:100%;padding:10px;margin:8px 0;border:1px solid #ddd;border-radius:5px;box-sizing:border-box}
button{width:100%;padding:10px;background:#1a73e8;color:white;border:none;border-radius:5px;cursor:pointer}
h2{text-align:center}</style></head><body><div class="box"><h2>CEACGE FINAL</h2>
{% if error %}<p style="color:red">{{error}}</p>{% endif %}
<form method="post"><input name="usuario" placeholder="Usuario" required><input name="password" type="password" placeholder="Contraseña" required><button>Entrar</button></form>
<p style="font-size:12px;color:#666;text-align:center">admin / ceacge2025</p></div></body></html>"""

@app.route('/')
def index(): return redirect('/login')

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
            pw = u['password'] if isinstance(u, dict) else (u[2] if u else None)
            rol = u['rol'] if isinstance(u, dict) else (u[3] if u else None)
            if u and check_password_hash(pw, password):
                session['usuario']=usuario; session['rol']=rol
                return redirect('/dashboard')
            else: error="Usuario o contraseña incorrectos"
        except Exception as e: error=f"Error DB: {e}"
        finally:
            try: cur.close()
            except: pass
            try: conn.close()
            except: pass
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect('/login')
    return f"<h1>Bienvenido {session['usuario']}</h1><p>Login ya funciona. Ahora podemos restaurar tu V18 completo.</p><a href='/login'>Salir</a>"

@app.route('/fotos/<path:filename>')
def fotos(filename): return send_from_directory(UPLOAD_FOLDER, filename)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
