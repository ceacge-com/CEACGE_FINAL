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
app.secret_key='V17-AZUL-GRANADA-VERDE-ROJO-FIX'
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
        if session.get('rol')!='admin': return "Solo admin <a href='/'>Volver</a>"
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
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,)); user=cur.fetchone()
        if user and p and check_password_hash(user['password'], p):
            session['usuario']=user['usuario']; session['rol']=user['rol'] or 'admin'; session['centro_codigo']=user['centro_codigo']; conn.close(); return redirect('/')
        cur.execute(adapt("SELECT * FROM centros WHERE codigo_acceso=?"),(u,)); centro=cur.fetchone()
        if centro:
            session['usuario']=centro['nombre']; session['rol']='centro'; session['centro_codigo']=centro['codigo']; conn.close(); return redirect('/')
        conn.close(); return 'Código mal <a href=/login>volver</a>'
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:linear-gradient(135deg,#0a2a7a,#0a7a4a)"><div style="background:white;padding:30px;border-radius:12px"><h2>CEACGE V17</h2><form method=post><input name=usuario placeholder="admin o CODIGO CENTRO" style="width:100%;padding:10px" required><br><br><input type=password name=password placeholder="password" style="width:100%;padding:10px"><br><br><button style="width:100%;padding:12px;background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;border:none">ENTRAR</button></form></div></body>'

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
    return render_template_string("""
    <body style="font-family:Arial;background:#f0f5f1;padding:15px"><b>{{session['usuario']}} ({{rol}})</b> - <a href='/logout'>Salir</a>
    <h2 style="color:#0a2a7a">V17 - OFICIAL CON COLORES CORREGIDOS</h2>
    <a href='/nuevo' style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:10px;text-decoration:none;border-radius:6px'>+ ESBA/BACH</a>
    <a href='/primaria/nuevo' style='background:#0a7a4a;color:white;padding:10px;text-decoration:none;border-radius:6px'>+ PRIMARIA</a>
    {% if rol=='admin' %}<a href='/centros/nuevo' style='background:#0a2a7a;color:white;padding:10px;text-decoration:none;border-radius:6px'>+ CENTRO</a>{% endif %}
    <h3>Secundaria ({{alumnos|length}})</h3>
    <table border=1 cellpadding=5 style='width:100%;background:white;border-collapse:collapse'><tr style='background:#0a2a7a;color:white'><th>Foto</th><th>Alumno</th><th>Centro</th><th>Acción</th></tr>
    {% for x in alumnos %}<tr><td>{% if x['foto'] %}<img src='/fotos/{{x['foto']}}' width=35>{% endif %}</td><td>{{x['nombre']}} {{x['apellidos']}}</td><td>{{x['centro_codigo']}}</td><td><a href='/alumnos/{{x['id']}}/ver' style='background:#e0f2fe;padding:4px 8px;border-radius:4px;text-decoration:none'>VER</a> <a href='/alumnos/{{x['id']}}/editar' style='background:#fef3c7;padding:4px 8px;border-radius:4px;text-decoration:none'>EDITAR</a> <a href='/notas/{{x['id']}}'>Notas</a> <a href='/pdf/{{x['id']}}' style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:4px 8px;text-decoration:none;border-radius:4px'>PDF OFICIAL</a></td></tr>{% endfor %}</table>
    <h3>Primaria ({{primaria|length}})</h3>
    <table border=1 cellpadding=5 style='width:100%;background:white;border-collapse:collapse'>{% for p in primaria %}<tr><td>{{p['nombre']}} {{p['apellidos']}}</td><td><a href='/primaria/{{p['id']}}/ver'>VER</a> <a href='/primaria/{{p['id']}}/editar'>EDITAR</a></td></tr>{% endfor %}</table>
    <h3>Centros ({{centros|length}})</h3>
    <table border=1 cellpadding=5 style='width:100%;background:white;border-collapse:collapse'>{% for c in centros %}<tr><td>{{c['nombre']}} - {{c['codigo']}}</td><td><code>{{c['codigo_acceso']}}</code></td><td><a href='/centros/{{c['id']}}/ver'>VER</a> <a href='/centros/{{c['id']}}/generar_codigo'>Código</a></td></tr>{% endfor %}</table>
    </body>""", alumnos=alumnos, primaria=primaria, centros=centros, rol=rol, session=session)

# RUTAS VER/EDITAR SIMPLES
@app.route('/alumnos/<int:id>/ver')
@login_required
def alumno_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone(); conn.close()
    return render_template_string("<body style='font-family:Arial;padding:20px'><a href='/'>Volver</a><h2>{{a['nombre']}} {{a['apellidos']}}</h2><p>{{a['natural_de']}} - {{a['distrito']}} - {{a['provincia']}}</p><p>{{a['centro_nombre']}} - {{a['centro_codigo']}}</p><p>Contacto: {{a['contacto']}} Email: {{a['email']}}</p><a href='/alumnos/{{a['id']}}/editar'>EDITAR</a> | <a href='/pdf/{{a['id']}}'>PDF OFICIAL</a></body>", a=a)

@app.route('/alumnos/<int:id>/editar', methods=['GET','POST'])
@login_required
def alumno_editar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("UPDATE alumnos SET nombre=?,apellidos=?,natural_de=?,distrito=?,provincia=?,contacto=?,email=?,centro_nombre=?,centro_codigo=?,centro_localidad=?,centro_contacto=?,anio=? WHERE id=?"),(request.form['nombre'],request.form['apellidos'],request.form['natural_de'],request.form['distrito'],request.form['provincia'],request.form['contacto'],request.form['email'],request.form['centro_nombre'],request.form['centro_codigo'],request.form['centro_localidad'],request.form['centro_contacto'],request.form['anio'],id))
        conn.commit(); conn.close(); return redirect('/')
    conn.close()
    return render_template_string("<body style='font-family:Arial;padding:20px'><h2>Editar {{a['nombre']}}</h2><form method=post>Nombre:<input name=nombre value='{{a['nombre']}}'><br>Apellidos:<input name=apellidos value='{{a['apellidos']}}'><br>Natural:<input name=natural_de value='{{a['natural_de']}}'><br>Distrito:<input name=distrito value='{{a['distrito']}}'><br>Provincia:<input name=provincia value='{{a['provincia']}}'><br>Contacto:<input name=contacto value='{{a['contacto']}}'><br>Email:<input name=email value='{{a['email']}}'><br>Centro:<input name=centro_nombre value='{{a['centro_nombre']}}'><br>Codigo:<input name=centro_codigo value='{{a['centro_codigo']}}'><br>Localidad:<input name=centro_localidad value='{{a['centro_localidad']}}'><br>Contacto centro:<input name=centro_contacto value='{{a['centro_contacto']}}'><br>Año:<input name=anio value='{{a['anio']}}'><br><button>Guardar</button></form></body>", a=a)

