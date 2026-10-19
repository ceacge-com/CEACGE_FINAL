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
app.secret_key='V15-VER-EDITAR-ROLES-CODIGOS'
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
        cur.execute("CREATE TABLE IF NOT EXISTS cursos_manuales (id SERIAL PRIMARY KEY, nombre TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, foto TEXT, anio TEXT, contacto TEXT, email TEXT, centro_nombre TEXT, centro_codigo TEXT, centro_localidad TEXT, centro_contacto TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, hijo_de TEXT, y_de TEXT, fecha_nacimiento TEXT, centro TEXT, localidad TEXT, codigo TEXT, foto TEXT, anio TEXT, centro_codigo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT, localidad TEXT, contacto TEXT, email TEXT, codigo_acceso TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cursos_manuales (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
        try:
            cols=[r[1] for r in cur.execute("PRAGMA table_info(alumnos)").fetchall()]
            for col in ['contacto','email','centro_nombre','centro_codigo','centro_localidad','centro_contacto']:
                if col not in cols: cur.execute(f"ALTER TABLE alumnos ADD COLUMN {col} TEXT")
            cols2=[r[1] for r in cur.execute("PRAGMA table_info(alumnos_primaria)").fetchall()]
            if 'centro_codigo' not in cols2: cur.execute("ALTER TABLE alumnos_primaria ADD COLUMN centro_codigo TEXT")
            cols3=[r[1] for r in cur.execute("PRAGMA table_info(centros)").fetchall()]
            if 'codigo_acceso' not in cols3: cur.execute("ALTER TABLE centros ADD COLUMN codigo_acceso TEXT")
            cols4=[r[1] for r in cur.execute("PRAGMA table_info(usuarios)").fetchall()]
            if 'rol' not in cols4: cur.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT")
            if 'centro_codigo' not in cols4: cur.execute("ALTER TABLE usuarios ADD COLUMN centro_codigo TEXT")
        except: pass
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
        if session.get('rol')!='admin': return "Solo admin puede hacer esto. <a href='/'>Volver</a>"
        return f(*a,**kw)
    return dec
def gen_qr(text):
    qr=qrcode.QRCode(box_size=6, border=1); qr.add_data(text); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white").convert('RGB')
    buf=io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0); return buf
