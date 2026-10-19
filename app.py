import os, sqlite3, io
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
app.secret_key='V14-FIRMA-PRIMARIA-CENTROS-CURSO-MANUAL'
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
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, hijo_de TEXT, y_de TEXT, fecha_nacimiento TEXT, centro TEXT, localidad TEXT, codigo TEXT, foto TEXT, anio TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT, localidad TEXT, contacto TEXT, email TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cursos_manuales (id SERIAL PRIMARY KEY, nombre TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, foto TEXT, anio TEXT, contacto TEXT, email TEXT, centro_nombre TEXT, centro_codigo TEXT, centro_localidad TEXT, centro_contacto TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, hijo_de TEXT, y_de TEXT, fecha_nacimiento TEXT, centro TEXT, localidad TEXT, codigo TEXT, foto TEXT, anio TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT, localidad TEXT, contacto TEXT, email TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cursos_manuales (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
        try:
            cols=[r[1] for r in cur.execute("PRAGMA table_info(alumnos)").fetchall()]
            for col in ['contacto','email','centro_nombre','centro_codigo','centro_localidad','centro_contacto']:
                if col not in cols: cur.execute(f"ALTER TABLE alumnos ADD COLUMN {col} TEXT")
        except: pass
    cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),('admin',))
    if not cur.fetchone():
        cur.execute(adapt("INSERT INTO usuarios (usuario,password) VALUES (?,?)"),('admin',generate_password_hash('ceacge2025')))
    conn.commit(); conn.close()

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'usuario' not in session: return redirect('/login')
        return f(*a,**kw)
    return dec
