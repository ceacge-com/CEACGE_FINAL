import os, secrets, io, base64
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'CEACGE-V21-QR-2026'
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
def gen_codigo(p="SEC"): return f"{p}{secrets.token_hex(3).upper()}"
def gen_qr(text):
    try:
        import qrcode
        qr = qrcode.make(text)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except:
        import urllib.parse
        return f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(text)}"

def init_db():
    conn = get_conn(); cur = conn.cursor()
    try:
        if USE_POSTGRES:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, alumno_codigo TEXT, asignatura TEXT, nota TEXT, periodo TEXT, observaciones TEXT, centro_codigo TEXT)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, alumno_codigo TEXT, asignatura TEXT, nota TEXT, periodo TEXT, observaciones TEXT, centro_codigo TEXT)")
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
        if not cur.fetchone():
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
        conn.commit()
    except Exception as e:
        print(e)
        try: conn.rollback()
        except: pass
    finally:
        try: cur.close(); conn.close()
        except: pass
init_db()

def can_edit(cc):
    if session.get('rol')=='admin': return True
    return session.get('centro_codigo')==cc

BASE = """<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CEACGE</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'><style>@media print{.no-print{display:none}}</style></head><body><nav class='navbar navbar-dark bg-primary no-print'><div class='container'><a class='navbar-brand' href='/dashboard'>CEACGE V21</a><div><a href='/consulta' class='btn btn-sm btn-light me-2'>Consulta Pública</a><span class='text-white me-2'>{{session.usuario}} ({{session.rol}})</span><a href='/logout' class='text-white'>Salir</a></div></div></nav><div class='container mt-4'>{{content|safe}}</div></body></html>"""

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
                    session['usuario']=row['usuario'] if isinstance(row,dict) else row[1]
                    session['rol']=row['rol'] if isinstance(row,dict) else row[3]
                    session['centro_codigo']=row['centro_codigo'] if isinstance(row,dict) else row[4]
                    return redirect('/dashboard')
            error="Usuario o contraseña incorrectos"
        except Exception as e: error=str(e)
        finally:
            try: cur.close(); conn.close()
            except: pass
    return render_template_string("<html><head><meta charset='utf-8'><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'><title>Login</title></head><body class='bg-light'><div class='container d-flex justify-content-center align-items-center vh-100'><div class='card p-4' style='width:360px'><h4 class='text-center'>CEACGE V21</h4>{% if error %}<div class='alert alert-danger'>{{error}}</div>{% endif %}<form method='post'><input class='form-control mb-2' name='usuario' placeholder='Usuario' required><input class='form-control mb-3' type='password' name='password' placeholder='Contraseña' required><button class='btn btn-primary w-100'>Entrar</button></form><hr><a href='/consulta' class='btn btn-outline-secondary w-100'>Consulta Pública por Código</a><small class='text-muted d-block text-center mt-2'>admin / ceacge2025</small></div></div></body></html>", error=error)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM alumnos"); sec=list(cur.fetchone().values())[0] if USE_POSTGRES else cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM alumnos_primaria"); prim=list(cur.fetchone().values())[0] if USE_POSTGRES else cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM centros"); cen=list(cur.fetchone().values())[0] if USE_POSTGRES else cur.fetchone()[0]
    except: sec=prim=cen=0
    finally:
        try: cur.close(); conn.close()
        except: pass
    content=f"<h3>Panel - {session['usuario']} ({session.get('rol')})</h3><div class='row g-3 mt-3'><div class='col-md-4'><div class='card p-3'><h5>Secundaria / Bach</h5><h2>{sec}</h2><a href='/alumnos' class='btn btn-sm btn-primary'>Ver</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Primaria</h5><h2>{prim}</h2><a href='/primaria' class='btn btn-sm btn-success'>Ver</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Centros</h5><h2>{cen}</h2><a href='/centros' class='btn btn-sm btn-warning'>Ver</a></div></div></div><div class='mt-4'><a href='/alumnos/nuevo' class='btn btn-primary'>+ Secundaria</a> <a href='/primaria/nuevo' class='btn btn-success'>+ Primaria</a> <a href='/centros/nuevo' class='btn btn-warning'>+ Centro</a> <a href='/usuarios' class='btn btn-dark'>Usuarios</a> <a href='/consulta' class='btn btn-secondary'>Consulta</a></div><div class='alert alert-info mt-3'>Centro actual: <b>{session.get('centro_codigo') or 'ADMIN CENTRAL'}</b> - Los centros solo editan lo suyo</div>"
    return render_template_string(BASE, content=content)