def generar_codigo():
    return ''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(8))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['usuario']; p=request.form['password']
        conn=get_conn(); cur=conn.cursor()
        # login como admin o como centro con codigo de acceso
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,))
        user=cur.fetchone()
        if user and check_password_hash(user['password'], p):
            session['usuario']=user['usuario']; session['rol']=user['rol'] or 'admin'; session['centro_codigo']=user['centro_codigo']
            conn.close(); return redirect('/')
        # login centro con codigo_acceso
        cur.execute(adapt("SELECT * FROM centros WHERE codigo_acceso=?"),(u,))
        centro=cur.fetchone()
        if centro:
            session['usuario']=centro['nombre']; session['rol']='centro'; session['centro_codigo']=centro['codigo']; session['centro_id']=centro['id']
            conn.close(); return redirect('/')
        conn.close()
        return 'Código o clave incorrecta <a href=/login>volver</a>'
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:linear-gradient(135deg,#0a2a7a,#0a7a4a)"><div style="background:white;padding:30px;border-radius:12px;max-width:400px"><h2 style="color:#0a2a7a">CEACGE V15</h2><p><b>Admin:</b> admin / ceacge2025<br><b>Centro:</b> usa su código de acceso (8 dígitos)</p><form method=post><input name=usuario placeholder="admin o CODIGO CENTRO" style="width:100%;padding:10px;border-radius:6px;border:1px solid #ccc" required><br><br><input type=password name=password placeholder="Si eres centro deja vacío y pon solo código arriba - Si eres admin pon password" style="width:100%;padding:10px;border-radius:6px;border:1px solid #ccc"><br><small>Centro: escribe solo su código en el primer campo y deja password vacío</small><br><br><button style="width:100%;padding:12px;background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;border:none;border-radius:6px">ENTRAR</button></form></div></body>'

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor()
    rol=session.get('rol'); mi_codigo=session.get('centro_codigo')
    # Filtrado por centro
    if rol=='centro':
        cur.execute(adapt("SELECT * FROM alumnos WHERE centro_codigo=? ORDER BY id DESC"),(mi_codigo,)); alumnos=cur.fetchall()
        cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE centro_codigo=? OR codigo=? ORDER BY id DESC"),(mi_codigo,mi_codigo)); primaria=cur.fetchall()
        cur.execute(adapt("SELECT * FROM centros WHERE codigo=?"),(mi_codigo,)); centros=cur.fetchall()
    else:
        cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall()
        cur.execute("SELECT * FROM alumnos_primaria ORDER BY id DESC"); primaria=cur.fetchall()
        cur.execute("SELECT * FROM centros ORDER BY id DESC"); centros=cur.fetchall()
    cur.execute("SELECT * FROM cursos_manuales ORDER BY id DESC"); cursos=cur.fetchall()
    conn.close()
    return render_template_string("""
    <body style="font-family:Arial;background:#f0f5f1;padding:20px">
    <div style="background:white;padding:12px;border-radius:8px;display:flex;justify-content:space-between;align-items:center"><b>Usuario: {{session['usuario']}} ({{rol}}) {% if mi_codigo %}- Centro: {{mi_codigo}}{% endif %}</b><a href='/logout'>Salir</a></div>
    <h2 style="color:#0a2a7a">CEACGE V15 - VER + EDITAR + CÓDIGOS | PDF solo al imprimir</h2>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:15px">
        <a href='/nuevo' style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:10px 14px;text-decoration:none;border-radius:8px'>+ ALUMNO ESBA/BACH</a>
        <a href='/primaria/nuevo' style='background:#0a7a4a;color:white;padding:10px 14px;text-decoration:none;border-radius:8px'>+ ALUMNO PRIMARIA</a>
        {% if rol=='admin' %}
        <a href='/centros/nuevo' style='background:#0a2a7a;color:white;padding:10px 14px;text-decoration:none;border-radius:8px'>+ CENTRO (admin)</a>
        <a href='/cursos/nuevo' style='background:#64748b;color:white;padding:10px 14px;text-decoration:none;border-radius:8px'>+ CURSO MANUAL</a>
        {% endif %}
    </div>

    <h3 style="color:#0a2a7a">a) Secundaria y ESBA/Bach ({{alumnos|length}})</h3>
    <table border=1 cellpadding=6 style='width:100%;border-collapse:collapse;background:white'><tr style='background:#0a2a7a;color:white'><th>Foto</th><th>Alumno</th><th>Centro</th><th>Acción</th></tr>
    {% for x in alumnos %}<tr>
    <td>{% if x['foto'] %}<img src='/fotos/{{x['foto']}}' width=40 style='border-radius:6px'>{% endif %}</td>
    <td><b>{{x['nombre']}} {{x['apellidos']}}</b><br><small>{{x['contacto']}}</small></td>
    <td><small>{{x['centro_nombre']}} - {{x['centro_codigo']}}</small></td>
    <td style='display:flex;gap:4px;flex-wrap:wrap'>
        <a href='/alumnos/{{x['id']}}/ver' style='background:#e0f2fe;color:#0a2a7a;padding:5px 8px;text-decoration:none;border-radius:5px;border:1px solid #0a2a7a'>VER</a>
        <a href='/alumnos/{{x['id']}}/editar' style='background:#fef3c7;color:#92400e;padding:5px 8px;text-decoration:none;border-radius:5px;border:1px solid #f59e0b'>EDITAR</a>
        <a href='/notas/{{x['id']}}' style='color:#0a2a7a'>Notas</a>
        <a href='/pdf/{{x['id']}}' style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:5px 10px;text-decoration:none;border-radius:5px'>PDF</a>
    </td></tr>{% endfor %}</table>

    <h3 style="color:#0a7a4a;margin-top:20px">b) Primaria ({{primaria|length}})</h3>
    <table border=1 cellpadding=6 style='width:100%;border-collapse:collapse;background:white'><tr style='background:#0a7a4a;color:white'><th>Foto</th><th>Alumno Primaria</th><th>Filiación</th><th>Centro</th><th>Acción</th></tr>
    {% for p in primaria %}<tr>
    <td>{% if p['foto'] %}<img src='/fotos/{{p['foto']}}' width=40>{% endif %}</td>
    <td><b>{{p['nombre']}} {{p['apellidos']}}</b><br><small>{{p['fecha_nacimiento']}}</small></td>
    <td><small>Hijo de {{p['hijo_de']}} y {{p['y_de']}}</small></td>
    <td><small>{{p['centro']}} - {{p['localidad']}} - {{p['codigo']}}</small></td>
    <td><a href='/primaria/{{p['id']}}/ver' style='background:#e0f2fe;padding:5px 8px;border-radius:5px;text-decoration:none'>VER</a> <a href='/primaria/{{p['id']}}/editar' style='background:#fef3c7;padding:5px 8px;border-radius:5px;text-decoration:none'>EDITAR</a></td>
    </tr>{% endfor %}</table>

    <h3 style="color:#0a2a7a;margin-top:20px">c) Centros ({{centros|length}})</h3>
    <table border=1 cellpadding=6 style='width:100%;border-collapse:collapse;background:white'><tr style='background:#0a2a7a;color:white'><th>Nombre</th><th>Código</th><th>Localidad</th><th>Código Acceso</th><th>Acción</th></tr>
    {% for c in centros %}<tr>
    <td>{{c['nombre']}}</td><td>{{c['codigo']}}</td><td>{{c['localidad']}}</td>
    <td><code style='background:#f1f5f9;padding:4px 6px;border-radius:4px'>{{c['codigo_acceso'] or 'SIN CODIGO'}}</code></td>
    <td>
        <a href='/centros/{{c['id']}}/ver' style='background:#e0f2fe;padding:5px 8px;border-radius:5px;text-decoration:none'>VER</a>
        <a href='/centros/{{c['id']}}/editar' style='background:#fef3c7;padding:5px 8px;border-radius:5px;text-decoration:none'>EDITAR</a>
        {% if rol=='admin' %}<a href='/centros/{{c['id']}}/generar_codigo' style='background:#0a7a4a;color:white;padding:5px 8px;border-radius:5px;text-decoration:none'>Generar Código</a>{% endif %}
    </td></tr>{% endfor %}</table>
    </body>""", alumnos=alumnos, primaria=primaria, centros=centros, rol=rol, mi_codigo=mi_codigo, session=session)

# ----- VER COMPLETO Y EDITAR -----
@app.route('/alumnos/<int:id>/ver')
@login_required
def alumno_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone(); conn.close()
    if not a: return "No encontrado"
    if session.get('rol')=='centro' and a['centro_codigo']!=session.get('centro_codigo'): return "No tienes permiso para ver este alumno"
    return render_template_string("""
    <body style="font-family:Arial;padding:20px;background:#f0f5f1"><a href='/'>← Volver</a>
    <div style="background:white;padding:20px;border-radius:12px;max-width:800px;margin-top:15px">
    <h2 style="color:#0a2a7a">Ficha Completa - {{a['nombre']}} {{a['apellidos']}}</h2>
    {% if a['foto'] %}<img src='/fotos/{{a['foto']}}' width=150 style='border-radius:12px;border:2px solid #0a7a4a'>{% endif %}
    <table border=1 cellpadding=8 style='width:100%;border-collapse:collapse;margin-top:15px'>
    <tr><td><b>Nombre</b></td><td>{{a['nombre']}}</td></tr>
    <tr><td><b>Apellidos</b></td><td>{{a['apellidos']}}</td></tr>
    <tr><td><b>Natural de</b></td><td>{{a['natural_de']}}</td></tr>
    <tr><td><b>Distrito</b></td><td>{{a['distrito']}}</td></tr>
    <tr><td><b>Provincia</b></td><td>{{a['provincia']}}</td></tr>
    <tr><td><b>Contacto</b></td><td>{{a['contacto']}}</td></tr>
    <tr><td><b>Email</b></td><td>{{a['email']}}</td></tr>
    <tr><td><b>Centro</b></td><td>{{a['centro_nombre']}} - {{a['centro']}}</td></tr>
    <tr><td><b>Código Centro</b></td><td>{{a['centro_codigo']}}</td></tr>
    <tr><td><b>Localidad Centro</b></td><td>{{a['centro_localidad']}}</td></tr>
    <tr><td><b>Contacto Centro</b></td><td>{{a['centro_contacto']}}</td></tr>
    <tr><td><b>Año</b></td><td>{{a['anio']}}</td></tr>
    </table>
    <br><a href='/alumnos/{{a['id']}}/editar' style='background:#f59e0b;color:white;padding:10px 15px;border-radius:6px;text-decoration:none'>EDITAR INFORMACIÓN</a>
    <a href='/pdf/{{a['id']}}' style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:10px 15px;border-radius:6px;text-decoration:none;margin-left:10px'>VER PDF</a>
    </div></body>""", a=a)

@app.route('/alumnos/<int:id>/editar', methods=['GET','POST'])
@login_required
def alumno_editar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    if not a: conn.close(); return "No encontrado"
    if session.get('rol')=='centro' and a['centro_codigo']!=session.get('centro_codigo'): conn.close(); return "Solo puedes editar alumnos de tu centro"
    if request.method=='POST':
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; natural=request.form['natural_de']; distrito=request.form['distrito']; provincia=request.form['provincia']; contacto=request.form['contacto']; email=request.form['email']
        c_nombre=request.form['centro_nombre']; c_codigo=request.form['centro_codigo']; c_localidad=request.form['centro_localidad']; c_contacto=request.form['centro_contacto']; anio=request.form['anio']; foto_file=request.files.get('foto'); fn=a['foto']
        if foto_file and foto_file.filename:
            fn=secure_filename(foto_file.filename); foto_file.save(os.path.join(UPLOAD_FOLDER, fn))
        cur.execute(adapt("UPDATE alumnos SET nombre=?,apellidos=?,natural_de=?,distrito=?,provincia=?,contacto=?,email=?,centro_nombre=?,centro_codigo=?,centro_localidad=?,centro_contacto=?,anio=?,foto=? WHERE id=?"),(nombre,apellidos,natural,distrito,provincia,contacto,email,c_nombre,c_codigo,c_localidad,c_contacto,anio,fn,id))
        conn.commit(); conn.close(); return redirect(f'/alumnos/{id}/ver')
    conn.close()
    return render_template_string("""
    <body style="font-family:Arial;padding:20px"><h2>Editar {{a['nombre']}} {{a['apellidos']}}</h2>
    <form method=post enctype=multipart/form-data style='background:white;padding:20px;max-width:600px;display:flex;flex-direction:column;gap:8px'>
    Nombre:<input name=nombre value="{{a['nombre']}}" required> Apellidos:<input name=apellidos value="{{a['apellidos']}}" required>
    Natural:<input name=natural_de value="{{a['natural_de']}}"> Distrito:<input name=distrito value="{{a['distrito']}}"> Provincia:<input name=provincia value="{{a['provincia']}}">
    Contacto:<input name=contacto value="{{a['contacto']}}"> Email:<input name=email value="{{a['email']}}">
    Centro Nombre:<input name=centro_nombre value="{{a['centro_nombre']}}"> Codigo:<input name=centro_codigo value="{{a['centro_codigo']}}"> Localidad:<input name=centro_localidad value="{{a['centro_localidad']}}"> Contacto Centro:<input name=centro_contacto value="{{a['centro_contacto']}}">
    Año:<input name=anio value="{{a['anio']}}"> Foto:<input type=file name=foto><button style='padding:12px;background:#0a2a7a;color:white;border:none;border-radius:6px'>GUARDAR CAMBIOS</button></form><a href='/'>Volver</a></body>""", a=a)

@app.route('/primaria/<int:id>/ver')
@login_required
def primaria_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"),(id,)); p=cur.fetchone(); conn.close()
    if not p: return "No encontrado"
    if session.get('rol')=='centro' and p['centro_codigo']!=session.get('centro_codigo') and p['codigo']!=session.get('centro_codigo'): return "Sin permiso"
    return render_template_string("""<body style="font-family:Arial;padding:20px"><a href='/'>Volver</a><div style="background:white;padding:20px;border-radius:12px;max-width:700px;margin-top:10px">
    <h2 style="color:#0a7a4a">Primaria - {{p['nombre']}} {{p['apellidos']}}</h2>
    {% if p['foto'] %}<img src='/fotos/{{p['foto']}}' width=140 style='border-radius:10px'>{% endif %}
    <table border=1 cellpadding=8 style='width:100%;border-collapse:collapse;margin-top:10px'>
    <tr><td>Nombre</td><td>{{p['nombre']}} {{p['apellidos']}}</td></tr><tr><td>Hijo de</td><td>{{p['hijo_de']}} y de {{p['y_de']}}</td></tr><tr><td>Fecha Nac.</td><td>{{p['fecha_nacimiento']}}</td></tr><tr><td>Centro</td><td>{{p['centro']}}</td></tr><tr><td>Localidad</td><td>{{p['localidad']}}</td></tr><tr><td>Código</td><td>{{p['codigo']}} (centro_codigo: {{p['centro_codigo']}})</td></tr><tr><td>Año</td><td>{{p['anio']}}</td></tr></table>
    <br><a href='/primaria/{{p['id']}}/editar' style='background:#0a7a4a;color:white;padding:10px 15px;border-radius:6px;text-decoration:none'>EDITAR</a></div></body>""", p=p)

@app.route('/primaria/<int:id>/editar', methods=['GET','POST'])
@login_required
def primaria_editar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"),(id,)); p=cur.fetchone()
    if not p: conn.close(); return "No encontrado"
    if session.get('rol')=='centro' and p['centro_codigo']!=session.get('centro_codigo'): conn.close(); return "Sin permiso"
    if request.method=='POST':
        cur.execute(adapt("UPDATE alumnos_primaria SET nombre=?,apellidos=?,hijo_de=?,y_de=?,fecha_nacimiento=?,centro=?,localidad=?,codigo=?,centro_codigo=?,anio=? WHERE id=?"),(request.form['nombre'],request.form['apellidos'],request.form['hijo_de'],request.form['y_de'],request.form['fecha_nacimiento'],request.form['centro'],request.form['localidad'],request.form['codigo'],request.form['centro_codigo'],request.form['anio'],id))
        conn.commit(); conn.close(); return redirect(f'/primaria/{id}/ver')
    conn.close()
    return render_template_string("""<body style="font-family:Arial;padding:20px"><h2>Editar Primaria</h2><form method=post style='display:flex;flex-direction:column;gap:8px;max-width:500px'>
    Nombre:<input name=nombre value="{{p['nombre']}}"> Apellidos:<input name=apellidos value="{{p['apellidos']}}"> Hijo de:<input name=hijo_de value="{{p['hijo_de']}}"> Y de:<input name=y_de value="{{p['y_de']}}"> Fecha:<input name=fecha_nacimiento value="{{p['fecha_nacimiento']}}" type=date>
    Centro:<input name=centro value="{{p['centro']}}"> Localidad:<input name=localidad value="{{p['localidad']}}"> Codigo:<input name=codigo value="{{p['codigo']}}"> Centro Codigo:<input name=centro_codigo value="{{p['centro_codigo']}}"> Año:<input name=anio value="{{p['anio']}}">
    <button style='padding:10px;background:#0a7a4a;color:white;border:none;border-radius:6px'>GUARDAR</button></form></body>""", p=p)

@app.route('/centros/<int:id>/ver')
@login_required
def centro_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM centros WHERE id=?"),(id,)); c=cur.fetchone(); conn.close()
    if session.get('rol')=='centro' and c['codigo']!=session.get('centro_codigo'): return "Solo puedes ver tu registro"
    return render_template_string("""<body style="font-family:Arial;padding:20px"><a href='/'>Volver</a><div style="background:white;padding:20px;border-radius:12px;max-width:600px">
    <h2>Centro - {{c['nombre']}}</h2><table border=1 cellpadding=8 style='width:100%;border-collapse:collapse'>
    <tr><td>Nombre</td><td>{{c['nombre']}}</td></tr><tr><td>Código</td><td>{{c['codigo']}}</td></tr><tr><td>Localidad</td><td>{{c['localidad']}}</td></tr><tr><td>Contacto</td><td>{{c['contacto']}}</td></tr><tr><td>Email</td><td>{{c['email']}}</td></tr><tr><td>Código Acceso</td><td><b>{{c['codigo_acceso']}}</b></td></tr></table>
    <br><a href='/centros/{{c['id']}}/editar' style='background:#0a2a7a;color:white;padding:10px;border-radius:6px;text-decoration:none'>EDITAR</a>
    {% if session['rol']=='admin' %}<a href='/centros/{{c['id']}}/generar_codigo' style='background:#0a7a4a;color:white;padding:10px;border-radius:6px;text-decoration:none;margin-left:10px'>Generar Nuevo Código Acceso</a>{% endif %}
    </div></body>""", c=c)

@app.route('/centros/<int:id>/editar', methods=['GET','POST'])
@login_required
def centro_editar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM centros WHERE id=?"),(id,)); c=cur.fetchone()
    if not c: conn.close(); return "No existe"
    if session.get('rol')=='centro' and c['codigo']!=session.get('centro_codigo'): conn.close(); return "Solo puedes editar tu centro"
    if session.get('rol')!='admin' and session.get('rol')!='centro': conn.close(); return "Sin permiso"
    if request.method=='POST':
        if session.get('rol')!='admin':
            # Centro solo puede modificar contacto/email, no codigo/nombre
            cur.execute(adapt("UPDATE centros SET contacto=?,email=? WHERE id=?"),(request.form['contacto'],request.form['email'],id))
        else:
            cur.execute(adapt("UPDATE centros SET nombre=?,codigo=?,localidad=?,contacto=?,email=? WHERE id=?"),(request.form['nombre'],request.form['codigo'],request.form['localidad'],request.form['contacto'],request.form['email'],id))
        conn.commit(); conn.close(); return redirect(f'/centros/{id}/ver')
    conn.close()
    return render_template_string("""<body style="font-family:Arial;padding:20px"><h2>Editar Centro - {{c['nombre']}}</h2>
    <form method=post style='max-width:500px;display:flex;flex-direction:column;gap:8px'>
    {% if session['rol']=='admin' %}
    Nombre:<input name=nombre value="{{c['nombre']}}"> Código:<input name=codigo value="{{c['codigo']}}"> Localidad:<input name=localidad value="{{c['localidad']}}">
    {% else %}<p><b>{{c['nombre']}} - {{c['codigo']}} (solo contacto editable para centros)</b></p>{% endif %}
    Contacto:<input name=contacto value="{{c['contacto']}}"> Email:<input name=email value="{{c['email']}}">
    <button style='padding:10px;background:#0a2a7a;color:white;border:none;border-radius:6px'>GUARDAR</button></form></body>""", c=c)

@app.route('/centros/<int:id>/generar_codigo')
@login_required
@admin_required
def generar_codigo_centro(id):
    nuevo=generar_codigo()
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("UPDATE centros SET codigo_acceso=? WHERE id=?"),(nuevo,id))
    # Crear o actualizar usuario centro
    cur.execute(adapt("SELECT * FROM centros WHERE id=?"),(id,)); centro=cur.fetchone()
    cur.execute(adapt("SELECT * FROM usuarios WHERE centro_codigo=?"),(centro['codigo'],))
    u=cur.fetchone()
    if u:
        cur.execute(adapt("UPDATE usuarios SET usuario=?, password=?, rol=?, centro_codigo=? WHERE id=?"),(centro['codigo'], generate_password_hash(nuevo), 'centro', centro['codigo'], u['id']))
    else:
        cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"),(centro['codigo'], generate_password_hash(nuevo), 'centro', centro['codigo']))
    conn.commit(); conn.close()
    return f"<body style='font-family:Arial;padding:20px'><h2>Código generado para {centro['nombre']}</h2><p style='font-size:24px;background:#f1f5f9;padding:15px;border-radius:8px'>Código: <b>{nuevo}</b></p><p>El centro entra en login escribiendo: <b>{centro['codigo']}</b> como usuario y este código como contraseña, o solo el código en el primer campo.</p><p>Comparte este código de forma segura.</p><a href='/centros/{id}/ver'>Volver a ver centro</a> | <a href='/'>Inicio</a></body>"