def gen_qr(text):
    qr=qrcode.QRCode(box_size=6, border=1); qr.add_data(text); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white").convert('RGB')
    buf=io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0); return buf

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['usuario']; p=request.form['password']
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,)); user=cur.fetchone(); conn.close()
        if user and check_password_hash(user['password'], p):
            session['usuario']=u; return redirect('/')
        return 'Clave mal'
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:linear-gradient(135deg,#0a2a7a,#0a7a4a)"><div style="background:white;padding:30px;border-radius:12px"><h2 style="color:#0a2a7a">CEACGE V14</h2><form method=post><input name=usuario value=admin style="width:100%;padding:10px"><br><br><input type=password name=password placeholder="ceacge2025" style="width:100%;padding:10px"><br><br><button style="width:100%;padding:12px;background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;border:none;border-radius:6px">ENTRAR</button></form></div></body>'

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall()
    cur.execute("SELECT * FROM alumnos_primaria ORDER BY id DESC"); primaria=cur.fetchall()
    cur.execute("SELECT * FROM centros ORDER BY id DESC"); centros=cur.fetchall()
    cur.execute("SELECT * FROM cursos_manuales ORDER BY id DESC"); cursos=cur.fetchall()
    conn.close()
    return render_template_string("""
    <body style="font-family:Arial;background:#f0f5f1;padding:20px">
    <h2 style="color:#0a2a7a">CEACGE V14 - TODO GUARDADO | PDF SOLO AL IMPRIMIR</h2>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:15px">
        <a href='/nuevo' style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:12px 18px;text-decoration:none;border-radius:8px'>+ ALUMNO ESBA/SECUNDARIA</a>
        <a href='/primaria/nuevo' style='background:#0a7a4a;color:white;padding:12px 18px;text-decoration:none;border-radius:8px'>+ ALUMNO PRIMARIA</a>
        <a href='/centros/nuevo' style='background:#0a2a7a;color:white;padding:12px 18px;text-decoration:none;border-radius:8px'>+ CENTRO</a>
        <a href='/cursos/nuevo' style='background:#64748b;color:white;padding:12px 18px;text-decoration:none;border-radius:8px'>+ CURSO MANUAL (RAMA)</a>
        <a href='/logout'>Salir</a>
    </div>

    <h3 style="color:#0a2a7a">a) Alumnos Secundaria y ESBA ({{alumnos|length}})</h3>
    <table border=1 cellpadding=6 style='width:100%;border-collapse:collapse;background:white'><tr style='background:#0a2a7a;color:white'><th>Foto</th><th>Alumno</th><th>Centro</th><th>Acción</th></tr>
    {% for x in alumnos %}<tr><td>{% if x['foto'] %}<img src='/fotos/{{x['foto']}}' width=40>{% endif %}</td><td><b>{{x['nombre']}} {{x['apellidos']}}</b><br><small>{{x['contacto']}} | {{x['email']}}</small></td><td><small>{{x['centro_nombre']}} - {{x['centro_codigo']}}</small></td><td><a href='/notas/{{x['id']}}'>Notas</a> | <a href='/pdf/{{x['id']}}' style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:5px 10px;text-decoration:none;border-radius:5px'>VER PDF</a></td></tr>{% endfor %}</table>

    <h3 style="color:#0a7a4a;margin-top:20px">b) Alumnos Primaria ({{primaria|length}}) - Registro: Nombre, Apellidos, hijo de, y de, Fecha nac., centro, localidad, código</h3>
    <table border=1 cellpadding=6 style='width:100%;border-collapse:collapse;background:white'><tr style='background:#0a7a4a;color:white'><th>Foto</th><th>Alumno Primaria</th><th>Filiación</th><th>Centro</th></tr>
    {% for p in primaria %}<tr><td>{% if p['foto'] %}<img src='/fotos/{{p['foto']}}' width=40>{% endif %}</td><td><b>{{p['nombre']}} {{p['apellidos']}}</b><br><small>Nac: {{p['fecha_nacimiento']}}</small></td><td><small>Hijo de {{p['hijo_de']}} y de {{p['y_de']}}</small></td><td><small>{{p['centro']}} - {{p['localidad']}} - {{p['codigo']}}</small></td></tr>{% endfor %}</table>

    <h3 style="color:#0a2a7a;margin-top:20px">c) Centros ({{centros|length}}) - Nombre, Código, Localidad</h3>
    <table border=1 cellpadding=6 style='width:100%;border-collapse:collapse;background:white'><tr style='background:#0a2a7a;color:white'><th>Nombre Centro</th><th>Código</th><th>Localidad</th><th>Contacto</th></tr>
    {% for c in centros %}<tr><td>{{c['nombre']}}</td><td>{{c['codigo']}}</td><td>{{c['localidad']}}</td><td>{{c['contacto']}} - {{c['email']}}</td></tr>{% endfor %}</table>

    <h3 style="margin-top:20px">Cursos Manuales (RAMA) - {{cursos|length}}</h3>
    <table border=1 cellpadding=6 style='width:100%;border-collapse:collapse;background:white'><tr><th>Curso</th><th>Tipo</th></tr>{% for cu in cursos %}<tr><td>{{cu['nombre']}}</td><td>{{cu['tipo']}}</td></tr>{% endfor %}</table>
    </body>""", alumnos=alumnos, primaria=primaria, centros=centros, cursos=cursos)

@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM centros"); centros_list=cur.fetchall()
    if request.method=='POST':
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; natural=request.form['natural_de']; distrito=request.form['distrito']; provincia=request.form['provincia']; centro=request.form['centro']; foto_file=request.files.get('foto'); contacto=request.form['contacto']; email=request.form['email']
        c_nombre=request.form['centro_nombre']; c_codigo=request.form['centro_codigo']; c_localidad=request.form['centro_localidad']; c_contacto=request.form['centro_contacto']; anio=request.form['anio']
        fn=''
        if foto_file and foto_file.filename:
            fn=secure_filename(foto_file.filename); foto_file.save(os.path.join(UPLOAD_FOLDER, fn))
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio,contacto,email,centro_nombre,centro_codigo,centro_localidad,centro_contacto) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"),(nombre,apellidos,natural,distrito,provincia,centro,fn,anio,contacto,email,c_nombre,c_codigo,c_localidad,c_contacto))
        conn.commit(); cur.execute(adapt("SELECT id FROM alumnos ORDER BY id DESC LIMIT 1")); nid=cur.fetchone()['id']; conn.close(); return redirect(f'/notas/{nid}')
    conn.close()
    options="".join([f"<option value='{c['nombre']}' data-codigo='{c['codigo']}' data-localidad='{c['localidad']}' data-contacto='{c['contacto']}'>{c['nombre']} - {c['codigo']}</option>" for c in centros_list])
    return f"""
    <body style="font-family:Arial;background:#f0f5f1;padding:20px"><h2 style="color:#0a2a7a">NUEVO ALUMNO ESBA/SECUNDARIA - Sin PDF auto</h2>
    <form method=post enctype=multipart/form-data style='background:white;padding:20px;border-radius:12px;max-width:700px;display:flex;flex-direction:column;gap:8px'>
    Nombre:<input name=nombre required> Apellidos:<input name=apellidos required>
    Natural:<input name=natural_de value='VABE' required> Distrito:<input name=distrito value='KOGO' required> Provincia:<input name=provincia value='LITORAL' required>
    Contacto:<input name=contacto placeholder='222...'> E-mail:<input name=email type=email>
    Año:<input name=anio value='2023-2024'> Foto:<input type=file name=foto>
    <h3 style="color:#0a2a7a">Centro</h3>
    <select id='selCentro' onchange="let o=this.options[this.selectedIndex]; document.querySelector('[name=centro_nombre]').value=o.value; document.querySelector('[name=centro_codigo]').value=o.dataset.codigo||''; document.querySelector('[name=centro_localidad]').value=o.dataset.localidad||''; document.querySelector('[name=centro_contacto]').value=o.dataset.contacto||'';">
    <option value=''>-- Elegir centro registrado --</option>{options}</select>
    Nombre centro:<input name=centro_nombre value='IPES PADRE SANTY' required> Código:<input name=centro_codigo value='IPES-007' required> Localidad:<input name=centro_localidad value='BATA' required> Contacto centro:<input name=centro_contacto> Centro resumen:<input name=centro value='PADRE SANTY - BATA'>
    <button style='padding:14px;background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;border:none;border-radius:8px'>GUARDAR EN BD (sin PDF auto)</button></form><a href='/'>Volver</a></body>"""