@app.route('/alumnos')
def alumnos():
    if 'usuario' not in session: return redirect('/login')
    q=request.args.get('q','')
    conn=get_conn(); cur=conn.cursor()
    try:
        if q: cur.execute(adapt("SELECT * FROM alumnos WHERE codigo_alumno LIKE ? OR nombre LIKE ? ORDER BY id DESC"), (f"%{q}%", f"%{q}%"))
        else: cur.execute("SELECT * FROM alumnos ORDER BY id DESC")
        rows=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    html=f"<h4>Secundaria / Bachillerato <a href='/alumnos/nuevo' class='btn btn-sm btn-primary'>+ Nuevo</a></h4><form class='mb-3'><input name='q' value='{q}' placeholder='Buscar código/nombre' class='form-control' style='max-width:300px;display:inline-block'><button class='btn btn-secondary'>Buscar</button></form><div class='table-responsive'><table class='table'><tr><th>Foto</th><th>Código</th><th>Nombre</th><th>Centro</th><th>Acciones</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'centro':r[8],'codigo_alumno':r[10],'foto':r[11],'centro_codigo':r[12]}
        foto=f"<img src='/fotos/{d['foto']}' style='width:50px;height:50px;object-fit:cover'>" if d.get('foto') else "-"
        html+=f"<tr><td>{foto}</td><td><b>{d.get('codigo_alumno')}</b></td><td>{d.get('nombre')} {d.get('apellidos')}</td><td>{d.get('centro')} ({d.get('centro_codigo')})</td><td><a href='/alumno/{d['id']}' class='btn btn-sm btn-primary'>Ver/QR/Notas</a></td></tr>"
    html+="</table></div>"
    return render_template_string(BASE, content=html)

@app.route('/alumnos/nuevo', methods=['GET','POST'])
def alumno_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        f=request.form
        codigo=f.get('codigo_alumno') or gen_codigo("SEC")
        foto_name=None
        if 'foto' in request.files:
            up=request.files['foto']
            if up.filename:
                foto_name=secure_filename(f"{codigo}_{up.filename}")
                up.save(os.path.join(UPLOAD_FOLDER, foto_name))
        cc=session.get('centro_codigo') if session.get('rol')!='admin' else f.get('centro_codigo') or f.get('centro')
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,lugar_nacimiento,distrito,provincia,telefono,email,centro,anio,codigo_alumno,foto,centro_codigo,curso) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"), (f.get('nombre'),f.get('apellidos'),f.get('lugar_nacimiento'),f.get('distrito'),f.get('provincia'),f.get('telefono'),f.get('email'),f.get('centro'),f.get('anio'),codigo,foto_name,cc,f.get('curso')))
            conn.commit()
        finally:
            try: cur.close(); conn.close()
            except: pass
        return redirect('/alumnos')
    extra = f"<input name='centro_codigo' placeholder='Código centro (admin)' class='form-control mb-2'>" if session.get('rol')=='admin' else ""
    content=f"<h4>Nuevo Secundaria / Bach</h4><form method='post' enctype='multipart/form-data' class='row g-2'><div class='col-md-6'><input name='nombre' placeholder='Nombre' class='form-control' required></div><div class='col-md-6'><input name='apellidos' placeholder='Apellidos' class='form-control' required></div><div class='col-md-4'><input name='lugar_nacimiento' placeholder='Lugar nacimiento' class='form-control'></div><div class='col-md-4'><input name='distrito' placeholder='Distrito' class='form-control'></div><div class='col-md-4'><input name='provincia' placeholder='Provincia' class='form-control'></div><div class='col-md-4'><input name='telefono' placeholder='Teléfono contacto' class='form-control'></div><div class='col-md-4'><input name='email' placeholder='Email' class='form-control'></div><div class='col-md-4'><input name='curso' placeholder='Curso Ej: 3ro Bach' class='form-control'></div><div class='col-md-4'><input name='centro' placeholder='Centro' class='form-control'></div><div class='col-md-4'><input name='anio' placeholder='Año' class='form-control'></div><div class='col-md-4'><input name='codigo_alumno' placeholder='Código auto si vacío' class='form-control'></div><div class='col-md-4'>{extra}</div><div class='col-md-6'><input type='file' name='foto' class='form-control' accept='image/*'></div><div class='col-12'><button class='btn btn-primary'>Guardar</button></div></form>"
    return render_template_string(BASE, content=content)