@app.route('/primaria/<int:id>/ver')
@login_required
def primaria_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"),(id,)); p=cur.fetchone(); conn.close()
    return render_template_string("<body><a href='/'>Volver</a><h2>{{p['nombre']}} {{p['apellidos']}}</h2><p>Hijo de {{p['hijo_de']}} y {{p['y_de']}}</p></body>", p=p)

@app.route('/primaria/<int:id>/editar', methods=['GET','POST'])
@login_required
def primaria_editar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"),(id,)); p=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("UPDATE alumnos_primaria SET nombre=?,apellidos=?,hijo_de=?,y_de=?,fecha_nacimiento=?,centro=?,localidad=?,codigo=?,anio=? WHERE id=?"),(request.form['nombre'],request.form['apellidos'],request.form['hijo_de'],request.form['y_de'],request.form['fecha_nacimiento'],request.form['centro'],request.form['localidad'],request.form['codigo'],request.form['anio'],id)); conn.commit(); conn.close(); return redirect('/')
    conn.close()
    return render_template_string("<body><form method=post><input name=nombre value='{{p['nombre']}}'><input name=apellidos value='{{p['apellidos']}}'><button>Guardar</button></form></body>", p=p)

@app.route('/centros/<int:id>/ver')
@login_required
def centro_ver(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM centros WHERE id=?"),(id,)); c=cur.fetchone(); conn.close()
    return render_template_string("<body><a href='/'>Volver</a><h2>{{c['nombre']}} {{c['codigo']}}</h2><p>Localidad: {{c['localidad']}}</p><p>Cod Acceso: {{c['codigo_acceso']}}</p><a href='/centros/{{c['id']}}/generar_codigo'>Generar nuevo código</a></body>", c=c)

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
    return f"<body><h2>Código nuevo para {centro['nombre']}: {nuevo}</h2><a href='/'>Volver</a></body>"

@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor(); foto=request.files.get('foto'); fn=''
        if foto and foto.filename: fn=secure_filename(foto.filename); foto.save(os.path.join(UPLOAD_FOLDER, fn))
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio,contacto,email,centro_nombre,centro_codigo,centro_localidad,centro_contacto) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"),(request.form['nombre'],request.form['apellidos'],request.form['natural_de'],request.form['distrito'],request.form['provincia'],request.form['centro'],fn,request.form['anio'],request.form['contacto'],request.form['email'],request.form['centro_nombre'],request.form['centro_codigo'],request.form['centro_localidad'],request.form['centro_contacto']))
        conn.commit(); cur.execute(adapt("SELECT id FROM alumnos ORDER BY id DESC LIMIT 1")); nid=cur.fetchone()['id']; conn.close(); return redirect(f'/notas/{nid}')
    return "<body><h2>Nuevo ESBA</h2><form method=post enctype=multipart/form-data>Nombre:<input name=nombre required><br>Apellidos:<input name=apellidos required><br>Natural:<input name=natural_de value=VABE><br>Distrito:<input name=distrito value=KOGO><br>Provincia:<input name=provincia value=LITORAL><br>Contacto:<input name=contacto><br>Email:<input name=email><br>Centro nombre:<input name=centro_nombre value='IPES PADRE SANTY' required><br>Codigo:<input name=centro_codigo value='IPES-007' required><br>Localidad:<input name=centro_localidad value=BATA><br>Contacto centro:<input name=centro_contacto><br>Centro resumen:<input name=centro value='PADRE SANTY - BATA'><br>Año:<input name=anio value='2023-2024'><br>Foto:<input type=file name=foto><br><button>Guardar</button></form></body>"