@app.route('/primaria/nuevo', methods=['GET','POST'])
@login_required
def primaria_nuevo():
    if request.method=='POST':
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; hijo=request.form['hijo_de']; yde=request.form['y_de']; fnac=request.form['fecha_nacimiento']; centro=request.form['centro']; localidad=request.form['localidad']; codigo=request.form['codigo']; anio=request.form['anio']; foto_file=request.files.get('foto'); fname=''
        if foto_file and foto_file.filename:
            fname=secure_filename(foto_file.filename); foto_file.save(os.path.join(UPLOAD_FOLDER, fname))
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,hijo_de,y_de,fecha_nacimiento,centro,localidad,codigo,foto,anio) VALUES (?,?,?,?,?,?,?,?,?,?)"),(nombre,apellidos,hijo,yde,fnac,centro,localidad,codigo,fname,anio)); conn.commit(); conn.close(); return redirect('/')
    return """<body style="font-family:Arial;padding:20px"><h2 style="color:#0a7a4a">NUEVO ALUMNO PRIMARIA</h2><p>Registro: Nombre, Apellidos, hijo de, y de, Fecha nacimiento, centro, localidad, código</p>
    <form method=post enctype=multipart/form-data style='background:white;padding:20px;max-width:600px;display:flex;flex-direction:column;gap:8px'>
    Nombre:<input name=nombre required> Apellidos:<input name=apellidos required> Hijo de:<input name=hijo_de required> Y de:<input name=y_de required> Fecha nacimiento:<input name=fecha_nacimiento type=date required>
    Centro:<input name=centro required> Localidad:<input name=localidad required> Código:<input name=codigo required> Año:<input name=anio value='2023-2024'> Foto:<input type=file name=foto>
    <button style='padding:12px;background:#0a7a4a;color:white;border:none;border-radius:6px'>GUARDAR PRIMARIA EN BD</button></form><a href='/'>Volver</a></body>"""

@app.route('/centros/nuevo', methods=['GET','POST'])
@login_required
def centros_nuevo():
    if request.method=='POST':
        nombre=request.form['nombre']; codigo=request.form['codigo']; localidad=request.form['localidad']; contacto=request.form['contacto']; email=request.form['email']
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email) VALUES (?,?,?,?,?)"),(nombre,codigo,localidad,contacto,email)); conn.commit(); conn.close(); return redirect('/')
    return """<body style="font-family:Arial;padding:20px"><h2 style="color:#0a2a7a">NUEVO CENTRO</h2>
    <form method=post style='background:white;padding:20px;max-width:500px;display:flex;flex-direction:column;gap:8px'>
    a) Nombre del centro:<input name=nombre required placeholder='IPES PADRE SANTY'> b) Código del centro:<input name=codigo required placeholder='IPES-007'> c) Localidad del centro:<input name=localidad required placeholder='BATA'> Contacto:<input name=contacto> Email:<input name=email type=email>
    <button style='padding:12px;background:#0a2a7a;color:white;border:none;border-radius:6px'>GUARDAR CENTRO</button></form><a href='/'>Volver</a></body>"""