@app.route('/alumno/<int:id>')
def alumno_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,))
        r=cur.fetchone()
        if not r: return "No encontrado",404
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'lugar_nacimiento':r[3],'distrito':r[4],'provincia':r[5],'telefono':r[6],'email':r[7],'centro':r[8],'anio':r[9],'codigo_alumno':r[10],'foto':r[11],'centro_codigo':r[12],'curso':r[13]}
        cur.execute(adapt("SELECT * FROM notas WHERE alumno_codigo=? ORDER BY periodo DESC"), (d['codigo_alumno'],))
        notas=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    qr=gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html=f"<img src='/fotos/{d['foto']}' style='width:150px;border-radius:10px'>" if d.get('foto') else "Sin foto"
    edit_ok=can_edit(d.get('centro_codigo'))
    notas_html="<table class='table'><tr><th>Periodo</th><th>Asignatura</th><th>Nota</th><th>Obs</th></tr>"
    for n in notas:
        nd=dict(n) if isinstance(n,dict) else {'asignatura':n[3],'nota':n[4],'periodo':n[5],'observaciones':n[6]}
        notas_html+=f"<tr><td>{nd['periodo']}</td><td>{nd['asignatura']}</td><td><b>{nd['nota']}</b></td><td>{nd['observaciones'] or ''}</td></tr>"
    notas_html+="</table>"
    form_notas=f"<form method='post' action='/alumno/{id}/nota/add' class='row g-2 mt-3 border p-3'><div class='col-md-3'><input name='periodo' placeholder='Periodo' class='form-control' required></div><div class='col-md-3'><input name='asignatura' placeholder='Asignatura' class='form-control' required></div><div class='col-md-2'><input name='nota' placeholder='Nota' class='form-control' required></div><div class='col-md-4'><input name='observaciones' placeholder='Obs' class='form-control'></div><div class='col-12'><button class='btn btn-success btn-sm'>+ Añadir Nota</button></div></form>" if edit_ok else "<div class='alert alert-secondary'>Solo lectura</div>"
    content=f"<div class='row'><div class='col-md-8'><h4>{d['nombre']} {d['apellidos']} <small>({d['codigo_alumno']})</small></h4><p>Lugar: {d.get('lugar_nacimiento')} | Distrito: {d.get('distrito')} | Provincia: {d.get('provincia')}<br>Tel: {d.get('telefono')} | Email: {d.get('email')}<br>Centro: {d.get('centro')} ({d.get('centro_codigo')}) | Curso: {d.get('curso')}</p><a href='/alumno/{id}/notas' class='btn btn-primary'>Ver Notas / Imprimir</a> <a href='/alumnos' class='btn btn-secondary'>Volver</a><hr><h5>Notas</h5>{notas_html}{form_notas}</div><div class='col-md-4 text-center'>{foto_html}<br><br><div class='card p-2'><b>QR</b><br><img src='{qr}' style='width:180px'><br><small>{d['codigo_alumno']}</small></div></div></div>"
    return render_template_string(BASE, content=content)