# ----- RESTO V14 SE MANTIENE IGUAL -----
@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM centros"); centros_list=cur.fetchall()
    if request.method=='POST':
        if session.get('rol')=='centro':
            # Centro solo puede crear alumnos de su propio centro
            mi_codigo=session.get('centro_codigo')
            cur.execute(adapt("SELECT * FROM centros WHERE codigo=?"),(mi_codigo,)); mi_centro=cur.fetchone()
            c_nombre=mi_centro['nombre']; c_codigo=mi_centro['codigo']; c_localidad=mi_centro['localidad']; c_contacto=mi_centro['contacto']
        else:
            c_nombre=request.form['centro_nombre']; c_codigo=request.form['centro_codigo']; c_localidad=request.form['centro_localidad']; c_contacto=request.form['centro_contacto']
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; natural=request.form['natural_de']; distrito=request.form['distrito']; provincia=request.form['provincia']; centro=request.form['centro']; foto_file=request.files.get('foto'); contacto=request.form['contacto']; email=request.form['email']; anio=request.form['anio']
        fn=''
        if foto_file and foto_file.filename:
            fn=secure_filename(foto_file.filename); foto_file.save(os.path.join(UPLOAD_FOLDER, fn))
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio,contacto,email,centro_nombre,centro_codigo,centro_localidad,centro_contacto) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"),(nombre,apellidos,natural,distrito,provincia,centro,fn,anio,contacto,email,c_nombre,c_codigo,c_localidad,c_contacto))
        conn.commit(); cur.execute(adapt("SELECT id FROM alumnos ORDER BY id DESC LIMIT 1")); nid=cur.fetchone()['id']; conn.close(); return redirect(f'/notas/{nid}')
    conn.close()
    options="".join([f"<option value='{c['nombre']}' data-codigo='{c['codigo']}' data-localidad='{c['localidad']}' data-contacto='{c['contacto']}'>{c['nombre']} - {c['codigo']}</option>" for c in centros_list])
    disabled = "disabled" if session.get('rol')=='centro' else ""
    return f"<body style='font-family:Arial;background:#f0f5f1;padding:20px'><h2>NUEVO ALUMNO ESBA - Rol: {session.get('rol')}</h2><form method=post enctype=multipart/form-data style='background:white;padding:20px;max-width:700px;display:flex;flex-direction:column;gap:8px'>Nombre:<input name=nombre required> Apellidos:<input name=apellidos required> Natural:<input name=natural_de value='VABE'> Distrito:<input name=distrito value='KOGO'> Provincia:<input name=provincia value='LITORAL'> Contacto:<input name=contacto> E-mail:<input name=email> Año:<input name=anio value='2023-2024'> Foto:<input type=file name=foto><h3>Centro</h3><select onchange=\"document.querySelector('[name=centro_nombre]').value=this.options[this.selectedIndex].value;\" {disabled}><option>-- Elegir --</option>{options}</select> Nombre centro:<input name=centro_nombre value='IPES PADRE SANTY'> Código:<input name=centro_codigo> Localidad:<input name=centro_localidad> Contacto centro:<input name=centro_contacto> Centro resumen:<input name=centro value='PADRE SANTY - BATA'><button style='padding:14px;background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;border:none;border-radius:8px'>GUARDAR EN BD</button></form><a href='/'>Volver</a></body>"

