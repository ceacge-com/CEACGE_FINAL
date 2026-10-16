import os, sqlite3, base64, urllib.parse
from flask import Flask, request, redirect, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = "CEACGE-FOTO-IZQ-QR-DER-NOMBRE-GRANDE"
UPLOAD_FOLDER = "fotos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

SISTEMA_GE = {
    "1 PRIMARIA": ["Lengua Española","Matemáticas","Conocimiento del Medio","Francés","Inglés","Educación Física","Educación Artística","Religión"],
    "2 PRIMARIA": ["Lengua Española","Matemáticas","Conocimiento del Medio","Francés","Inglés","Educación Física","Educación Artística","Religión"],
    "3 PRIMARIA": ["Lengua Española","Matemáticas","Conocimiento del Medio","Francés","Inglés","Educación Física","Educación Artística","Religión"],
    "4 PRIMARIA": ["Lengua Española","Matemáticas","Conocimiento del Medio","Francés","Inglés","Educación Física","Educación Artística","Religión"],
    "5 PRIMARIA": ["Lengua Española","Matemáticas","Conocimiento del Medio","Francés","Inglés","Educación Física","Educación Artística","Religión","Informática Básica"],
    "6 PRIMARIA": ["Lengua Española","Matemáticas","Conocimiento del Medio","Francés","Inglés","Educación Física","Educación Artística","Religión","Informática Básica"],
    "1 ESBA": ["Lengua Esp. y Lit.","Matemáticas","Geofía Gral. Y","Ciencia Naturales I","E. Plástica y Visual I","Religión","Francés","E. Física","Ingles"],
    "2 ESBA": ["Lengua Esp. y Lit.","Matemáticas","Geofía. Descp. Univ.","Ciencia Naturales II","E. Plástica y Visual II","Religión","Francés","Ingles","E. Física"],
    "3 ESBA": ["Lengua Esp. y Lit.","Matemáticas","Hª. de áfrica y de G.E.","Biología y Geología","Tecnología","E. Plást. y Artística I","Física y Química","Religión","Francés","Ingles","E. Física"],
    "4 ESBA": ["Lengua Esp. y Lit.","Matemáticas","Hª Universal","Física y Química","Tecnología","Biología y Geología","Religión","Francés","Ingles","E. Plástica y Artista","E. Física"],
    "1 BACHILLERATO - RAMA COMÚN": ["Lengua Española","Historia de África y de G.E","Filosofía","Educación Física","Religión","Francés","Ingles","CC. de la Tierra y M","Economia"],
    "1 BACHILLERATO - CIENCIAS NATURALEZA Y SALUD": ["Matemáticas I","Fisica y Química","Dibujo Técnico I","Biología"],
    "1 BACHILLERATO - CIENCIAS SOCIALES Y HUMANIDADES": ["Latin","Griego","Geografía de G. Ecuatorial y Mundial","Matemáticas Aplicadas CCSS I"],
    "1 BACHILLERATO - TECNOLOGÍA": ["Tecnología Industrial I","Matemáticas I","Dibujo Técnico I","Física y Química"],
    "2 BACHILLERATO - RAMA COMÚN": ["Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencias de la Naturaleza","Economia de la Empresa","Religión","Ingles","Francés"],
    "2 BACHILLERATO - CIENCIAS NATURALEZA Y SALUD": ["Matemáticas II","Química","Biología","Geología","Física"],
    "2 BACHILLERATO - TECNOLOGÍA": ["Tecnología Industrial II","Matemáticas II","Electrotecnia","Dibujo Técnico II","Física"],
    "2 BACHILLERATO - HUMANIDADES Y CCSS": ["Matemáticas aplicadas a CCSS II","Historia del Arte","Latin II","Griego II","Geografía"]
}