@app.route('/alumno/<int:id>/notas')
def alumno_notas(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,))
        r=cur.fetchone()
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13]}
        cur.execute(adapt("SELECT * FROM notas WHERE alumno_codigo=? ORDER BY periodo"), (d['codigo_alumno'],))
        notas=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    rows=""
    for n in notas:
        nd=dict(n) if isinstance(n,dict) else {'periodo':n[5],'asignatura':n[3],'nota':n[4],'observaciones':n[6]}
        rows+=f"<tr><td>{nd['periodo']}</td><td>{nd['asignatura']}</td><td>{nd['nota']}</td><td>{nd['observaciones'] or ''}</td></tr>"
    content=f"<div class='no-print mb-3'><a href='/alumno/{id}' class='btn btn-secondary'>Volver</a> <button onclick='window.print()' class='btn btn-primary'>Imprimir</button></div><div class='card p-4'><h3 class='text-center'>BOLETIN DE NOTAS - CEACGE</h3><hr><p>Alumno: {d['nombre']} {d['apellidos']} | Código: {d['codigo_alumno']} | Centro: {d['centro']}</p><table class='table table-bordered'><tr><th>Periodo</th><th>Asignatura</th><th>Nota</th><th>Obs</th></tr>{rows or '<tr><td colspan=4>Sin notas</td></tr>'}</table><div class='mt-5 d-flex justify-content-between'><span>Firma Tutor</span><span>Sello</span><span>Fecha</span></div></div>"
    return render_template_string(BASE, content=content)

@app.route('/alumno/<int:id>/nota/add', methods=['POST'])
def nota_add(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,))
        r=cur.fetchone()
        d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
        if not can_edit(d['centro_codigo']): return "No autorizado",403
        cur.execute(adapt("INSERT INTO notas (alumno_id,alumno_codigo,asignatura,nota,periodo,observaciones,centro_codigo) VALUES (?,?,?,?,?,?,?)"), (id,d['codigo_alumno'],request.form.get('asignatura'),request.form.get('nota'),request.form.get('periodo'),request.form.get('observaciones'),d['centro_codigo']))
        conn.commit()
    finally:
        try: cur.close(); conn.close()
        except: pass
    return redirect(f'/alumno/{id}')

@app.route('/primaria')
def primaria():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("SELECT * FROM alumnos_primaria ORDER BY id DESC"); rows=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    html="<h4>Primaria <a href='/primaria/nuevo' class='btn btn-sm btn-success'>+ Nuevo</a></h4><div class='row'>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'foto':r[3],'codigo_alumno':r[4]}
        html+=f"<div class='col-md-3 mb-3'><div class='card p-2 text-center'><b>{d['nombre']} {d['apellidos']}</b><br><small>{d['codigo_alumno']}</small><br><a href='/primaria/{d['id']}' class='btn btn-sm btn-success mt-1'>Ver/QR</a></div></div>"
    html+="</div>"
    return render_template_string(BASE, content=html)

@app.route('/primaria/nuevo', methods=['GET','POST'])
def primaria_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        codigo=request.form.get('codigo_alumno') or gen_codigo("PRI")
        foto_name=None
        if 'foto' in request.files:
            up=request.files['foto']
            if up.filename:
                foto_name=secure_filename(f"{codigo}_{up.filename}")
                up.save(os.path.join(UPLOAD_FOLDER, foto_name))
        cc=session.get('centro_codigo') if session.get('rol')!='admin' else request.form.get('centro_codigo') or request.form.get('centro')
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,foto,codigo_alumno,centro,anio,centro_codigo) VALUES (?,?,?,?,?,?,?)"), (request.form.get('nombre'),request.form.get('apellidos'),foto_name,codigo,request.form.get('centro'),request.form.get('anio'),cc))
            conn.commit()
        finally:
            try: cur.close(); conn.close()
            except: pass
        return redirect('/primaria')
    extra = "<input name='centro_codigo' placeholder='Código centro (admin)' class='form-control mb-2'>" if session.get('rol')=='admin' else ""
    return render_template_string(BASE, content=f"<h4>Nuevo Primaria (foto carné)</h4><form method='post' enctype='multipart/form-data'><input name='nombre' placeholder='Nombre' class='form-control mb-2' required><input name='apellidos' placeholder='Apellidos' class='form-control mb-2' required><input name='centro' placeholder='Centro' class='form-control mb-2'><input name='anio' placeholder='Año' class='form-control mb-2'><input name='codigo_alumno' placeholder='Código auto' class='form-control mb-2'>{extra}<input type='file' name='foto' class='form-control mb-2' accept='image/*' required><button class='btn btn-success'>Guardar</button></form>")

