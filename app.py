import os
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'CEACGE-V18-FINAL-2026'
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
def adapt(q): return q.replace('?','%s') if USE_POSTGRES else q
def init_db():
    conn = get_conn(); cur = conn.cursor()
    try:
        try: cur.execute("SELECT usuario FROM usuarios LIMIT 1")
        except:
            try: conn.rollback()
            except: pass
            cur.execute("DROP TABLE IF EXISTS usuarios"); conn.commit()
        if USE_POSTGRES:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT, codigo_acceso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, foto TEXT, anio TEXT, contacto TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, hijo_de TEXT, y_de TEXT, fecha_nacimiento TEXT, centro TEXT, localidad TEXT, codigo TEXT, foto TEXT, anio TEXT, centro_codigo TEXT)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT, codigo_acceso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, foto TEXT, anio TEXT, contacto TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, hijo_de TEXT, y_de TEXT, fecha_nacimiento TEXT, centro TEXT, localidad TEXT, codigo TEXT, foto TEXT, anio TEXT, centro_codigo TEXT)")
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
        if not cur.fetchone():
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
        conn.commit()
    except Exception as e:
        print(f"init_db: {e}")
        try: conn.rollback()
        except: pass
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
init_db()
BASE = """<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CEACGE</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body><nav class='navbar navbar-dark bg-primary'><div class='container'><a class='navbar-brand' href='/dashboard'>CEACGE FINAL V18</a><span class='text-white'>{{session.usuario}} | <a href='/logout' class='text-white'>Salir</a></span></div></nav><div class='container mt-4'>{{content|safe}}</div></body></html>"""
@app.route('/')
def index(): return redirect('/dashboard' if 'usuario' in session else '/login')
@app.route('/login', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        u=request.form.get('usuario','').strip(); p=request.form.get('password','')
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), (u,))
            row=cur.fetchone()
            if row:
                pw=row['password'] if isinstance(row,dict) else row[2]
                if check_password_hash(pw,p):
                    session['usuario']=u; session['rol']=row['rol'] if isinstance(row,dict) else row[3]; return redirect('/dashboard')
            error="Usuario o contraseña incorrectos"
        except Exception as e: error=str(e)
        finally:
            try: cur.close()
            except: pass
            try: conn.close()
            except: pass
    return render_template_string("<!DOCTYPE html><html><head><meta charset='utf-8'><title>CEACGE</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body class='bg-light'><div class='container d-flex justify-content-center align-items-center vh-100'><div class='card p-4' style='width:360px'><h4 class='text-center'>CEACGE FINAL</h4>{% if error %}<div class='alert alert-danger'>{{error}}</div>{% endif %}<form method='post'><input class='form-control mb-2' name='usuario' placeholder='Usuario' required><input class='form-control mb-3' type='password' name='password' placeholder='Contraseña' required><button class='btn btn-primary w-100'>Entrar</button></form></div></div></body></html>", error=error)
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM alumnos"); sec=cur.fetchone(); sec=sec[0] if not isinstance(sec,dict) else list(sec.values())[0]
        cur.execute("SELECT COUNT(*) FROM alumnos_primaria"); prim=cur.fetchone(); prim=prim[0] if not isinstance(prim,dict) else list(prim.values())[0]
        cur.execute("SELECT COUNT(*) FROM centros"); cen=cur.fetchone(); cen=cen[0] if not isinstance(cen,dict) else list(cen.values())[0]
    except: sec=prim=cen=0
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
    content=f"<h3>Panel - {session['usuario']}</h3><div class='row g-3 mt-2'><div class='col-md-4'><div class='card p-3'><h5>Secundaria</h5><h2>{sec}</h2><a href='/alumnos' class='btn btn-sm btn-primary'>Ver alumnos</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Primaria</h5><h2>{prim}</h2><a href='/primaria' class='btn btn-sm btn-success'>Ver primaria</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Centros</h5><h2>{cen}</h2><a href='/centros' class='btn btn-sm btn-warning'>Ver centros</a></div></div></div><div class='mt-4'><a href='/alumnos/nuevo' class='btn btn-primary'>+ Nuevo Secundaria</a> <a href='/primaria/nuevo' class='btn btn-success'>+ Nuevo Primaria</a> <a href='/centros/nuevo' class='btn btn-warning'>+ Nuevo Centro</a> <a href='/usuarios' class='btn btn-dark'>Usuarios</a></div>"
    return render_template_string(BASE, content=content)