def get_conn():
    conn = sqlite3.connect("ceacge.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_foto_base64(filename):
    try:
        path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(path): return None
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        mime = "jpeg" if filename.lower().endswith(("jpg","jpeg")) else "png"
        return f"data:image/{mime};base64,{data}"
    except: return None

def init_db():
    conn=get_conn(); cur=conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS escuelas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, codigo TEXT, distrito TEXT)')
    try: cur.execute("ALTER TABLE escuelas ADD COLUMN codigo TEXT")
    except: pass
    try: cur.execute("ALTER TABLE escuelas ADD COLUMN distrito TEXT")
    except: pass
    cur.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, rol TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, nombres TEXT, apellidos TEXT, telefono TEXT, localidad TEXT, distrito_nac TEXT, provincia_nac TEXT, fecha_nacimiento TEXT, escuela_id INTEGER, foto TEXT, antecedente TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, materia TEXT, nota REAL, UNIQUE(alumno_id, curso, materia))')
    cur.execute("SELECT id FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username, password_hash, rol) VALUES (?,?,?)", ("admin", generate_password_hash("ceacge2025"), "admin"))
    cur.execute("SELECT COUNT(*) FROM escuelas")
    if cur.fetchone()[0]==0:
        cur.execute("INSERT INTO escuelas (nombre, codigo, distrito) VALUES (?,?,?)", ("DOCTOR RAFAEL Mª NZÉ ABUY - EBIBEYIN","IPES-DRMNA","EBIBEYIN"))
        cur.execute("INSERT INTO escuelas (nombre, codigo, distrito) VALUES (?,?,?)", ("INES P. SIALO","INES-PS","BATA"))
    conn.commit(); conn.close()

def login_required(f):
    @wraps(f)
    def decorated(*a,**k):
        if 'user_id' not in session: return redirect('/login')
        return f(*a,**k)
    return decorated