@app.route('/primaria/nuevo', methods=['GET','POST'])
@login_required
def primaria_nuevo():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,hijo_de,y_de,fecha_nacimiento,centro,localidad,codigo,anio,centro_codigo) VALUES (?,?,?,?,?,?,?,?,?,?)"),(request.form['nombre'],request.form['apellidos'],request.form['hijo_de'],request.form['y_de'],request.form['fecha_nacimiento'],request.form['centro'],request.form['localidad'],request.form['codigo'],request.form['anio'],request.form['centro_codigo']))
        conn.commit(); conn.close(); return redirect('/')
    return "<body><h2>Nuevo Primaria</h2><form method=post>Nombre:<input name=nombre><br>Apellidos:<input name=apellidos><br>Hijo de:<input name=hijo_de><br>Y de:<input name=y_de><br>Fecha:<input name=fecha_nacimiento type=date><br>Centro:<input name=centro><br>Localidad:<input name=localidad><br>Codigo:<input name=codigo><br>Centro_codigo:<input name=centro_codigo><br>Año:<input name=anio value='2023-2024'><br><button>Guardar</button></form></body>"

@app.route('/centros/nuevo', methods=['GET','POST'])
@login_required
@admin_required
def centros_nuevo():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor(); codigo_acceso=generar_codigo()
        cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email,codigo_acceso) VALUES (?,?,?,?,?,?)"),(request.form['nombre'],request.form['codigo'],request.form['localidad'],request.form['contacto'],request.form['email'],codigo_acceso))
        cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"),(request.form['codigo'],generate_password_hash(codigo_acceso),'centro',request.form['codigo']))
        conn.commit(); conn.close(); return redirect('/')
    return "<body><h2>Nuevo Centro</h2><form method=post>Nombre:<input name=nombre><br>Codigo:<input name=codigo><br>Localidad:<input name=localidad><br>Contacto:<input name=contacto><br>Email:<input name=email><br><button>Guardar + Código</button></form></body>"