@app.route('/primaria/<int:id>')
def primaria_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"), (id,))
        r=cur.fetchone()
        if not r: return "No encontrado",404
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'foto':r[3],'codigo_alumno':r[4],'centro':r[5],'centro_codigo':r[7]}
    finally:
        try: cur.close(); conn.close()
        except: pass
    qr=gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html=f"<img src='/fotos/{d['foto']}' style='width:200px'>" if d.get('foto') else "Sin foto"
    return render_template_string(BASE, content=f"<h4>{d['nombre']} {d['apellidos']} - {d['codigo_alumno']}</h4><div class='row'><div class='col-md-6'>{foto_html}<p>Centro: {d.get('centro')} ({d.get('centro_codigo')})</p><a href='/primaria' class='btn btn-secondary'>Volver</a></div><div class='col-md-6 text-center'><div class='card p-3'><b>QR</b><br><img src='{qr}' style='width:200px'></div></div></div>")

@app.route('/centros')
def centros():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("SELECT * FROM centros ORDER BY id DESC"); rows=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    html="<h4>Centros <a href='/centros/nuevo' class='btn btn-sm btn-warning'>+ Nuevo</a></h4><table class='table'><tr><th>Nombre</th><th>Código</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'nombre':r[1],'codigo':r[2]}
        html+=f"<tr><td>{d['nombre']}</td><td>{d['codigo']}</td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)

@app.route('/centros/nuevo', methods=['GET','POST'])
def centro_nuevo():
    if 'usuario' not in session or session.get('rol')!='admin': return "Solo admin",403
    if request.method=='POST':
        codigo=request.form.get('codigo') or gen_codigo("CEN")
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email) VALUES (?,?,?,?,?)"), (request.form.get('nombre'),codigo,request.form.get('localidad'),request.form.get('contacto'),request.form.get('email')))
            conn.commit()
        finally:
            try: cur.close(); conn.close()
            except: pass
        return redirect('/centros')
    return render_template_string(BASE, content="<h4>Nuevo Centro</h4><form method='post'><input name='nombre' placeholder='Nombre' class='form-control mb-2' required><input name='codigo' placeholder='Código auto si vacío' class='form-control mb-2'><input name='localidad' placeholder='Localidad' class='form-control mb-2'><input name='contacto' placeholder='Contacto' class='form-control mb-2'><input name='email' placeholder='Email' class='form-control mb-2'><button class='btn btn-warning'>Guardar</button></form>")

@app.route('/usuarios')
def usuarios():
    if 'usuario' not in session or session.get('rol')!='admin': return "Solo admin",403
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("SELECT * FROM usuarios ORDER BY id"); rows=cur.fetchall()
        cur.execute("SELECT codigo,nombre FROM centros"); centros=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    opts="".join([f"<option value='{c['codigo'] if isinstance(c,dict) else c[0]}'>{c['codigo'] if isinstance(c,dict) else c[0]} - {c['nombre'] if isinstance(c,dict) else c[1]}</option>" for c in centros])
    html="<h4>Usuarios Centros</h4><table class='table'><tr><th>Usuario</th><th>Rol</th><th>Centro</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'usuario':r[1],'rol':r[3],'centro_codigo':r[4]}
        html+=f"<tr><td>{d['usuario']}</td><td>{d['rol']}</td><td>{d['centro_codigo']}</td></tr>"
    html+=f"</table><hr><h5>Crear usuario centro</h5><form method='post' action='/usuarios/nuevo' class='row g-2'><div class='col-md-3'><input name='usuario' placeholder='Usuario' class='form-control' required></div><div class='col-md-3'><input name='password' placeholder='Contraseña' class='form-control' required></div><div class='col-md-3'><select name='centro_codigo' class='form-control' required><option value=''>Elige centro</option>{opts}</select></div><div class='col-md-3'><button class='btn btn-dark'>Crear</button></div></form>"
    return render_template_string(BASE, content=html)