@app.route('/cursos/nuevo', methods=['GET','POST'])
@login_required
def cursos_nuevo():
    if request.method=='POST':
        nombre=request.form['nombre']; tipo=request.form['tipo']
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("INSERT INTO cursos_manuales (nombre,tipo) VALUES (?,?)"),(nombre,tipo)); conn.commit(); conn.close(); return redirect('/')
    return """<body style="font-family:Arial;padding:20px"><h2>CURSO MANUAL - Para apartado CURSO en las RAMAS</h2>
    <p>Aquí generas manualmente los cursos que aparecen en el lateral azul CURSO. Ej: 1 ESBA, 2 ESBA, 1 BACH, etc.</p>
    <form method=post style='background:white;padding:20px;max-width:500px;display:flex;flex-direction:column;gap:8px'>
    Nombre curso:<input name=nombre required placeholder='Ej: 3 ESBA o 1 BACH o RAMA DE...'> Tipo:<select name=tipo><option value='ESBA'>ESBA/BACH (azul)</option><option value='RAMA'>RAMA (verde/rojo)</option></select>
    <button style='padding:12px;background:#64748b;color:white;border:none;border-radius:6px'>GUARDAR CURSO MANUAL</button></form><a href='/'>Volver</a></body>"""

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
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(id,))
        for bloque in BLOQUES_IZQ+BLOQUES_DER:
            titulo=bloque[0]; lista=bloque[1]
            for mat in lista:
                o=request.form.get(f"{titulo}__{mat}__o",''); e=request.form.get(f"{titulo}__{mat}__e",'')
                if o or e: cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(id,titulo,mat,o,e))
        conn.commit(); conn.close(); return redirect(f'/')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); db=cur.fetchall(); nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in db}
    cur.execute("SELECT * FROM cursos_manuales"); cursos_man=cur.fetchall(); conn.close()
    h=f"<body style='font-family:Arial;padding:15px'><h2>Notas de {alum['nombre']} - BD (PDF solo al imprimir)</h2><p>Cursos manuales creados: {', '.join([c['nombre'] for c in cursos_man])}</p><form method=post>"
    for bloque in BLOQUES_IZQ+BLOQUES_DER:
        titulo=bloque[0]; lista=bloque[1]
        h+=f"<h4 style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:6px;border-radius:4px'>{titulo} - CURSO editable manual</h4><table border=1 style='width:100%;border-collapse:collapse'>"
        for mat in lista:
            o,e=nm.get((titulo,mat),('','')); h+=f"<tr><td style='width:70%'>{mat}</td><td><input name='{titulo}__{mat}__o' value='{o}' style='width:60px'></td><td><input name='{titulo}__{mat}__e' value='{e}' style='width:60px'></td></tr>"
        h+="</table>"
    h+="<br><button style='padding:15px;background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;width:100%;border:none;border-radius:8px'>GUARDAR NOTAS EN BD (no genera PDF auto)</button></form><br><a href='/'>Volver</a> | <a href='/pdf/{0}'>VER PDF</a></body>".format(id)
    return h

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); nl=cur.fetchall(); conn.close()
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

    # === NUEVO: LINEA DE PUNTA A PUNTA DEBAJO DE TABLAS ===
    linea_y = min(y_left, y_right) - 2
    if linea_y < 95: linea_y = 95
    c.setStrokeColor(colors.HexColor("#0a2a7a")); c.setLineWidth(1.2)
    c.line(8, linea_y, w-8, linea_y)

    # === VB Inspector + Director CEACGE ===
    c.setFont("Helvetica-Bold",8); c.setFillColor(colors.HexColor("#0a2a7a"))
    c.drawString(15, linea_y-14, "VB del Inspector de Educación")
    c.drawString(w*0.55, linea_y-14, "El Director CEACGE")
    c.setFont("Helvetica",6); c.setFillColor(colors.black)
    c.drawString(15, linea_y-24, "Firma y sello")
    c.drawString(w*0.55, linea_y-24, "Firma y sello")

    # TEXTO SEGURIDAD + QR
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
    r=make_response(buf.getvalue()); r.headers['Content-Type']='application/pdf'; r.headers['Content-Disposition']=f'inline; filename=HOJA_V14_{id}.pdf'; return r

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