def render_page(content):
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<nav class="navbar bg-success px-3"><a class="navbar-brand text-white fw-bold" href="/">🇬🇶 CEACGE</a><div><a href="/alumnos" class="btn btn-sm btn-light me-2">Alumnos</a><a href="/escuelas" class="btn btn-sm btn-warning me-2">Centros</a><a href="/logout" class="btn btn-sm btn-dark">Salir</a></div></nav>
<div class="container mt-4">{content}</div></body></html>"""

@app.route('/fotos/<filename>')
def fotos(filename): return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM usuarios WHERE username=?", (request.form.get('username'),)); u=cur.fetchone(); conn.close()
        if u and check_password_hash(u['password_hash'], request.form.get('password')):
            session['user_id']=u['id']; session['username']=u['username']; return redirect('/')
    return render_page("""<div class="card p-4 text-center" style="max-width:400px;margin:auto"><h3>CEACGE</h3><form method="post"><input class="form-control mb-2" name="username" placeholder="admin"><input class="form-control mb-2" type="password" name="password" placeholder="ceacge2025"><button class="btn btn-success w-100">ENTRAR</button></form></div>""")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT COUNT(*) FROM alumnos"); a=cur.fetchone()[0]; cur.execute("SELECT COUNT(*) FROM escuelas"); e=cur.fetchone()[0]; conn.close()
    return render_page(f"<div class='card p-4'><h3>Bienvenido {session.get('username')}</h3><p>Alumnos: {a} | Centros: {e}</p><a href='/alumnos' class='btn btn-primary me-2'>Ver Alumnos</a><a href='/escuelas' class='btn btn-warning'>Centros</a></div>")

@app.route('/escuelas', methods=['GET','POST'])
@login_required
def escuelas():
    conn=get_conn(); cur=conn.cursor()
    if request.method=='POST':
        try:
            cur.execute("INSERT INTO escuelas (nombre, codigo, distrito) VALUES (?,?,?)", (request.form.get('nombre'), request.form.get('codigo'), request.form.get('distrito')))
            conn.commit()
        except: pass
    cur.execute("SELECT * FROM escuelas ORDER BY id DESC"); lista=cur.fetchall(); conn.close()
    rows="".join([f"<tr><td><b>{e['codigo'] or ''}</b></td><td>{e['nombre']}</td><td>{e['distrito'] or ''}</td></tr>" for e in lista])
    return render_page(f"<div class='card p-4'><h4>Centros - Con Código</h4><table class='table'><tr><th>Código Centro</th><th>Nombre</th><th>Distrito</th></tr>{rows}</table><form method='post' class='row g-2 mt-3'><div class='col-md-3'><input name='codigo' placeholder='Código Ej: IPES-001' class='form-control' required></div><div class='col-md-5'><input name='nombre' placeholder='Nombre del centro' class='form-control' required></div><div class='col-md-2'><input name='distrito' placeholder='Distrito Ej: BATA' class='form-control'></div><div class='col-md-2'><button class='btn btn-warning w-100'>Añadir Centro</button></div></form></div>")

@app.route('/alumnos')
@login_required
def alumnos_list():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT a.*, e.nombre as escuela_nombre, e.codigo as escuela_codigo FROM alumnos a LEFT JOIN escuelas e ON a.escuela_id=e.id ORDER BY a.id DESC"); lista=cur.fetchall(); cur.execute("SELECT * FROM escuelas"); esc=cur.fetchall(); conn.close()
    rows="".join([f"<tr><td><b>{al['codigo']}</b></td><td>{al['nombres']} {al['apellidos']}</td><td>{al['escuela_codigo'] or ''} - {al['escuela_nombre'] or ''}</td><td><a href='/ver_alumno/{al['id']}' class='btn btn-sm btn-success'>Perfil</a> <a href='/notas/{al['id']}' class='btn btn-sm btn-warning'>Notas</a> <a href='/imprimir/{al['id']}' target='_blank' class='btn btn-sm btn-primary'>PDF</a></td></tr>" for al in lista])
    opts="".join([f"<option value='{e['id']}'>{e['codigo'] or ''} - {e['nombre']}</option>" for e in esc])
    return render_page(f"<div class='card p-4'><h4>Alumnos - {len(lista)}</h4><table class='table table-sm'><tr><th>Código Alumno</th><th>Nombre</th><th>Centro</th><th>Acciones</th></tr>{rows}</table><div class='card p-3 mt-4'><h5>Agregar Alumno</h5><form action='/add_alumno' method='post' enctype='multipart/form-data' class='row g-2'><input name='codigo' placeholder='Codigo Alumno' class='form-control col' required><input name='nombres' placeholder='Nombres' class='form-control col' required><input name='apellidos' placeholder='Apellidos' class='form-control col' required><input name='telefono' placeholder='Telefono' class='form-control col'><input name='localidad' placeholder='Natural de' class='form-control col'><input name='distrito_nac' placeholder='Distrito' class='form-control col' value='NSOC-NSOMO'><input name='provincia_nac' placeholder='Provincia' class='form-control col' value='KIÉ-NTEM'><input name='fecha_nacimiento' type='date' class='form-control col'><select name='escuela_id' class='form-control col'><option value=''>Centro</option>{opts}</select><input name='antecedente' placeholder='APTO' class='form-control col'><input type='file' name='foto' class='form-control col'><button class='btn btn-success'>Guardar</button></form></div></div>")

@app.route('/add_alumno', methods=['POST'])
@login_required
def add_alumno():
    fn=None
    if 'foto' in request.files:
        f=request.files['foto']
        if f.filename: fn=secure_filename(f.filename); f.save(os.path.join(UPLOAD_FOLDER, fn))
    conn=get_conn(); cur=conn.cursor()
    cur.execute("INSERT INTO alumnos (codigo, nombres, apellidos, telefono, localidad, distrito_nac, provincia_nac, escuela_id, foto, fecha_nacimiento, antecedente) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(request.form['codigo'], request.form['nombres'], request.form['apellidos'], request.form.get('telefono'), request.form['localidad'], request.form['distrito_nac'], request.form['provincia_nac'], request.form.get('escuela_id'), fn, request.form.get('fecha_nacimiento'), request.form.get('antecedente')))
    conn.commit(); conn.close(); return redirect('/alumnos')

@app.route('/ver_alumno/<int:id>')
@login_required
def ver_alumno(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT a.*, e.nombre as escuela_nombre, e.codigo as escuela_codigo FROM alumnos a LEFT JOIN escuelas e ON a.escuela_id=e.id WHERE a.id=?", (id,)); al=cur.fetchone(); conn.close()
    foto = f"<img src='/fotos/{al['foto']}' style='width:180px;height:220px;object-fit:cover;border-radius:8px'>" if al['foto'] else "Sin foto"
    qr = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(al['codigo'])}"
    return render_page(f"<div class='card p-4'><div class='row'><div class='col-md-3 text-center'>{foto}<br><img src='{qr}' class='mt-2' style='width:120px'><br><small>{al['codigo']}</small></div><div class='col-md-9'><h4>{al['nombres']} {al['apellidos']}</h4><p><b>Código:</b> {al['codigo']}<br><b>Tel:</b> {al['telefono']}<br><b>Fecha Nac:</b> {al['fecha_nacimiento']}<br><b>Lugar:</b> {al['localidad']} - {al['distrito_nac']}/{al['provincia_nac']}<br><b>Centro:</b> {al['escuela_codigo'] or ''} - {al['escuela_nombre']}<br><b>Antecedente:</b> {al['antecedente']}</p><a href='/notas/{al['id']}' class='btn btn-warning'>✏️ Gestionar Notas Completas</a> <a href='/imprimir/{al['id']}' target='_blank' class='btn btn-success'>📄 PDF ESBA+BACH</a></div></div></div>")

@app.route('/notas/<int:id>', methods=['GET','POST'])
@login_required
def notas(id):
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM alumnos WHERE id=?", (id,)); al=cur.fetchone()
    if request.method=='POST':
        for curso, materias in SISTEMA_GE.items():
            for mat in materias:
                key = f"nota__{curso}__{mat}"
                val = request.form.get(key)
                if val not in (None, "", " "):
                    try: cur.execute("INSERT OR REPLACE INTO notas (alumno_id, curso, materia, nota) VALUES (?,?,?,?)", (id, curso, mat, float(val)))
                    except: pass
        conn.commit()
    cur.execute("SELECT curso, materia, nota FROM notas WHERE alumno_id=?", (id,)); existentes=cur.fetchall()
    notas_dict = {(r['curso'], r['materia']): r['nota'] for r in existentes}
    conn.close()
    html_cursos = ""
    for curso, materias in SISTEMA_GE.items():
        color = "#e8f5e9"
        if "PRIMARIA" in curso: color="#e3f2fd"
        elif "ESBA" in curso: color="#fff3e0"
        elif "BACH" in curso: color="#f3e5f5"
        filas = ""
        for mat in materias:
            nota_val = notas_dict.get((curso, mat), "")
            filas += f"<tr><td style='width:60%'>{mat}</td><td><input type='number' step='0.1' min='0' max='10' name='nota__{curso}__{mat}' value='{nota_val}' class='form-control form-control-sm' placeholder='0-10'></td></tr>"
        html_cursos += f"""<div class="card mb-3" style="border-left:5px solid #009e49"><div class="card-header" style="background:{color};font-weight:bold">{curso}</div><div class="card-body p-2"><table class="table table-sm mb-0">{filas}</table></div></div>"""
    return render_page(f"<div class='card p-4'><h4>📚 Sistema Completo - Notas de {al['nombres']} {al['apellidos']} - {al['codigo']}</h4><div class='alert alert-info'>Rellena todo (Primaria a Bach). En el PDF solo se imprimirán ESBA y BACH.</div><form method='post'>{html_cursos}<button class='btn btn-success btn-lg w-100 mt-3'>💾 GUARDAR TODAS LAS NOTAS</button></form><div class='mt-3'><a href='/imprimir/{id}' target='_blank' class='btn btn-primary'>Ver PDF ESBA+BACH</a> <a href='/alumnos' class='btn btn-dark'>Volver</a></div></div>")

@app.route('/imprimir/<int:id>')
@login_required
def imprimir_alumno(id):
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT a.*, e.nombre as escuela_nombre, e.codigo as escuela_codigo FROM alumnos a LEFT JOIN escuelas e ON a.escuela_id=e.id WHERE a.id=?", (id,)); al=cur.fetchone()
    cur.execute("SELECT curso, materia, nota FROM notas WHERE alumno_id=?", (id,)); notas=cur.fetchall()
    conn.close()
    if not al: return "No existe"
    foto_b64=get_foto_base64(al['foto']) if al['foto'] else None
    foto_html = f"<img src='{foto_b64}' style='width:75px;height:95px;object-fit:cover;border:1px solid #000'>" if foto_b64 else "<div style='width:75px;height:95px;border:1px solid #000;display:flex;align-items:center;justify-content:center;font-size:6px;background:white'>FOTO</div>"
    nombre = f"{al['nombres']} {al['apellidos']}".upper()
    centro = (al['escuela_nombre'] or "DOCTOR RAFAEL Mª NZÉ ABUY").upper()
    codigo_centro = (al['escuela_codigo'] or "").upper()
    natural = (al['localidad'] or "").upper()
    distrito = (al['distrito_nac'] or "VABE").upper()
    provincia = (al['provincia_nac'] or "LITORAL").upper()
    fecha = al['fecha_nacimiento'] or "2021-04-02"
    antecedente = al['antecedente'] or "Estudiante excelente"
    nd={}
    for n in notas:
        if n['curso'] not in nd: nd[n['curso']]={}
        nd[n['curso']][n['materia']]=n['nota']
    def get_exact(curso, mat):
        if curso in nd and mat in nd[curso]: return f"<b>{nd[curso][mat]}</b>"
        return ""
    def col_materias(curso):
        return "".join([f"<div style='padding:5px 0;border-bottom:0.3px dotted #a5d6a7;line-height:1.2;font-size:9px;color:#000'>{m}</div>" for m in SISTEMA_GE[curso]])
    def col_notas(curso):
        return "".join([f"<div style='padding:5px 0;border-bottom:0.3px dotted #a5d6a7;line-height:1.2;text-align:center;font-size:9px'>{get_exact(curso, m) or '&nbsp;'}</div>" for m in SISTEMA_GE[curso]])
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=90x90&data={urllib.parse.quote(al['codigo']+' '+nombre)}"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page{{size:A4;margin:2mm 4mm}}
body{{font-family:"Times New Roman",serif;font-size:8px;background:#f4fdf5;margin:0;position:relative}}
.watermark{{position:fixed;top:45%;left:50%;transform:translate(-50%,-50%) rotate(-30deg);font-size:100px;font-weight:900;color:#009e49;opacity:0.06;letter-spacing:12px;z-index:0;pointer-events:none}}
.tit{{text-align:center;font-weight:bold;font-size:10px;color:#0d2a7a;line-height:1.2;margin:0;padding:5px 0}}
.tab{{width:100%;border-collapse:collapse;position:relative;z-index:1;background:rgba(255,255,255,0.92)}}.tab td{{border:0.6px solid #2e7d32;padding:2px 3px;vertical-align:top;font-size:8px}}.tab th{{border:0.6px solid #2e7d32;background:#e8f5e9;font-size:7px;text-align:center;color:#1b5e20}}
.cab-datos{{display:flex;justify-content:space-between;align-items:stretch;background:rgba(255,255,255,0.95);border:0.8px solid #2e7d32;padding:4px;margin-bottom:3px;position:relative;z-index:1}}
.line{{border-bottom:0.8px solid #000;display:inline-block;min-width:30px;text-align:center;font-weight:bold}}
.nombre-grande{{font-size:14px;font-weight:900;color:#000;letter-spacing:0.5px;text-transform:uppercase;text-align:center;margin-bottom:4px;border:1px solid #000;padding:3px;background:#fff}}
@media print{{.no-print{{display:none}}}}
</style></head><body>
<div class="watermark">CEACGE</div>
<div class="no-print" style="text-align:center;padding:4px;background:#eee;z-index:2;position:relative"><button onclick="window.print()" style="padding:6px 12px;background:#009e49;color:white;border:0;border-radius:3px;font-size:10px">🖨️ IMPRIMIR 1 HOJA</button></div>

<div class="tit">REPÚBLICA DE GUINEA ECUATORIAL<br>MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL<br>DELEGACIÓN REGIONAL - BATA<br>IPES "{centro}" [{codigo_centro}]</div>

<div class="cab-datos">
    <div style="text-align:center">{foto_html}<br><span style="font-size:5px">{al['codigo']}</span></div>
    <div style="flex:1;padding:0 8px">
        <div class="nombre-grande">{nombre}</div>
        <div style="font-size:8px;line-height:1.4">
            Natural: <b>{natural}</b> &nbsp; Distrito: <b>{distrito}</b> &nbsp; Prov: <b>{provincia}</b> &nbsp; Nac: <b>{fecha}</b><br>
            Código Alumno: <b>{al['codigo']}</b> &nbsp; Centro: <b>{codigo_centro}</b><br>
            INGRESO: <b>{antecedente}</b> &nbsp; Tel: <b>{al['telefono'] or ''}</b>
        </div>
    </div>
    <div style="text-align:center;background:white;border:0.8px solid #000;padding:2px"><img src="{qr_url}" style="width:70px;height:70px"><br><span style="font-size:5px">{al['codigo']}</span></div>
</div>

<table class="tab">
<tr><th style="width:6%">CURSO</th><th style="width:22%">ASIGNATURAS</th><th style="width:6%">NOTA</th><th style="width:6%">CURSO</th><th style="width:22%">ASIGNATURAS</th><th style="width:6%">NOTA</th><th style="width:6%">CURSO</th><th style="width:20%">ASIGNATURAS</th><th style="width:6%">NOTA</th></tr>
<tr><td>1 ESBA</td><td>{col_materias('1 ESBA')}</td><td>{col_notas('1 ESBA')}</td><td>2 ESBA</td><td>{col_materias('2 ESBA')}</td><td>{col_notas('2 ESBA')}</td><td>3 ESBA</td><td>{col_materias('3 ESBA')}</td><td>{col_notas('3 ESBA')}</td></tr>
<tr><td>4 ESBA</td><td>{col_materias('4 ESBA')}</td><td>{col_notas('4 ESBA')}</td><td>1 BACH COMÚN</td><td>{col_materias('1 BACHILLERATO - RAMA COMÚN')}</td><td>{col_notas('1 BACHILLERATO - RAMA COMÚN')}</td><td>1 BACH NAT</td><td>{col_materias('1 BACHILLERATO - CIENCIAS NATURALEZA Y SALUD')}</td><td>{col_notas('1 BACHILLERATO - CIENCIAS NATURALEZA Y SALUD')}</td></tr>
<tr><td>1 BACH SOC</td><td>{col_materias('1 BACHILLERATO - CIENCIAS SOCIALES Y HUMANIDADES')}</td><td>{col_notas('1 BACHILLERATO - CIENCIAS SOCIALES Y HUMANIDADES')}</td><td>1 BACH TEC</td><td>{col_materias('1 BACHILLERATO - TECNOLOGÍA')}</td><td>{col_notas('1 BACHILLERATO - TECNOLOGÍA')}</td><td>2 BACH COMÚN</td><td>{col_materias('2 BACHILLERATO - RAMA COMÚN')}</td><td>{col_notas('2 BACHILLERATO - RAMA COMÚN')}</td></tr>
<tr><td>2 BACH NAT</td><td>{col_materias('2 BACHILLERATO - CIENCIAS NATURALEZA Y SALUD')}</td><td>{col_notas('2 BACHILLERATO - CIENCIAS NATURALEZA Y SALUD')}</td><td>2 BACH TEC</td><td>{col_materias('2 BACHILLERATO - TECNOLOGÍA')}</td><td>{col_notas('2 BACHILLERATO - TECNOLOGÍA')}</td><td>2 BACH HUM</td><td>{col_materias('2 BACHILLERATO - HUMANIDADES Y CCSS')}</td><td>{col_notas('2 BACHILLERATO - HUMANIDADES Y CCSS')}</td></tr>
</table>
<div style="margin-top:2px;font-size:7px;position:relative;z-index:1;background:rgba(255,255,255,0.9);padding:3px;border:0.8px solid #c8e6c9">CERTIFICO: Exactitud de datos. Centro Código: {codigo_centro} - Bata a ___ de ___________ de 20__<div style="display:flex;justify-content:space-between;margin-top:5px;text-align:center"><div>DIRECTOR<br><br>__________________</div><div>JEFE ESTUDIOS<br><br>__________________</div><div>SECRETARIO<br><br>__________________</div></div></div>
</body></html>"""

if __name__=='__main__': init_db(); app.run(debug=True, host='0.0.0.0', port=5000)