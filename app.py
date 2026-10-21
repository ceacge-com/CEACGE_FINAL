import os, sqlite3, io, secrets, string
from flask import Flask, request, redirect, session, send_from_directory, render_template_string, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

app=Flask(__name__)
app.secret_key='V18-SIN-LINEA-DIRECTOR-VER-COMPLETO-ELEGANTE'
basedir=os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER=os.path.join(basedir,"fotos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATABASE_URL=os.environ.get('DATABASE_URL')
USE_POSTGRES=DATABASE_URL and 'postgres' in DATABASE_URL

def get_conn():
    if USE_POSTGRES:
        import psycopg2, psycopg2.extras
        url=DATABASE_URL.replace('postgres://','postgresql://',1) if DATABASE_URL.startswith('postgres://') else DATABASE_URL
        return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn=sqlite3.connect(os.path.join(basedir,"ceacge.db")); conn.row_factory=sqlite3.Row; return conn
def adapt(q): return q.replace('?','%s') if USE_POSTGRES else q

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if USE_POSTGRES:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, foto TEXT, anio TEXT, contacto TEXT, email TEXT, centro_nombre TEXT, centro_codigo TEXT, centro_localidad TEXT, centro_contacto TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, hijo_de TEXT, y_de TEXT, fecha_nacimiento TEXT, centro TEXT, localidad TEXT, codigo TEXT, foto TEXT, anio TEXT, centro_codigo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT, localidad TEXT, contacto TEXT, email TEXT, codigo_acceso TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, foto TEXT, anio TEXT, contacto TEXT, email TEXT, centro_nombre TEXT, centro_codigo TEXT, centro_localidad TEXT, centro_contacto TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, hijo_de TEXT, y_de TEXT, fecha_nacimiento TEXT, centro TEXT, localidad TEXT, codigo TEXT, foto TEXT, anio TEXT, centro_codigo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT, localidad TEXT, contacto TEXT, email TEXT, codigo_acceso TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
    cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),('admin',))
    if not cur.fetchone():
        cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"),('admin',generate_password_hash('ceacge2025'),'admin'))
    conn.commit(); conn.close()

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'usuario' not in session: return redirect('/login')
        return f(*a,**kw)
    return dec
def admin_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if session.get('rol')!='admin': return "Solo admin"
        return f(*a,**kw)
    return dec
def gen_qr(text):
    qr=qrcode.QRCode(box_size=10, border=1); qr.add_data(text); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white").convert('RGB')
    buf=io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0); return buf