@app.route('/primaria/nuevo', methods=['GET','POST'])
@login_required
def primaria_nuevo():
    if request.method=='POST':
        centro_codigo = session.get('centro_codigo') if session.get('rol')=='centro' else request.form.get('centro_codigo','')
        conn=get_conn(); cur=conn.cursor(); foto_file=request.files.get('foto'); fname=''
        if foto_file and foto_file.filename:
            fname=secure_filename(foto_file.filename); foto_file.save(os.path.join(UPLOAD_FOLDER, fname))
        cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,hijo_de,y_de,fecha_nacimiento,centro,localidad,codigo,foto,anio,centro_codigo) VALUES (?,?,?,?,?,?,?,?,?,?,?)"),(request.form['nombre'],request.form['apellidos'],request.form['hijo_de'],request.form['y_de'],request.form['fecha_nacimiento'],request.form['centro'],request.form['localidad'],request.form['codigo'],fname,request.form['anio'],centro_codigo)); conn.commit(); conn.close(); return redirect('/')
    return """<body style="font-family:Arial;padding:20px"><h2>NUEVO PRIMARIA</h2><form method=post enctype=multipart/form-data style='max-width:500px;display:flex;flex-direction:column;gap:8px'>Nombre:<input name=nombre required> Apellidos:<input name=apellidos required> Hijo de:<input name=hijo_de required> Y de:<input name=y_de required> Fecha:<input name=fecha_nacimiento type=date required> Centro:<input name=centro required> Localidad:<input name=localidad required> Código:<input name=codigo required> Centro Codigo (para vincular):<input name=centro_codigo> Año:<input name=anio value='2023-2024'> Foto:<input type=file name=foto><button style='padding:10px;background:#0a7a4a;color:white;border:none;border-radius:6px'>GUARDAR PRIMARIA</button></form><a href='/'>Volver</a></body>"""