@app.route('/usuarios/nuevo', methods=['POST'])
def usuario_nuevo():
    if 'usuario' not in session or session.get('rol')!='admin': return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"), (request.form.get('usuario'), generate_password_hash(request.form.get('password')), 'centro', request.form.get('centro_codigo')))
        conn.commit()
    except Exception as e:
        return render_template_string(BASE, content=f"<div class='alert alert-danger'>{e}</div><a href='/usuarios'>Volver</a>")
    finally:
        try: cur.close(); conn.close()
        except: pass
    return redirect('/usuarios')

@app.route('/consulta', methods=['GET','POST'])
def consulta():
    codigo=request.args.get('codigo') or request.form.get('codigo')
    alumno=None; notas=[]
    if codigo:
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("SELECT * FROM alumnos WHERE codigo_alumno=?"), (codigo.strip(),))
            alumno=cur.fetchone()
            if not alumno:
                cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE codigo_alumno=?"), (codigo.strip(),))
                alumno=cur.fetchone()
            if alumno:
                ad=dict(alumno) if isinstance(alumno,dict) else {'codigo_alumno':alumno[10] if len(alumno)>4 else alumno[4]}
                cur.execute(adapt("SELECT * FROM notas WHERE alumno_codigo=?"), (ad['codigo_alumno'],))
                notas=cur.fetchall()
        finally:
            try: cur.close(); conn.close()
            except: pass
    content=f"<h3 class='text-center'>Consulta Pública</h3><form method='post' class='d-flex justify-content-center gap-2 mt-4'><input name='codigo' value='{codigo or ''}' placeholder='Código Alumno' class='form-control' style='max-width:350px' required><button class='btn btn-primary'>Buscar</button></form>"
    if codigo and not alumno: content+=f"<div class='alert alert-danger mt-4 text-center'>Código {codigo} no encontrado</div>"
    if alumno:
        d=dict(alumno) if isinstance(alumno,dict) else {'nombre':alumno[1],'apellidos':alumno[2],'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4],'centro':alumno[8] if len(alumno)>8 else alumno[5],'foto':alumno[11] if len(alumno)>11 else alumno[3]}
        foto=f"<img src='/fotos/{d.get('foto')}' style='width:120px'>" if d.get('foto') else ""
        notas_html="<table class='table'><tr><th>Periodo</th><th>Asignatura</th><th>Nota</th></tr>"
        for n in notas:
            nd=dict(n) if isinstance(n,dict) else {'periodo':n[5],'asignatura':n[3],'nota':n[4]}
            notas_html+=f"<tr><td>{nd['periodo']}</td><td>{nd['asignatura']}</td><td><b>{nd['nota']}</b></td></tr>"
        notas_html+="</table>" if notas else "<p>Sin notas</p>"
        content+=f"<div class='card p-4 mt-4'><div class='row'><div class='col-md-8'><h4>{d.get('nombre')} {d.get('apellidos')}</h4><p>Código: {d.get('codigo_alumno')} | Centro: {d.get('centro')}</p>{notas_html}</div><div class='col-md-4 text-center'>{foto}</div></div></div>"
    return render_template_string(BASE, content=content)

@app.route('/fotos/<path:filename>')
def fotos(filename): return send_from_directory(UPLOAD_FOLDER, filename)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