@app.route('/alumnos')
def alumnos():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); rows=cur.fetchall()
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
    html="<h4>Alumnos Secundaria <a href='/alumnos/nuevo' class='btn btn-sm btn-primary'>+ Nuevo</a></h4><div class='row'>"
    for r in rows:
        nombre=r['nombre'] if isinstance(r,dict) else r[1]; apellidos=r['apellidos'] if isinstance(r,dict) else r[2]
        html+=f"<div class='col-md-3 mb-3'><div class='card'><div class='card-body'><h6>{nombre} {apellidos}</h6><a href='/alumnos' class='btn btn-sm btn-outline-primary'>Ver</a></div></div></div>"
    html+="</div>"
    return render_template_string(BASE, content=html)
@app.route('/alumnos/nuevo', methods=['GET','POST'])
def alumno_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        nombre=request.form.get('nombre'); apellidos=request.form.get('apellidos'); centro=request.form.get('centro')
        conn=get_conn(); cur=conn.cursor()
        try: cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,centro) VALUES (?,?,?)"), (nombre,apellidos,centro)); conn.commit()
        finally:
            try: cur.close()
            except: pass
            try: conn.close()
            except: pass
        return redirect('/alumnos')
    return render_template_string(BASE, content="<h4>Nuevo Secundaria</h4><form method='post'><input name='nombre' class='form-control mb-2' placeholder='Nombre' required><input name='apellidos' class='form-control mb-2' placeholder='Apellidos' required><input name='centro' class='form-control mb-2' placeholder='Centro'><button class='btn btn-primary'>Guardar</button></form>")
@app.route('/primaria')
def primaria():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("SELECT * FROM alumnos_primaria ORDER BY id DESC"); rows=cur.fetchall()
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
    html="<h4>Primaria <a href='/primaria/nuevo' class='btn btn-sm btn-success'>+ Nuevo</a></h4><div class='row'>"
    for r in rows:
        nombre=r['nombre'] if isinstance(r,dict) else r[1]; apellidos=r['apellidos'] if isinstance(r,dict) else r[2]
        html+=f"<div class='col-md-3 mb-3'><div class='card'><div class='card-body'><h6>{nombre} {apellidos}</h6></div></div></div>"
    html+="</div>"
    return render_template_string(BASE, content=html)
@app.route('/primaria/nuevo', methods=['GET','POST'])
def primaria_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        nombre=request.form.get('nombre'); apellidos=request.form.get('apellidos'); centro=request.form.get('centro')
        conn=get_conn(); cur=conn.cursor()
        try: cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,centro) VALUES (?,?,?)"), (nombre,apellidos,centro)); conn.commit()
        finally:
            try: cur.close()
            except: pass
            try: conn.close()
            except: pass
        return redirect('/primaria')
    return render_template_string(BASE, content="<h4>Nuevo Primaria</h4><form method='post'><input name='nombre' class='form-control mb-2' placeholder='Nombre' required><input name='apellidos' class='form-control mb-2' placeholder='Apellidos' required><input name='centro' class='form-control mb-2' placeholder='Centro'><button class='btn btn-success'>Guardar</button></form>")
@app.route('/centros')
def centros():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("SELECT * FROM centros ORDER BY id DESC"); rows=cur.fetchall()
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
    html="<h4>Centros <a href='/centros/nuevo' class='btn btn-sm btn-warning'>+ Nuevo</a></h4><ul class='list-group'>"
    for r in rows:
        nombre=r['nombre'] if isinstance(r,dict) else r[1]; codigo=r['codigo'] if isinstance(r,dict) else r[2]
        html+=f"<li class='list-group-item'>{nombre} - {codigo}</li>"
    html+="</ul>"
    return render_template_string(BASE, content=html)
@app.route('/centros/nuevo', methods=['GET','POST'])
def centro_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        nombre=request.form.get('nombre'); codigo=request.form.get('codigo'); localidad=request.form.get('localidad')
        conn=get_conn(); cur=conn.cursor()
        try: cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad) VALUES (?,?,?)"), (nombre,codigo,localidad)); conn.commit()
        finally:
            try: cur.close()
            except: pass
            try: conn.close()
            except: pass
        return redirect('/centros')
    return render_template_string(BASE, content="<h4>Nuevo Centro</h4><form method='post'><input name='nombre' class='form-control mb-2' placeholder='Nombre' required><input name='codigo' class='form-control mb-2' placeholder='Código' required><input name='localidad' class='form-control mb-2' placeholder='Localidad'><button class='btn btn-warning'>Guardar</button></form>")
@app.route('/usuarios')
def usuarios():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("SELECT id,usuario,rol FROM usuarios ORDER BY id"); rows=cur.fetchall()
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
    html="<h4>Usuarios</h4><table class='table'><tr><th>Usuario</th><th>Rol</th></tr>"
    for r in rows: html+=f"<tr><td>{r['usuario'] if isinstance(r,dict) else r[1]}</td><td>{r['rol'] if isinstance(r,dict) else r[2]}</td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)
@app.route('/fotos/<path:filename>')
def fotos(filename): return send_from_directory(UPLOAD_FOLDER, filename)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