@app.route('/centros/nuevo', methods=['GET','POST'])
@login_required
@admin_required
def centros_nuevo():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor(); codigo_acceso=generar_codigo(); cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email,codigo_acceso) VALUES (?,?,?,?,?,?)"),(request.form['nombre'],request.form['codigo'],request.form['localidad'],request.form['contacto'],request.form['email'],codigo_acceso)); cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"),(request.form['codigo'], generate_password_hash(codigo_acceso), 'centro', request.form['codigo'])); conn.commit(); conn.close(); return redirect('/')
    return """<body style="font-family:Arial;padding:20px"><h2>NUEVO CENTRO - Admin genera código acceso automático</h2><form method=post style='max-width:500px;display:flex;flex-direction:column;gap:8px'>Nombre:<input name=nombre required> Código:<input name=codigo required> Localidad:<input name=localidad required> Contacto:<input name=contacto> Email:<input name=email><button style='padding:10px;background:#0a2a7a;color:white;border:none;border-radius:6px'>GUARDAR CENTRO + GENERAR CÓDIGO ACCESO</button></form><a href='/'>Volver</a></body>"""

@app.route('/cursos/nuevo', methods=['GET','POST'])
@login_required
@admin_required
def cursos_nuevo():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("INSERT INTO cursos_manuales (nombre,tipo) VALUES (?,?)"),(request.form['nombre'],request.form['tipo'])); conn.commit(); conn.close(); return redirect('/')
    return """<body style="font-family:Arial;padding:20px"><h2>CURSO MANUAL</h2><form method=post style='max-width:500px;display:flex;flex-direction:column;gap:8px'>Nombre curso:<input name=nombre required> Tipo:<select name=tipo><option>ESBA</option><option>RAMA</option></select><button>GUARDAR</button></form><a href='/'>Volver</a></body>"""