# BLOQUES EXACTOS DE TU HOJA OFICIAL (como en tu PDF)
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
    h=f"<body style='font-family:Arial;padding:15px'><h2>Notas {alum['nombre']} {alum['apellidos']}</h2><form method=post>"
    for bloque in BLOQUES_IZQ+BLOQUES_DER:
        titulo=bloque[0]; lista=bloque[1]
        h+=f"<h4 style='background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;padding:6px'>{titulo}</h4><table border=1 style='width:100%;border-collapse:collapse'>"
        for mat in lista:
            o,e=nm.get((titulo,mat),('','')); h+=f"<tr><td>{mat}</td><td><input name='{titulo}__{mat}__o' value='{o}' style='width:50px'></td><td><input name='{titulo}__{mat}__e' value='{e}' style='width:50px'></td></tr>"
        h+="</table>"
    h+="<br><button style='padding:15px;background:linear-gradient(90deg,#0a2a7a,#0a7a4a);color:white;width:100%;border:none'>GUARDAR NOTAS</button></form></body>"
    return h

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); nl=cur.fetchall(); conn.close()
    nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in nl}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    ROW_H=13.2; FONT_SIZE=7.5

    # === FONDO AZUL GRANADA + VERDE como pediste ===
    c.setFillColor(colors.HexColor("#f5f3ef")); c.rect(0,0,w,h,fill=1,stroke=0)
    # Cabecera azul granada
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0,h-30,w,30,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#0a7a4a")); c.rect(w*0.62,h-30,w*0.38,30,fill=1,stroke=0)

    # === TEXTO REPUBLICA - que faltaba ===
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6.5)
    c.drawString(8, h-12, "REPÚBLICA DE GUINEA ECUATORIAL")
    c.drawString(8, h-20, "MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")

    # NOMBRE EN ROJO como pediste
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",14)
    c.drawString(12, h-48, f"{a['nombre']} {a['apellidos']}".upper())

    # NATURAL
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",7)
    c.drawString(12, h-60, f"NATURAL DE {a['natural_de']}, DEL DISRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']}".upper())

    # IPES EN ROJO como pediste
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",10)
    c.drawString(12, h-74, f"IPES \"{a['centro_nombre'] or a['centro']} - {a['centro_localidad'] or 'BATA'}.".upper())

    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",11)
    c.drawString(12, h-88, "HOJA ACADÉMICA")

    c.setFont("Helvetica",7); c.drawString(12, h-100, f"AÑO ESCOLAR: {a['anio']}")

    # Foto
    xf=w-65; yf=h-95
    c.setFillColor(colors.white); c.setStrokeColor(colors.black); c.setLineWidth(1.5)
    c.rect(xf, yf, 52, 66, fill=1, stroke=1)
    c.setFont("Helvetica",7); c.drawCentredString(xf+26, yf+30, "FOTO")
    fp=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(fp):
        try: c.drawImage(ImageReader(fp), xf+1, yf+1, 50, 64, preserveAspectRatio=True)
        except: pass

    def draw_block(x, y_top, bw, titulo, materias, is_roja):
        GAP = 10
        total_h = len(materias)*ROW_H + 13
        # Etiqueta CURSO vertical (izquierda)
        c.setFillColor(colors.HexColor("#c8c5b8")); c.rect(x, y_top-total_h, 16, total_h, fill=1, stroke=0)
        c.saveState(); c.translate(x+8, y_top-total_h/2); c.rotate(90)
        c.setFillColor(colors.black); c.setFont("Helvetica-Bold",6)
        c.drawCentredString(0,0, "CURSO........." if "ESBA" in titulo or "BACH" in titulo else titulo[:10])
        c.restoreState()
        # Título
        if is_roja:
            c.setFillColor(colors.HexColor("#ffe0e0")); c.rect(x+16, y_top-11, bw-16, 11, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",5.5)
            c.drawString(x+18, y_top-7.5, titulo)
            y = y_top-11
        else:
            c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(x+16, y_top-11, bw-16, 11, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6)
            c.drawString(x+18, y_top-7.5, titulo)
            y = y_top-11

        yy=y
        for mat in materias:
            bx = x+16
            bw_mat = bw-16-44
            # fondo gris claro
            c.setFillColor(colors.HexColor("#f1f1f1")); c.rect(bx, yy-ROW_H, bw_mat, ROW_H, fill=1, stroke=0)
            c.setStrokeColor(colors.black); c.setLineWidth(0.5)
            c.rect(bx, yy-ROW_H, bw_mat, ROW_H, fill=0, stroke=1)
            c.rect(bx+bw_mat, yy-ROW_H, 22, ROW_H, fill=0, stroke=1)
            c.rect(bx+bw_mat+22, yy-ROW_H, 22, ROW_H, fill=0, stroke=1)
            c.setFillColor(colors.black); c.setFont("Helvetica", FONT_SIZE-0.5)
            c.drawString(bx+2, yy-ROW_H+3.5, mat[:36])
            o,e = nm.get((titulo,mat),('',''))
            c.setFont("Helvetica-Bold", FONT_SIZE)
            c.drawCentredString(bx+bw_mat+11, yy-ROW_H+3.5, o)
            c.drawCentredString(bx+bw_mat+33, yy-ROW_H+3.5, e)
            yy-=ROW_H
        return yy - GAP

    x_left=8; bw_col=(w-24)/2
    y_left=h-115
    for tit,mats in [(BLOQUES_IZQ[0][0],BLOQUES_IZQ[0][1]), (BLOQUES_IZQ[1][0],BLOQUES_IZQ[1][1]), (BLOQUES_IZQ[2][0],BLOQUES_IZQ[2][1]), (BLOQUES_IZQ[3][0],BLOQUES_IZQ[3][1])]:
        y_left=draw_block(x_left, y_left, bw_col, tit, mats, False)

    x_right=w/2+4; y_right=h-115
    for tit,mats,is_roja in BLOQUES_DER:
        y_right=draw_block(x_right, y_right, bw_col, tit, mats, is_roja)

    # LINEA FIRMA
    linea_y = min(y_left, y_right) - 6
    if linea_y < 85: linea_y = 85
    c.setStrokeColor(colors.black); c.setLineWidth(0.8); c.line(8, linea_y, w-8, linea_y)
    c.setFont("Helvetica-Bold",7); c.drawString(15, linea_y-12, "VB del Inspector de Educación")
    c.drawString(w*0.55, linea_y-12, "El Director CEACGE")

    # === TEXTO SEGURIDAD QUE FALTABA ===
    seguridad1 = "Cualquiera que intente falsificar o duplicar este documento academico, estara incurriendo en un delito de 'de falsificacion'."
    seguridad2 = "Los antecedentes de esta Hoja Academica, estan registrados en una base de Datos Nacional de Guinea Ecuatorial."
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica",6)
    c.drawString(12, 52, seguridad1)
    c.drawString(12, 44, seguridad2)

    # QR y COD
    qr_text=f"CEACGE-{id:04d} | {a['nombre']} {a['apellidos']} | {a['centro_codigo']} | ceacge-final.onrender.com/pdf/{id}"
    qr_buf=gen_qr(qr_text)
    c.drawImage(ImageReader(qr_buf), 8, 8, width=32, height=32)
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",7)
    c.drawString(w-90, 16, f"COD: CEA-{id:04d}-AA")
    c.setFont("Helvetica",5.5); c.drawString(45, 18, f"Alumno: {a['contacto']} | {a['email']} | {a['anio']} | Verificar QR")
    c.showPage(); c.save(); buf.seek(0)
    r=make_response(buf.getvalue()); r.headers['Content-Type']='application/pdf'; r.headers['Content-Disposition']=f'inline; filename=HOJA_OFICIAL_{id}.pdf'; return r

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
