import os, sqlite3
from flask import Flask, request, redirect, session, send_from_directory, render_template_string, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'CEACGE-2026')
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, "fotos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None and 'postgres' in DATABASE_URL

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
    conn=get_conn(); cur=conn.cursor()
    if USE_POSTGRES:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, fecha_nacimiento TEXT, centro TEXT, codigo_centro TEXT, nivel TEXT, foto TEXT, fecha_registro TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, fecha_nacimiento TEXT, centro TEXT, codigo_centro TEXT, nivel TEXT, foto TEXT, fecha_registro TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT)")
    cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),('admin',))
    if not cur.fetchone():
        cur.execute(adapt("INSERT INTO usuarios (usuario,password) VALUES (?,?)"),('admin',generate_password_hash('ceacge2025')))
    conn.commit(); conn.close()

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'usuario' not in session: return redirect(url_for('login'))
        return f(*a,**kw)
    return dec

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['usuario']; p=request.form['password']
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,))
        user=cur.fetchone(); conn.close()
        if user and check_password_hash(user['password'], p):
            session['usuario']=u; return redirect('/')
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5"><div style="background:white;padding:30px;border-radius:10px"><h2>CEACGE FINAL</h2><form method=post><input name=usuario placeholder=admin value=admin style="width:100%;padding:10px"><input name=password type=password placeholder=ceacge2025 style="width:100%;padding:10px"><button style="width:100%;padding:10px;background:#0d6efd;color:white;border:0">ENTRAR</button></form></div></body>'

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall(); conn.close()
    return render_template_string("""
    <style>body{font-family:Arial;margin:20px} .ok{background:#d1e7dd;padding:12px;border-radius:8px} .btn{background:#0d6efd;color:white;padding:14px 24px;text-decoration:none;border-radius:8px;display:inline-block;margin:10px 5px;font-weight:bold;font-size:18px} table{width:100%;border-collapse:collapse;margin-top:15px} th,td{border:1px solid #ddd;padding:8px} th{background:#0d6efd;color:white}</style>
    <h2>CEACGE - Alumnos ({{n}})</h2>
    <div class=ok>✓ Sistema funcionando en internet!<br>Link: ceacge-final.onrender.com<br>Base de datos: Postgres + SQLite compatible</div>
    <a class=btn href='/nuevo'>+ AGREGAR NUEVO ALUMNO</a> <a href='/logout' style='padding:10px'>Salir</a>
    <table><tr><th>Nombre</th><th>Centro</th><th>Accion</th></tr>
    {% for a in alumnos %}<tr><td>{{a['nombre']}} {{a['apellidos']}}</td><td>{{a['centro']}}</td><td><a href='/alumno/{{a['id']}}'>Ver Carnet (Foto Izq QR Der)</a></td></tr>{% endfor %}</table>
    {% if n==0 %}<p>No hay alumnos aun. La base de datos esta vacia pero funcionando. Dale al boton azul arriba.</p>{% endif %}
    """, alumnos=alumnos, n=len(alumnos))

@app.route('/alumno/<int:id>')
@login_required
def ver_alumno(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone(); conn.close()
    return f"<div style='font-family:Arial;display:flex;gap:20px;padding:20px'><div><img src='/fotos/{a['foto']}' width=180 style='border-radius:10px'><div style='border:1px dashed;padding:20px;margin-top:10px;text-align:center'>QR<br>{a['id']}</div></div><div><h1 style='font-size:32px'>{a['nombre']} {a['apellidos']}</h1><p>Centro: {a['centro']} ({a['codigo_centro']})<br>Nivel: {a['nivel']}</p><a href='/'>Volver</a></div></div>"

@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; centro=request.form['centro']; codigo=request.form['codigo_centro']; nivel=request.form['nivel']; fn=request.form['fecha_nacimiento']
        foto_file=request.files.get('foto'); foto_name=''
        if foto_file and foto_file.filename:
            foto_name=secure_filename(f"{nombre}_{datetime.datetime.now().strftime('%H%M%S')}.jpg")
            foto_file.save(os.path.join(UPLOAD_FOLDER, foto_name))
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,fecha_nacimiento,centro,codigo_centro,nivel,foto,fecha_registro) VALUES (?,?,?,?,?,?,?,?)"),(nombre,apellidos,fn,centro,codigo,nivel,foto_name,datetime.datetime.now().isoformat()))
        conn.commit(); conn.close(); return redirect('/')
    return '<h2>Nuevo Alumno</h2><form method=post enctype=multipart/form-data><input name=nombre placeholder=Nombre required><br><input name=apellidos placeholder=Apellidos required><br><input name=fecha_nacimiento type=date><br><input name=centro placeholder=Centro value="INES P. SIALO"><br><input name=codigo_centro placeholder=Codigo value="INES-PS"><br><select name=nivel><option>1 PRIMARIA</option><option>2 PRIMARIA</option><option>3 PRIMARIA</option><option>1 ESBA</option><option>2 BACHILLERATO</option></select><br><input type=file name=foto><br><button>GUARDAR</button></form><a href="/">Volver</a>'

@app.route('/borrar/<int:id>')
@login_required
def borrar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("DELETE FROM alumnos WHERE id=?"),(id,)); conn.commit(); conn.close(); return redirect('/')

try: init_db()
except: pass

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