BLOQUES_IZQ = [
 ("1 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("2 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("3 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Biología y Geología","Física y Química","Tecnología","E. Plástica y Visual I","Religión","Inglés","Francés","E. Física"]),
 ("4 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"]),
]
BLOQUES_DER = [
 ("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD", ["Lengua Española y Lit","Matemáticas","Biología","Física y Química","Dibujo Técnico I","Religión"], True),
 ("RAMA DE CIENCIAS SOCIALES Y HUMANIDADES", ["Latín","Literatura","Geografía de la España Actual","Mat. aplicadas a CC.SS."], True),
 ("1 BACH", ["Lengua Española y Lit","Matemáticas I","Física y Química","Filosofía","Historia del Mundo Contemporáneo","Inglés","Francés","E. Física","Religión"], False),
 ("RAMA DE TECNOLOGÍA", ["Tecnología Industrial I","Matemáticas I","Dibujo técnico I","Física"], True),
 ("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD Y TECNOLOGÍA", ["Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencias de la Tierra y Medio Ambiente","Tecnología de la Información","Biología","Física","Química"], True),
 ("2 BACH", ["Lengua Española y Lit","Matemáticas II","Física","Química","Biología","Historia de España","Inglés","Filosofía","E. Física"], False),
]

@app.route('/notas/<int:id>', methods=['GET','POST'])
@login_required
def notas(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); alum=cur.fetchone()
    if not alum: conn.close(); return "Alumno no existe"
    if session.get('rol')=='centro' and alum['centro_codigo']!=session.get('centro_codigo'): conn.close(); return "No puedes editar notas de otro centro"
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(id,))
        for bloque in BLOQUES_IZQ+BLOQUES_DER:
            titulo=bloque[0]; lista=bloque[1]
            for mat in lista:
                o=request.form.get(f"{titulo}__{mat}__o",''); e=request.form.get(f"{titulo}__{mat}__e",'')
                if o or e: cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(id,titulo,mat,o,e))
        conn.commit(); conn.close(); return redirect(f'/')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); db=cur.fetchall(); nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in db}; conn.close()
    h=f"<body style='font-family:Arial;padding:15px'><h2>Notas de {alum['nombre']} - Solo su centro y admin pueden modificar</h2><form method=post>"
    for bloque in BLOQUES_IZQ+BLOQUES_DER:
        titulo=bloque[0]; lista=bloque[1]
        h+=f"<h4 style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:6px;border-radius:4px'>{titulo}</h4><table border=1 style='width:100%;border-collapse:collapse'>"
        for mat in lista:
            o,e=nm.get((titulo,mat),('','')); h+=f"<tr><td style='width:70%'>{mat}</td><td><input name='{titulo}__{mat}__o' value='{o}' style='width:60px'></td><td><input name='{titulo}__{mat}__e' value='{e}' style='width:60px'></td></tr>"
        h+="</table>"
    h+="<br><button style='padding:15px;background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;width:100%;border:none;border-radius:8px'>GUARDAR NOTAS EN BD</button></form><br><a href='/'>Volver</a></body>"
    return h

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); nl=cur.fetchall(); conn.close()
    if not a: return "No existe"
    if session.get('rol')=='centro' and a['centro_codigo']!=session.get('centro_codigo'): return "Solo puedes ver alumnos de tu centro"
    nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in nl}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    FONT_SIZE=8.5; ROW_H=12
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0,h-28,w,28,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#0a7a4a")); c.rect(w*0.65,h-28,w*0.35,28,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6.5); c.drawString(10,h-18,"REPÚBLICA DE GUINEA ECUATORIAL - MINISTERIO DE EDUCACIÓN")
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold",11); c.drawString(10,h-44,f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",7.5); c.drawString(10,h-56,f"NATURAL DE {a['natural_de']}, DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']}")
    c.setFont("Helvetica-Bold",11); c.setFillColor(colors.HexColor("#0a2a7a"))
    centro_full = a['centro_nombre'] or a['centro']
    c.drawString(10,h-70,f"{centro_full} - {a['centro_localidad'] or 'BATA'} | Cod: {a['centro_codigo'] or ''} | Contacto: {a['centro_contacto'] or a['contacto'] or ''}")
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",13); c.drawString(w*0.68,h-70,"HOJA ACADÉMICA")
    c.setFillColor(colors.HexColor("#0a7a4a")); c.rect(0,h-73,w,1.2,fill=1,stroke=0)
    xf=w-62; yf=h-66
    c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor("#0a7a4a")); c.rect(xf,yf,50,58,fill=1,stroke=1)
    fp=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(fp):
        try: c.drawImage(ImageReader(fp), xf+1,yf+1,48,56,preserveAspectRatio=True)
        except: pass
    def draw_block(x, y_top, bw, titulo, materias, is_roja):
        GAP = 22 if not is_roja else 12
        total_h = len(materias)*ROW_H + 14
        if is_roja:
            c.setFillColor(colors.HexColor("#e6f4ea")); c.rect(x, y_top-11, bw, 11, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#0a7a4a")); c.setFont("Helvetica-Bold",5.5); c.drawString(x+3, y_top-7.5, titulo)
            y = y_top-11
        else:
            c.setFillColor(colors.HexColor("#64748b")); c.rect(x, y_top-total_h-3, 14, total_h+3, fill=1, stroke=0)
            c.saveState(); c.translate(x+7, y_top-total_h/2); c.rotate(90); c.setFillColor(colors.white); c.setFont("Helvetica-Bold",7); c.drawCentredString(0,0,"CURSO"); c.restoreState()
            c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(x+14, y_top-11, bw-14, 11, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6.5); c.drawString(x+18, y_top-7.5, titulo)
            y = y_top-11
        yy=y
        for mat in materias:
            bx = x+14 if not is_roja else x
            bw_materia = (bw-14 if not is_roja else bw)-44
            c.setFillColor(colors.HexColor("#e0f2fe") if not is_roja else colors.HexColor("#e6f4ea"))
            c.rect(bx, yy-ROW_H, bw_materia, ROW_H, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#93c5fd") if not is_roja else colors.HexColor("#86efac")); c.setLineWidth(0.35)
            c.rect(bx, yy-ROW_H, bw_materia, ROW_H, fill=0, stroke=1)
            c.setFillColor(colors.white); c.rect(bx+bw_materia, yy-ROW_H, 22, ROW_H, fill=1, stroke=1); c.rect(bx+bw_materia+22, yy-ROW_H, 22, ROW_H, fill=1, stroke=1)
            c.setFillColor(colors.black); c.setFont("Helvetica", FONT_SIZE-1.2); c.drawString(bx+2, yy-ROW_H+3.5, mat[:38])
            o,e = nm.get((titulo,mat),('',''))
            c.setFont("Helvetica-Bold", FONT_SIZE); c.drawCentredString(bx+bw_materia+11, yy-ROW_H+3.5, o); c.drawCentredString(bx+bw_materia+33, yy-ROW_H+3.5, e)
            yy-=ROW_H
        return yy - GAP
    x_left=8; bw_col=(w-24)/2
    y_left=h-85
    for tit,mats in BLOQUES_IZQ:
        y_left=draw_block(x_left, y_left, bw_col, tit, mats, False)
    x_right=w/2+4; y_right=h-85
    for bloque in BLOQUES_DER:
        tit,mats,is_roja=bloque
        y_right=draw_block(x_right, y_right, bw_col, tit, mats, is_roja)
    linea_y = min(y_left, y_right) - 2
    if linea_y < 95: linea_y = 95
    c.setStrokeColor(colors.HexColor("#0a2a7a")); c.setLineWidth(1.2)
    c.line(8, linea_y, w-8, linea_y)
    c.setFont("Helvetica-Bold",8); c.setFillColor(colors.HexColor("#0a2a7a"))
    c.drawString(15, linea_y-14, "VB del Inspector de Educación")
    c.drawString(w*0.55, linea_y-14, "El Director CEACGE")
    c.setFont("Helvetica",6); c.setFillColor(colors.black)
    c.drawString(15, linea_y-24, "Firma y sello")
    c.drawString(w*0.55, linea_y-24, "Firma y sello")
    seguridad = "ADVERTENCIA DE SEGURIDAD: La falsificación, alteración o uso fraudulento de este documento constituye delito tipificado en el Código Penal de la República de Guinea Ecuatorial. Este documento está registrado y verificado en la Base de Datos Nacional del Ministerio de Educación. Cualquier modificación invalida su autenticidad. Para verificar, escanee el código QR o visite ceacge-final.onrender.com/pdf/"+str(id)+". Contacto: "+(a['centro_contacto'] or '')+" - Email: "+(a['email'] or '')
    qr_text=f"CEACGE-{id:04d} | {a['nombre']} {a['apellidos']} | {a['centro_nombre']} | {a['centro_codigo']} | VERIFICAR: ceacge-final.onrender.com/pdf/{id}"
    qr_buf=gen_qr(qr_text)
    c.setFillColor(colors.HexColor("#f1f5f9")); c.rect(0,0,w,52,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0,0,w,3,fill=1,stroke=0)
    c.drawImage(ImageReader(qr_buf), 8, 8, width=36, height=36)
    c.setFillColor(colors.HexColor("#0a2a7a")); c.setFont("Helvetica-Bold",5.2); c.drawString(50,38,"DOCUMENTO OFICIAL - VERIFICACIÓN DIGITAL CON QR")
    c.setFillColor(colors.black); c.setFont("Helvetica",4.2)
    c.drawString(50,30, seguridad[:125]); c.drawString(50,24, seguridad[125:250]); c.drawString(50,16, seguridad[250:375])
    c.setFont("Helvetica-Bold",5.5); c.drawString(50,8,f"Alumno: {a['contacto']} | {a['email']} | COD: CEA-{id:04d}-AA | {a['anio']} | Centro: {a['centro_localidad']} - {a['centro_codigo']}")
    c.showPage(); c.save(); buf.seek(0)
    r=make_response(buf.getvalue()); r.headers['Content-Type']='application/pdf'; r.headers['Content-Disposition']=f'inline; filename=HOJA_V15_{id}.pdf'; return r

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