def generar_codigo():
    return ''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(8))

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
body{font-family:'Inter',Arial;background:#f3f5f7;margin:0;padding:0}
.card{background:white;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.08);padding:22px;margin:16px auto;max-width:1100px}
.btn{padding:10px 16px;border-radius:10px;text-decoration:none;font-weight:600;display:inline-block;transition:.2s}
.btn-primary{background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white}
.btn-blue{background:#e0f2fe;color:#0a2a7a;border:1px solid #0a2a7a}
.btn-amber{background:#fef3c7;color:#92400e;border:1px solid #f59e0b}
.input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid #d1d5db;background:#f9fafb;outline:none}
.input:focus{border-color:#0a2a7a;box-shadow:0 0 0 3px rgba(10,42,122,.15);background:white}
.label{font-size:12px;font-weight:600;color:#374151;margin-bottom:4px;display:block;text-transform:uppercase;letter-spacing:.5px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.topbar{background:white;padding:14px 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 12px rgba(0,0,0,.06);position:sticky;top:0;z-index:10}
table{border-collapse:collapse;width:100%;overflow:hidden;border-radius:12px}
th{background:#0a2a7a;color:white;font-size:12px;padding:12px 8px;text-transform:uppercase}
td{padding:10px 8px;border-bottom:1px solid #eef2f7;font-size:13px}
.ver-box{background:linear-gradient(135deg,#f8fafc,#eef2ff);border:1px solid #e0e7ff;border-radius:16px;padding:20px}
</style>
"""

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['usuario']; p=request.form['password']
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,)); user=cur.fetchone()
        if user and p and check_password_hash(user['password'], p):
            session['usuario']=user['usuario']; session['rol']=user['rol'] or 'admin'; session['centro_codigo']=user['centro_codigo']; conn.close(); return redirect('/')
        cur.execute(adapt("SELECT * FROM centros WHERE codigo_acceso=?"),(u,)); centro=cur.fetchone()
        if centro:
            session['usuario']=centro['nombre']; session['rol']='centro'; session['centro_codigo']=centro['codigo']; conn.close(); return redirect('/')
        conn.close(); return 'Código incorrecto <a href=/login>volver</a>'
    return f"<body style='display:flex;justify-content:center;align-items:center;height:100vh;background:linear-gradient(135deg,#0a2a7a,#0a7a4a)'><div style='background:white;padding:32px;border-radius:20px;max-width:400px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,.2)'><h2 style='color:#0a2a7a;margin:0 0 8px'>CEACGE V18</h2><p style='color:#6b7280;font-size:13px'>Acceso elegante - Admin y Centros</p><form method=post><label class=label>Usuario o Código Centro</label><input name=usuario class=input required><br><br><label class=label>Password</label><input type=password name=password class=input><br><br><button class='btn btn-primary' style='width:100%;padding:14px'>ENTRAR</button></form></div>{STYLE}</body>"

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); rol=session.get('rol'); mi_codigo=session.get('centro_codigo')
    if rol=='centro':
        cur.execute(adapt("SELECT * FROM alumnos WHERE centro_codigo=? ORDER BY id DESC"),(mi_codigo,)); alumnos=cur.fetchall()
        cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE centro_codigo=? ORDER BY id DESC"),(mi_codigo,)); primaria=cur.fetchall()
        cur.execute(adapt("SELECT * FROM centros WHERE codigo=?"),(mi_codigo,)); centros=cur.fetchall()
    else:
        cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall()
        cur.execute("SELECT * FROM alumnos_primaria ORDER BY id DESC"); primaria=cur.fetchall()
        cur.execute("SELECT * FROM centros ORDER BY id DESC"); centros=cur.fetchall()
    conn.close()
    return render_template_string(f"""
    <div class=topbar><b>👤 {{{{session['usuario']}}}} ({{{{rol}}}}) {{{{mi_codigo or ''}}}}</b><a href='/logout' class=btn style='background:#fee2e2;color:#991b1b'>Salir</a></div>
    <div class=card><h2 style="color:#0a2a7a;margin:0">CEACGE V18 - Vista Completa Elegante</h2><p style="color:#6b7280">Sin línea, seguridad separada, solo Director</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px">
        <a href='/nuevo' class=btn btn-primary>+ Alumno ESBA/BACH</a>
        <a href='/primaria/nuevo' class=btn style='background:#0a7a4a;color:white'>+ Alumno Primaria</a>
        {{% if rol=='admin' %}}<a href='/centros/nuevo' class=btn style='background:#0a2a7a;color:white'>+ Centro</a>{{% endif %}}
    </div></div>

    <div class=card><h3 style="color:#0a2a7a">a) Secundaria y ESBA/Bach ({{{{alumnos|length}}}})</h3>
    <table><tr><th>Foto</th><th>Alumno</th><th>Centro</th><th>Acción</th></tr>
    {{% for x in alumnos %}}<tr><td>{{% if x['foto'] %}}<img src='/fotos/{{{{x['foto']}}}}' width=40 style='border-radius:8px'>{{% endif %}}</td><td><b>{{{{x['nombre']}}}} {{{{x['apellidos']}}}}</b><br><small style="color:#6b7280">{{{{x['contacto']}}}}</small></td><td><small>{{{{x['centro_nombre']}}}} - {{{{x['centro_codigo']}}}}</small></td><td><a href='/alumnos/{{{{x['id']}}}}/ver' class=btn btn-blue>VER</a> <a href='/alumnos/{{{{x['id']}}}}/editar' class=btn btn-amber>EDITAR</a> <a href='/notas/{{{{x['id']}}}}' class=btn>Notas</a> <a href='/pdf/{{{{x['id']}}}}' class='btn btn-primary'>PDF</a></td></tr>{{% endfor %}}</table></div>

    <div class=card><h3 style="color:#0a7a4a">b) Primaria ({{{{primaria|length}}}})</h3>
    <table><tr><th>Foto</th><th>Alumno</th><th>Filiación</th><th>Centro</th><th>Acción</th></tr>
    {{% for p in primaria %}}<tr><td>{{% if p['foto'] %}}<img src='/fotos/{{{{p['foto']}}}}' width=36 style='border-radius:8px'>{{% endif %}}</td><td><b>{{{{p['nombre']}}}} {{{{p['apellidos']}}}}</b></td><td><small>Hijo de {{{{p['hijo_de']}}}} y {{{{p['y_de']}}}}</small></td><td><small>{{{{p['centro']}}}} - {{{{p['codigo']}}}}</small></td><td><a href='/primaria/{{{{p['id']}}}}/ver' class=btn btn-blue>VER</a> <a href='/primaria/{{{{p['id']}}}}/editar' class=btn btn-amber>EDITAR</a></td></tr>{{% endfor %}}</table></div>

    <div class=card><h3 style="color:#0a2a7a">c) Centros ({{{{centros|length}}}})</h3>
    <table><tr><th>Nombre</th><th>Código</th><th>Localidad</th><th>Código Acceso</th><th>Acción</th></tr>
    {{% for c in centros %}}<tr><td><b>{{{{c['nombre']}}}}</b></td><td>{{{{c['codigo']}}}}</td><td>{{{{c['localidad']}}}}</td><td><code style='background:#f1f5f9;padding:6px 8px;border-radius:6px'>{{{{c['codigo_acceso'] or 'SIN'}}}}</code></td><td><a href='/centros/{{{{c['id']}}}}/ver' class=btn btn-blue>VER</a> <a href='/centros/{{{{c['id']}}}}/editar' class=btn btn-amber>EDITAR</a> {{% if rol=='admin' %}}<a href='/centros/{{{{c['id']}}}}/generar_codigo' class=btn style='background:#0a7a4a;color:white'>Generar Código</a>{{% endif %}}</td></tr>{{% endfor %}}</table></div>
    {STYLE}
    """, alumnos=alumnos, primaria=primaria, centros=centros, rol=rol, mi_codigo=mi_codigo, session=session)

@app.route('/alumnos/<int:id>/ver')
@login_required
def alumno_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    if not a: conn.close(); return "No encontrado"
    qr_buf=gen_qr(f"CEACGE-{id:04d} | {a['nombre']} {a['apellidos']} | {a['centro_codigo']} | ceacge-final.onrender.com/pdf/{id}")
    import base64; qr_b64=base64.b64encode(qr_buf.getvalue()).decode()
    conn.close()
    return render_template_string(f"""
    <div class=topbar><a href='/' class=btn btn-blue>← Volver</a><a href='/pdf/{id}' class='btn btn-primary'>Ver PDF Oficial</a></div>
    <div class=card><h2 style="color:#c00000">Ficha Completa Alumno</h2>
    <div style="display:flex;gap:20px;flex-wrap:wrap">
        <div><img src='/fotos/{a['foto']}' width=180 style='border-radius:16px;border:3px solid #0a7a4a;box-shadow:0 8px 20px rgba(0,0,0,.15)' onerror="this.style.display='none'"><br><br>
        <div class=ver-box><b>QR Verificación</b><br><img src='data:image/png;base64,{qr_b64}' width=150><br><small>COD: CEA-{id:04d}-AA</small></div></div>
        <div style="flex:1;min-width:300px">
        <table><tr><td><b>Nombre</b></td><td>{a['nombre']}</td></tr>
        <tr><td><b>Apellidos</b></td><td>{a['apellidos']}</td></tr>
        <tr><td><b>Natural de</b></td><td>{a['natural_de']}</td></tr>
        <tr><td><b>Distrito</b></td><td>{a['distrito']}</td></tr>
        <tr><td><b>Provincia</b></td><td>{a['provincia']}</td></tr>
        <tr><td><b>Contacto Alumno</b></td><td>{a['contacto']}</td></tr>
        <tr><td><b>Email Alumno</b></td><td>{a['email']}</td></tr>
        <tr><td><b>Centro Nombre</b></td><td style="color:#c00000;font-weight:700">{a['centro_nombre']}</td></tr>
        <tr><td><b>Centro Código</b></td><td>{a['centro_codigo']}</td></tr>
        <tr><td><b>Centro Localidad</b></td><td>{a['centro_localidad']}</td></tr>
        <tr><td><b>Centro Contacto</b></td><td>{a['centro_contacto']}</td></tr>
        <tr><td><b>Año Escolar</b></td><td>{a['anio']}</td></tr>
        <tr><td><b>Centro resumen</b></td><td>{a['centro']}</td></tr>
        </table><br><a href='/alumnos/{id}/editar' class='btn btn-amber'>EDITAR INFORMACIÓN</a> <a href='/notas/{id}' class='btn btn-primary'>EDITAR NOTAS</a></div></div></div>{STYLE}
    """, a=a)

@app.route('/primaria/<int:id>/ver')
@login_required
def primaria_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"),(id,)); p=cur.fetchone(); conn.close()
    return render_template_string(f"<div class=topbar><a href='/' class=btn btn-blue>Volver</a></div><div class=card><h2 style='color:#0a7a4a'>Primaria - {p['nombre']} {p['apellidos']}</h2><table><tr><td>Hijo de</td><td>{p['hijo_de']} y {p['y_de']}</td></tr><tr><td>Fecha Nac.</td><td>{p['fecha_nacimiento']}</td></tr><tr><td>Centro</td><td>{p['centro']} - {p['localidad']} - {p['codigo']}</td></tr><tr><td>Año</td><td>{p['anio']}</td></tr></table><br><a href='/primaria/{id}/editar' class='btn btn-amber'>EDITAR</a></div>{STYLE}", p=p)

@app.route('/centros/<int:id>/ver')
@login_required
def centro_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM centros WHERE id=?"),(id,)); c=cur.fetchone()
    qr_buf=gen_qr(f"CENTRO {c['codigo']} | {c['nombre']} | {c['codigo_acceso']}"); import base64; qr_b64=base64.b64encode(qr_buf.getvalue()).decode()
    conn.close()
    return render_template_string(f"""
    <div class=topbar><a href='/' class=btn btn-blue>Volver</a></div>
    <div class=card><h2 style='color:#0a2a7a'>Centro - {c['nombre']}</h2>
    <div style="display:flex;gap:20px"><div class=ver-box><img src='data:image/png;base64,{qr_b64}' width=140><br><small>Acceso Centro</small></div>
    <table style='flex:1'><tr><td><b>Nombre</b></td><td>{c['nombre']}</td></tr><tr><td><b>Código</b></td><td>{c['codigo']}</td></tr><tr><td><b>Localidad</b></td><td>{c['localidad']}</td></tr><tr><td><b>Contacto</b></td><td>{c['contacto']}</td></tr><tr><td><b>Email</b></td><td>{c['email']}</td></tr><tr><td><b>Código Acceso</b></td><td><code style='font-size:18px;background:#f1f5f9;padding:8px 12px;border-radius:8px'>{c['codigo_acceso']}</code></td></tr></table></div><br><a href='/centros/{id}/editar' class='btn btn-amber'>EDITAR</a> <a href='/centros/{id}/generar_codigo' class='btn btn-primary'>Generar Nuevo Código</a></div>{STYLE}
    """, c=c)

@app.route('/alumnos/<int:id>/editar', methods=['GET','POST'])
@login_required
def alumno_editar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("UPDATE alumnos SET nombre=?,apellidos=?,natural_de=?,distrito=?,provincia=?,contacto=?,email=?,centro_nombre=?,centro_codigo=?,centro_localidad=?,centro_contacto=?,anio=? WHERE id=?"),(request.form['nombre'],request.form['apellidos'],request.form['natural_de'],request.form['distrito'],request.form['provincia'],request.form['contacto'],request.form['email'],request.form['centro_nombre'],request.form['centro_codigo'],request.form['centro_localidad'],request.form['centro_contacto'],request.form['anio'],id)); conn.commit(); conn.close(); return redirect(f'/alumnos/{id}/ver')
    conn.close()
    return render_template_string(f"<div class=topbar><a href='/' class=btn>Volver</a></div><div class=card style='max-width:700px'><h2>Editar Alumno</h2><form method=post class=grid><div><label class=label>Nombre</label><input name=nombre value='{a['nombre']}' class=input></div><div><label class=label>Apellidos</label><input name=apellidos value='{a['apellidos']}' class=input></div><div><label class=label>Natural</label><input name=natural_de value='{a['natural_de']}' class=input></div><div><label class=label>Distrito</label><input name=distrito value='{a['distrito']}' class=input></div><div><label class=label>Provincia</label><input name=provincia value='{a['provincia']}' class=input></div><div><label class=label>Contacto</label><input name=contacto value='{a['contacto']}' class=input></div><div><label class=label>Email</label><input name=email value='{a['email']}' class=input></div><div><label class=label>Centro Nombre</label><input name=centro_nombre value='{a['centro_nombre']}' class=input></div><div><label class=label>Código Centro</label><input name=centro_codigo value='{a['centro_codigo']}' class=input></div><div><label class=label>Localidad</label><input name=centro_localidad value='{a['centro_localidad']}' class=input></div><div><label class=label>Contacto Centro</label><input name=centro_contacto value='{a['centro_contacto']}' class=input></div><div><label class=label>Año</label><input name=anio value='{a['anio']}' class=input></div><div style='grid-column:1/-1'><button class='btn btn-primary' style='width:100%;padding:14px;margin-top:10px'>GUARDAR CAMBIOS</button></div></form></div>{STYLE}", a=a)

@app.route('/primaria/<int:id>/editar', methods=['GET','POST'])
@login_required
def primaria_editar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"),(id,)); p=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("UPDATE alumnos_primaria SET nombre=?,apellidos=?,hijo_de=?,y_de=?,fecha_nacimiento=?,centro=?,localidad=?,codigo=?,anio=? WHERE id=?"),(request.form['nombre'],request.form['apellidos'],request.form['hijo_de'],request.form['y_de'],request.form['fecha_nacimiento'],request.form['centro'],request.form['localidad'],request.form['codigo'],request.form['anio'],id)); conn.commit(); conn.close(); return redirect(f'/primaria/{id}/ver')
    conn.close()
    return f"<div class=card style='max-width:600px'><h2>Editar Primaria</h2><form method=post class=grid><div><label class=label>Nombre</label><input name=nombre value='{p['nombre']}' class=input></div><div><label class=label>Apellidos</label><input name=apellidos value='{p['apellidos']}' class=input></div><div><label class=label>Hijo de</label><input name=hijo_de value='{p['hijo_de']}' class=input></div><div><label class=label>Y de</label><input name=y_de value='{p['y_de']}' class=input></div><div><label class=label>Fecha</label><input name=fecha_nacimiento value='{p['fecha_nacimiento']}' type=date class=input></div><div><label class=label>Centro</label><input name=centro value='{p['centro']}' class=input></div><div><label class=label>Localidad</label><input name=localidad value='{p['localidad']}' class=input></div><div><label class=label>Código</label><input name=codigo value='{p['codigo']}' class=input></div><div><label class=label>Año</label><input name=anio value='{p['anio']}' class=input></div><button class='btn btn-primary' style='grid-column:1/-1;padding:14px'>Guardar</button></form></div>{STYLE}"

@app.route('/centros/<int:id>/editar', methods=['GET','POST'])
@login_required
def centro_editar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM centros WHERE id=?"),(id,)); c=cur.fetchone()
    if request.method=='POST':
        if session.get('rol')!='admin':
            cur.execute(adapt("UPDATE centros SET contacto=?,email=? WHERE id=?"),(request.form['contacto'],request.form['email'],id))
        else:
            cur.execute(adapt("UPDATE centros SET nombre=?,codigo=?,localidad=?,contacto=?,email=? WHERE id=?"),(request.form['nombre'],request.form['codigo'],request.form['localidad'],request.form['contacto'],request.form['email'],id))
        conn.commit(); conn.close(); return redirect(f'/centros/{id}/ver')
    conn.close()
    return render_template_string(f"<div class=card style='max-width:600px'><h2>Editar Centro {c['nombre']}</h2><form method=post class=grid><div><label class=label>Nombre</label><input name=nombre value='{c['nombre']}' class=input></div><div><label class=label>Código</label><input name=codigo value='{c['codigo']}' class=input></div><div><label class=label>Localidad</label><input name=localidad value='{c['localidad']}' class=input></div><div><label class=label>Contacto</label><input name=contacto value='{c['contacto']}' class=input></div><div><label class=label>Email</label><input name=email value='{c['email']}' class=input></div><button class='btn btn-primary' style='grid-column:1/-1;padding:14px'>Guardar Centro</button></form></div>{STYLE}", c=c)

@app.route('/centros/<int:id>/generar_codigo')
@login_required
@admin_required
def generar_codigo_centro(id):
    nuevo=generar_codigo(); conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("UPDATE centros SET codigo_acceso=? WHERE id=?"),(nuevo,id))
    cur.execute(adapt("SELECT * FROM centros WHERE id=?"),(id,)); centro=cur.fetchone()
    cur.execute(adapt("SELECT * FROM usuarios WHERE centro_codigo=?"),(centro['codigo'],)); u=cur.fetchone()
    if u: cur.execute(adapt("UPDATE usuarios SET password=? WHERE id=?"),(generate_password_hash(nuevo),u['id']))
    else: cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"),(centro['codigo'],generate_password_hash(nuevo),'centro',centro['codigo']))
    conn.commit(); conn.close()
    return f"<div class=card><h2>Código nuevo para {centro['nombre']}: <span style='background:#f1f5f9;padding:10px 16px;border-radius:10px;font-size:22px'>{nuevo}</span></h2><p>Usuario: {centro['codigo']}</p><a href='/' class=btn btn-primary>Volver</a></div>{STYLE}"

@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor(); foto=request.files.get('foto'); fn=''
        if foto and foto.filename: fn=secure_filename(foto.filename); foto.save(os.path.join(UPLOAD_FOLDER, fn))
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio,contacto,email,centro_nombre,centro_codigo,centro_localidad,centro_contacto) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"),(request.form['nombre'],request.form['apellidos'],request.form['natural_de'],request.form['distrito'],request.form['provincia'],request.form['centro'],fn,request.form['anio'],request.form['contacto'],request.form['email'],request.form['centro_nombre'],request.form['centro_codigo'],request.form['centro_localidad'],request.form['centro_contacto']))
        conn.commit(); cur.execute(adapt("SELECT id FROM alumnos ORDER BY id DESC LIMIT 1")); nid=cur.fetchone()['id']; conn.close(); return redirect(f'/notas/{nid}')
    return f"""
    <div class=topbar><a href='/' class=btn btn-blue>← Volver</a></div>
    <div class=card style='max-width:800px'><h2 style='color:#0a2a7a'>✨ Nuevo Alumno ESBA/Bach</h2>
    <form method=post enctype=multipart/form-data class=grid>
        <div><label class=label>Nombre</label><input name=nombre required class=input></div>
        <div><label class=label>Apellidos</label><input name=apellidos required class=input></div>
        <div><label class=label>Natural de</label><input name=natural_de value=VABE class=input></div>
        <div><label class=label>Distrito</label><input name=distrito value=KOGO class=input></div>
        <div><label class=label>Provincia</label><input name=provincia value=LITORAL class=input></div>
        <div><label class=label>Contacto</label><input name=contacto class=input></div>
        <div><label class=label>Email</label><input name=email class=input></div>
        <div><label class=label>Año Escolar</label><input name=anio value='2023-2024' class=input></div>
        <div><label class=label>Foto</label><input type=file name=foto class=input></div>
        <div style='grid-column:1/-1;height:1px;background:#e5e7eb;margin:10px 0'></div>
        <div><label class=label style='color:#c00000'>Centro Nombre</label><input name=centro_nombre value='IPES PADRE SANTY' required class=input></div>
        <div><label class=label>Código Centro</label><input name=centro_codigo value='IPES-007' required class=input></div>
        <div><label class=label>Localidad Centro</label><input name=centro_localidad value=BATA class=input></div>
        <div><label class=label>Contacto Centro</label><input name=centro_contacto class=input></div>
        <div style='grid-column:1/-1'><label class=label>Centro Resumen</label><input name=centro value='PADRE SANTY - BATA' class=input></div>
        <button class='btn btn-primary' style='grid-column:1/-1;padding:16px'>GUARDAR Y PASAR A NOTAS</button>
    </form></div>{STYLE}
    """

@app.route('/primaria/nuevo', methods=['GET','POST'])
@login_required
def primaria_nuevo():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,hijo_de,y_de,fecha_nacimiento,centro,localidad,codigo,anio,centro_codigo) VALUES (?,?,?,?,?,?,?,?,?,?)"),(request.form['nombre'],request.form['apellidos'],request.form['hijo_de'],request.form['y_de'],request.form['fecha_nacimiento'],request.form['centro'],request.form['localidad'],request.form['codigo'],request.form['anio'],request.form['centro_codigo']))
        conn.commit(); conn.close(); return redirect('/')
    return f"<div class=topbar><a href='/' class=btn>Volver</a></div><div class=card style='max-width:700px'><h2 style='color:#0a7a4a'>Nuevo Alumno Primaria</h2><form method=post class=grid><div><label class=label>Nombre</label><input name=nombre required class=input></div><div><label class=label>Apellidos</label><input name=apellidos required class=input></div><div><label class=label>Hijo de</label><input name=hijo_de required class=input></div><div><label class=label>Y de</label><input name=y_de required class=input></div><div><label class=label>Fecha Nac.</label><input name=fecha_nacimiento type=date required class=input></div><div><label class=label>Centro</label><input name=centro required class=input></div><div><label class=label>Localidad</label><input name=localidad required class=input></div><div><label class=label>Código</label><input name=codigo required class=input></div><div><label class=label>Centro Código vinculación</label><input name=centro_codigo class=input></div><div><label class=label>Año</label><input name=anio value='2023-2024' class=input></div><button class='btn btn-primary' style='grid-column:1/-1;padding:14px;background:#0a7a4a'>Guardar Primaria</button></form></div>{STYLE}"

@app.route('/centros/nuevo', methods=['GET','POST'])
@login_required
@admin_required
def centros_nuevo():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor(); codigo_acceso=generar_codigo()
        cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email,codigo_acceso) VALUES (?,?,?,?,?,?)"),(request.form['nombre'],request.form['codigo'],request.form['localidad'],request.form['contacto'],request.form['email'],codigo_acceso))
        cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"),(request.form['codigo'],generate_password_hash(codigo_acceso),'centro',request.form['codigo']))
        conn.commit(); conn.close(); return redirect('/')
    return f"<div class=topbar><a href='/' class=btn>Volver</a></div><div class=card style='max-width:600px'><h2 style='color:#0a2a7a'>Nuevo Centro - Elegante</h2><form method=post class=grid><div><label class=label>Nombre Centro</label><input name=nombre required class=input></div><div><label class=label>Código</label><input name=codigo required class=input></div><div><label class=label>Localidad</label><input name=localidad required class=input></div><div><label class=label>Contacto</label><input name=contacto class=input></div><div style='grid-column:1/-1'><label class=label>Email</label><input name=email class=input></div><button class='btn btn-primary' style='grid-column:1/-1;padding:14px'>Crear Centro + Código Acceso</button></form></div>{STYLE}"

BLOQUES_IZQ = [
 ("1 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gra. Y de GE","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("1 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gra. Y de GE","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("3 ESBA", ["Lengua Española y Lit","Matemáticas","H. de África y de G.E.","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Inglés","E. Física"]),
 ("4 ESBA", ["Lengua Española y Lit","Matemáticas","H. Universal","Física y Química","Tecnología","Biología y Geología","E. Plástica y Artística","Religión","Inglés","Inglés","E. Física"]),
]
BLOQUES_DER = [
 ("1 BACH", ["Lengua Española","H. de África y de G.E.","Educación Física","Religión","Francés","Inglés","CC. De la Tierra y M.","Biología"], False),
 ("RAMA DE CIENCIA DE LA NATURALEZA Y SALUD", ["Matemática I","Física y Química","Dibujo Técnico I","Biología"], True),
 ("RAMA DE CIENCIA SOCIALES Y HUMANIDADES", ["Latín","Griego","Geografía de G. Espa. Mund.","Matemáticas Aplic. ACC."], True),
 ("RAMA DE TECNOLOGÍA", ["Tecnología Industrial","Matemáticas I","Dibujo Técnico I","Biología"], True),
 ("2 BACH", ["Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencia de la Naturaleza y Salud","Economía de la Empresa","Religión","Francés","Inglés"], False),
 ("RAMA DE CIENCIA DE LA NATURALEZA Y SALUD", ["Matemáticas II","Electrotecnia","Química","Geografía"], True),
 ("RAMA DE TECNOLOGÍA", ["Tecnología Industrial","Matemáticas II","Electrotecnia","Dibujo Técnico"], True),
 ("RAMA DE HUMANIDADES Y CIENCIAS SOCIALES", ["Matemáticas Apl. A las C.S. II","Historia de Arte","Latín","Griego"], True),
]

@app.route('/notas/<int:id>', methods=['GET','POST'])
@login_required
def notas(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(id,))
        for bloque in BLOQUES_IZQ+BLOQUES_DER:
            titulo=bloque[0]; lista=bloque[1]
            for mat in lista:
                o=request.form.get(f"{titulo}__{mat}__o",''); e=request.form.get(f"{titulo}__{mat}__e",'')
                if o or e: cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(id,titulo,mat,o,e))
        conn.commit(); conn.close(); return redirect('/')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); db=cur.fetchall(); nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in db}; conn.close()
    h=f"<div class=topbar><a href='/' class=btn>Volver</a></div><div class=card><h2>Notas {alum['nombre']} {alum['apellidos']}</h2><form method=post>"
    for bloque in BLOQUES_IZQ+BLOQUES_DER:
        titulo=bloque[0]; lista=bloque[1]
        h+=f"<h4 style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:8px;border-radius:8px'>{titulo}</h4><table><tr><th>Asignatura</th><th>Ord</th><th>Extra</th></tr>"
        for mat in lista:
            o,e=nm.get((titulo,mat),('','')); h+=f"<tr><td>{mat}</td><td><input name='{titulo}__{mat}__o' value='{o}' style='width:60px' class=input></td><td><input name='{titulo}__{mat}__e' value='{e}' style='width:60px' class=input></td></tr>"
        h+="</table>"
    h+=f"<br><button class='btn btn-primary' style='width:100%;padding:16px'>GUARDAR NOTAS EN BD</button></form></div>{STYLE}"
    return h

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); nl=cur.fetchall(); conn.close()
    nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in nl}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    ROW_H=12.8; FONT_SIZE=7.2

    c.setFillColor(colors.HexColor("#f8f7f4")); c.rect(0,0,w,h,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0,h-28,w,28,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#0a7a4a")); c.rect(w*0.62,h-28,w*0.38,28,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6.2)
    c.drawString(8, h-11, "REPÚBLICA DE GUINEA ECUATORIAL - MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")

    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",14)
    c.drawString(12, h-46, f"{a['nombre']} {a['apellidos']}".upper())
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",6.8)
    c.drawString(12, h-58, f"NATURAL DE {a['natural_de']}, DEL DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']}".upper())
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",9.5)
    c.drawString(12, h-72, f"IPES \"{a['centro_nombre'] or a['centro']} - {a['centro_localidad'] or 'BATA'}.")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",11); c.drawString(12, h-86, "HOJA ACADÉMICA")
    c.setFont("Helvetica",7); c.drawString(12, h-98, f"AÑO ESCOLAR: {a['anio']}")

    xf=w-65; yf=h-92
    c.setFillColor(colors.white); c.setStrokeColor(colors.black); c.setLineWidth(1.2); c.rect(xf, yf, 52, 64, fill=1, stroke=1)
    c.setFont("Helvetica",7); c.drawCentredString(xf+26, yf+30, "FOTO")
    fp=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(fp):
        try: c.drawImage(ImageReader(fp), xf+1, yf+1, 50, 62, preserveAspectRatio=True)
        except: pass

    def draw_block(x, y_top, bw, titulo, materias, is_roja):
        GAP = 9
        total_h = len(materias)*ROW_H + 11
        c.setFillColor(colors.HexColor("#d6d2c4")); c.rect(x, y_top-total_h, 14, total_h, fill=1, stroke=0)
        c.saveState(); c.translate(x+7, y_top-total_h/2); c.rotate(90)
        c.setFillColor(colors.black); c.setFont("Helvetica-Bold",5.5); c.drawCentredString(0,0, titulo if "ESBA" in titulo or "BACH" in titulo else "RAMA")
        c.restoreState()
        if is_roja:
            c.setFillColor(colors.HexColor("#ffe4e6")); c.rect(x+14, y_top-10, bw-14, 10, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",5)
            c.drawString(x+16, y_top-7, titulo)
            y = y_top-10
        else:
            c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(x+14, y_top-10, bw-14, 10, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",5.5)
            c.drawString(x+16, y_top-7, titulo)
            y = y_top-10
        yy=y
        for mat in materias:
            bx = x+14; bw_mat = bw-14-44
            c.setFillColor(colors.HexColor("#f1f1f1")); c.rect(bx, yy-ROW_H, bw_mat, ROW_H, fill=1, stroke=0)
            c.setStrokeColor(colors.black); c.setLineWidth(0.4)
            c.rect(bx, yy-ROW_H, bw_mat, ROW_H, fill=0, stroke=1)
            c.rect(bx+bw_mat, yy-ROW_H, 22, ROW_H, fill=0, stroke=1)
            c.rect(bx+bw_mat+22, yy-ROW_H, 22, ROW_H, fill=0, stroke=1)
            c.setFillColor(colors.black); c.setFont("Helvetica", FONT_SIZE-0.3); c.drawString(bx+2, yy-ROW_H+3.8, mat[:34])
            o,e = nm.get((titulo,mat),('',''))
            c.setFont("Helvetica-Bold", FONT_SIZE); c.drawCentredString(bx+bw_mat+11, yy-ROW_H+3.8, o); c.drawCentredString(bx+bw_mat+33, yy-ROW_H+3.8, e)
            yy-=ROW_H
        return yy - GAP

    x_left=6; bw_col=(w-20)/2
    y_left=h-112
    for tit,mats in BLOQUES_IZQ:
        y_left=draw_block(x_left, y_left, bw_col, tit, mats, False)
    x_right=w/2+2; y_right=h-112
    for tit,mats,is_roja in BLOQUES_DER:
        y_right=draw_block(x_right, y_right, bw_col, tit, mats, is_roja)

    gap_seguridad = 28
    base_y = min(y_left, y_right) - gap_seguridad
    if base_y < 70: base_y = 70

    c.setFont("Helvetica-Bold",8); c.setFillColor(colors.black)
    c.drawString(w/2-35, base_y, "El Director CEACGE")
    c.setFont("Helvetica",6); c.drawString(w/2-20, base_y-10, "Firma y sello")

    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica",5.8)
    c.drawString(10, 38, "Cualquiera que intente falsificar o duplicar este documento academico, estara incurriendo en un delito de 'de falsificacion'.")
    c.drawString(10, 30, "Los antecedentes de esta Hoja Academica, estan registrados en una base de Datos Nacional de Guinea Ecuatorial.")

    qr_text=f"CEACGE-{id:04d} | {a['nombre']} {a['apellidos']} | {a['centro_codigo']} | ceacge-final.onrender.com/pdf/{id}"
    qr_buf=gen_qr(qr_text)
    c.drawImage(ImageReader(qr_buf), 8, 6, width=28, height=28)
    c.setFillColor(colors.black); c.setFont("Helvetica",5); c.drawString(42, 14, f"Alumno: {a['contacto']} | {a['email']} | {a['anio']} | Verificar QR  COD: CEA-{id:04d}-AA")
    c.setFont("Helvetica-Bold",6.5); c.drawString(w-85, 10, f"COD: CEA-{id:04d}-AA")

    c.showPage(); c.save(); buf.seek(0)
    r=make_response(buf.getvalue()); r.headers['Content-Type']='application/pdf'; r.headers['Content-Disposition']=f'inline; filename=HOJA_V18_{id}.pdf'; return r

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
