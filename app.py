import os, secrets, io, base64
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'CEACGE-V24-FINAL-FIX'
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, "fotos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_PG = DATABASE_URL and 'postgres' in DATABASE_URL

PLAN = {
    "1 ESBA": ["Lengua Espanola","Matematicas","Ciencias Sociales","Ciencias Naturales","Ingles","Frances","Educacion Fisica","Musica","Dibujo","Religion/Etica"],
    "2 ESBA": ["Lengua Espanola","Matematicas","Historia","Geografia","Biologia","Fisica y Quimica","Ingles","Frances","Ed. Fisica","Tecnologia"],
    "3 ESBA": ["Lengua y Literatura","Matematicas","Historia de GE y Africa","Biologia","Fisica","Quimica","Ingles","Frances","Filosofia","Ed. Fisica","Informatica"],
    "4 ESBA": ["Lengua y Literatura","Matematicas","Historia Contemporanea","Biologia","Fisica","Quimica","Ingles","Frances","Filosofia","Economia","Informatica"],
    "1 BACH - Ciencias": ["Lengua y Literatura","Matematicas I","Fisica","Quimica","Biologia","Ingles","Filosofia","Ed. Fisica","Informatica"],
    "1 BACH - Letras": ["Lengua y Literatura","Historia del Mundo","Filosofia","Literatura Universal","Ingles","Frances","Geografia Humana","Economia","Latin"],
    "1 BACH - Tecnico": ["Lengua y Literatura","Matematicas Aplicadas","Contabilidad","Economia de Empresa","Informatica de Gestion","Ingles","Filosofia","Tecnologia Industrial"],
    "2 BACH - Ciencias": ["Lengua y Literatura","Matematicas II","Fisica II","Quimica II","Biologia II","Ingles II","Historia de GE","Filosofia II"],
    "2 BACH - Letras": ["Lengua y Literatura II","Historia de GE","Filosofia II","Literatura Espanola","Ingles II","Latin II","Geografia de GE","Historia del Arte"],
    "2 BACH - Tecnico": ["Matematicas Financieras","Contabilidad II","Informatica II","Economia y Organizacion","Derecho Empresarial","Ingles II","Historia de GE","Proyecto Final"]
}

SELECTIVIDAD = {
    "Fase General": ["Lengua Espanola", "Historia", "Historia de la Filosofia", "Idioma (Ingles/Frances)"],
    "LETRAS Y CCSS / HUMANIDADES": ["Historia de Africa y de G.E", "Literatura Universal", "Historia de Arte", "Geografia", "Matematicas Aplicadas a CS", "Latin", "Griego"],
    "CIENCIAS Y TECNOLOGIA": ["Matematicas", "Fisica", "Quimica", "Dibujo Tecnico", "Informatica", "Tecnologia Industrial", "Electrotecnia"],
    "CIENCIAS DE LA NATURALEZA Y SALUD": ["Biologia y Geologia", "C.N y Salud", "Fisica y Quimica"]
}

def get_conn():
    if USE_PG:
        import psycopg2, psycopg2.extras
        url = DATABASE_URL.replace('postgres://','postgresql://',1) if DATABASE_URL.startswith('postgres://') else DATABASE_URL
        return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        import sqlite3
        conn = sqlite3.connect(os.path.join(basedir, "ceacge.db"))
        conn.row_factory = sqlite3.Row
        return conn

def adapt(q): return q.replace('?','%s') if USE_PG else q
def gen_codigo(p): 
    import datetime
    return f"{p}-{datetime.datetime.now().strftime('%H%M%S')}-{secrets.token_hex(2).upper()}"
def gen_qr(txt):
    try:
        import qrcode
        img = qrcode.make(txt)
        b = io.BytesIO(); img.save(b, format='PNG')
        return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
    except:
        import urllib.parse
        return f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(txt)}"

def init_db():
    conn=get_conn(); cur=conn.cursor()
    try:
        if USE_PG:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, alumno_codigo TEXT, asignatura TEXT, nota TEXT, periodo TEXT, observaciones TEXT, centro_codigo TEXT, curso TEXT, rama TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas_trimestres (id SERIAL PRIMARY KEY, alumno_codigo TEXT UNIQUE, curso TEXT, datos TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS selectividad (id SERIAL PRIMARY KEY, alumno_codigo TEXT, fase TEXT, asignatura TEXT, nota TEXT, convocatoria TEXT, centro_codigo TEXT)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, alumno_codigo TEXT, asignatura TEXT, nota TEXT, periodo TEXT, observaciones TEXT, centro_codigo TEXT, curso TEXT, rama TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas_trimestres (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_codigo TEXT UNIQUE, curso TEXT, datos TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS selectividad (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_codigo TEXT, fase TEXT, asignatura TEXT, nota TEXT, convocatoria TEXT, centro_codigo TEXT)")
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
        if not cur.fetchone():
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
        conn.commit()
    except Exception as e: print(e)
    finally:
        try: cur.close(); conn.close()
        except: pass
init_db()

BASE = "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CEACGE</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body><nav class='navbar navbar-dark bg-primary'><div class='container'><a class='navbar-brand' href='/dashboard'>CEACGE V24</a><div><a href='/dashboard' class='btn btn-sm btn-warning me-2'>Menu</a><a href='/consulta' class='btn btn-sm btn-light me-2'>Consulta</a><span class='text-white me-2'>{{session.usuario}} ({{session.rol}})</span><a href='/logout' class='text-white'>Salir</a></div></div></nav><div class='container mt-4'>{{content|safe}}</div></body></html>"

@app.route('/')
def index(): return redirect('/dashboard' if 'usuario' in session else '/login')
@app.route('/login', methods=['GET','POST'])
def login():
    err=None
    if request.method=='POST':
        u=request.form.get('usuario','').strip(); p=request.form.get('password','')
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), (u,)); row=cur.fetchone()
        try: cur.close(); conn.close()
        except: pass
        if row:
            pw=row['password'] if isinstance(row,dict) else row[2]
            if check_password_hash(pw,p):
                session['usuario']=row['usuario'] if isinstance(row,dict) else row[1]
                session['rol']=row['rol'] if isinstance(row,dict) else row[3]
                session['centro_codigo']=row['centro_codigo'] if isinstance(row,dict) else row[4]
                return redirect('/dashboard')
        err="Usuario incorrecto"
    return render_template_string("<html><head><meta charset='utf-8'><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body class='bg-light'><div class='container d-flex justify-content-center align-items-center vh-100'><div class='card p-4' style='width:360px'><h4 class='text-center'>CEACGE V24</h4>{% if err %}<div class='alert alert-danger'>{{err}}</div>{% endif %}<form method='post'><input class='form-control mb-2' name='usuario' placeholder='Usuario' required><input class='form-control mb-3' type='password' name='password' placeholder='Pass' required><button class='btn btn-primary w-100'>Entrar</button></form><hr><a href='/consulta' class='btn btn-outline-secondary w-100'>Consulta por Codigo</a></div></div></body></html>", err=err)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM alumnos"); sec=cur.fetchone(); sec=list(sec.values())[0] if USE_PG else sec[0]
        cur.execute("SELECT COUNT(*) FROM alumnos_primaria"); pri=cur.fetchone(); pri=list(pri.values())[0] if USE_PG else pri[0]
        cur.execute("SELECT COUNT(*) FROM centros"); cen=cur.fetchone(); cen=list(cen.values())[0] if USE_PG else cen[0]
    except: sec=pri=cen=0
    finally:
        try: cur.close(); conn.close()
        except: pass
    return render_template_string(BASE, content=f"<h3>Panel {session['usuario']}</h3><div class='row g-3 mt-2'><div class='col-md-4'><div class='card p-3'><h5>Secundaria y Bachillerato</h5><h2>{sec}</h2><a href='/alumnos' class='btn btn-primary btn-sm'>Ver Listado</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Primaria</h5><h2>{pri}</h2><a href='/primaria' class='btn btn-success btn-sm'>Ver</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Centros</h5><h2>{cen}</h2><a href='/centros' class='btn btn-warning btn-sm'>Ver</a></div></div></div><div class='mt-4'><a href='/alumnos/nuevo' class='btn btn-primary'>+ Sec/Bach</a> <a href='/primaria/nuevo' class='btn btn-success'>+ Primaria</a> <a href='/centros/nuevo' class='btn btn-warning'>+ Centro</a> <a href='/usuarios' class='btn btn-dark'>Usuarios</a></div>")

@app.route('/alumnos')
def alumnos():
    if 'usuario' not in session: return redirect('/login')
    q=request.args.get('q',''); conn=get_conn(); cur=conn.cursor()
    if q: cur.execute(adapt("SELECT * FROM alumnos WHERE codigo_alumno LIKE ? OR nombre LIKE ? ORDER BY id DESC"), (f"%{q}%", f"%{q}%"))
    else: cur.execute("SELECT * FROM alumnos ORDER BY id DESC")
    rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html=f"<div class='d-flex justify-content-between'><h4>Secundaria y Bach <a href='/alumnos/nuevo' class='btn btn-sm btn-primary'>+ Nuevo</a></h4><a href='/dashboard' class='btn btn-sm btn-secondary'>Volver al Menu Principal</a></div><form class='mb-2 mt-2'><input name='q' value='{q}' class='form-control' style='max-width:300px;display:inline-block' placeholder='Buscar'><button class='btn btn-secondary'>Buscar</button></form><table class='table table-hover'><tr><th>Codigo</th><th>Nombre</th><th>Centro</th><th>Accion</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'centro':r[8],'codigo_alumno':r[10],'centro_codigo':r[12]}
        html+=f"<tr><td><b>{d['codigo_alumno']}</b></td><td>{d['nombre']} {d['apellidos']}</td><td>{d['centro']} ({d['centro_codigo']})</td><td><div class='btn-group'><a href='/alumno/{d['id']}' class='btn btn-sm btn-primary'>Ver/Notas</a><a href='/alumno/{d['id']}/editar' class='btn btn-sm btn-warning'>Editar</a><a href='/alumno/{d['id']}/selectividad' class='btn btn-sm btn-dark'>Selectividad</a></div></td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)

@app.route('/alumnos/nuevo', methods=['GET','POST'])
def alumno_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        f=request.form
        codigo_bruto = f.get('codigo_alumno','').strip()
        codigo = codigo_bruto if codigo_bruto else gen_codigo("SEC")
        foto_name=None
        if 'foto' in request.files:
            up=request.files['foto']
            if up.filename:
                foto_name=secure_filename(f"{codigo}_{up.filename}")
                try:
                    from PIL import Image
                    im=Image.open(up); im.thumbnail((800,800)); im.save(os.path.join(UPLOAD_FOLDER, foto_name), optimize=True, quality=80)
                except:
                    up.save(os.path.join(UPLOAD_FOLDER, foto_name))
        cc=session.get('centro_codigo') if session.get('rol')!='admin' else f.get('centro_codigo') or f.get('centro')
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,lugar_nacimiento,distrito,provincia,telefono,email,centro,anio,codigo_alumno,foto,centro_codigo,curso) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"), (f.get('nombre'),f.get('apellidos'),f.get('lugar_nacimiento'),f.get('distrito'),f.get('provincia'),f.get('telefono'),f.get('email'),f.get('centro'),f.get('anio'),codigo,foto_name,cc,f.get('curso')))
            conn.commit()
        except Exception as e:
            conn.rollback()
            codigo = gen_codigo("SEC")
            try:
                cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,lugar_nacimiento,distrito,provincia,telefono,email,centro,anio,codigo_alumno,foto,centro_codigo,curso) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"), (f.get('nombre'),f.get('apellidos'),f.get('lugar_nacimiento'),f.get('distrito'),f.get('provincia'),f.get('telefono'),f.get('email'),f.get('centro'),f.get('anio'),codigo,foto_name,cc,f.get('curso')))
                conn.commit()
                try: cur.close(); conn.close()
                except: pass
                return redirect('/alumnos')
            except Exception as e2:
                try: cur.close(); conn.close()
                except: pass
                return render_template_string(BASE, content=f"<div class='alert alert-danger'><b>El codigo {codigo_bruto} ya existe.</b><br>Deja el campo CODIGO en BLANCO.<br><small>{e}</small></div><a href='/alumnos/nuevo' class='btn btn-primary'>Volver</a> <a href='/dashboard' class='btn btn-warning'>Menu Principal</a>")
        try: cur.close(); conn.close()
        except: pass
        return redirect('/alumnos')
    extra = "<input name='centro_codigo' placeholder='Codigo centro (admin)' class='form-control mb-2'>" if session.get('rol')=='admin' else ""
    return render_template_string(BASE, content=f"<a href='/alumnos' class='btn btn-sm btn-secondary mb-2'>Volver</a> <a href='/dashboard' class='btn btn-sm btn-warning mb-2'>Menu Principal</a><h4>Nuevo Sec/Bach</h4><div class='alert alert-info py-1'><small>Consejo: Deja el CODIGO en blanco para que se genere automatico.</small></div><form method='post' enctype='multipart/form-data' class='row g-2'><div class='col-md-6'><input name='nombre' placeholder='Nombre' class='form-control' required></div><div class='col-md-6'><input name='apellidos' placeholder='Apellidos' class='form-control' required></div><div class='col-md-4'><input name='lugar_nacimiento' placeholder='Lugar nac' class='form-control'></div><div class='col-md-4'><input name='distrito' placeholder='Distrito' class='form-control'></div><div class='col-md-4'><input name='provincia' placeholder='Provincia' class='form-control'></div><div class='col-md-4'><input name='telefono' placeholder='Telefono' class='form-control'></div><div class='col-md-4'><input name='email' placeholder='Email' class='form-control'></div><div class='col-md-4'><input name='curso' placeholder='Ej: 1 ESBA, 2 BACH' class='form-control'></div><div class='col-md-4'><input name='centro' placeholder='Centro' class='form-control'></div><div class='col-md-4'><input name='anio' placeholder='Anio' class='form-control'></div><div class='col-md-4'><input name='codigo_alumno' placeholder='Codigo auto (deja en blanco)' class='form-control'></div><div class='col-md-4'>{extra}</div><div class='col-md-6'><input type='file' name='foto' class='form-control'></div><div class='col-12'><button class='btn btn-primary'>Guardar</button></div></form>")

@app.route('/alumno/<int:id>/editar', methods=['GET','POST'])
def alumno_editar(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'lugar_nacimiento':r[3],'distrito':r[4],'provincia':r[5],'telefono':r[6],'email':r[7],'centro':r[8],'anio':r[9],'codigo_alumno':r[10],'foto':r[11],'centro_codigo':r[12],'curso':r[13]}
    if request.method=='POST':
        f=request.form
        cur.execute(adapt("UPDATE alumnos SET nombre=?, apellidos=?, lugar_nacimiento=?, distrito=?, provincia=?, telefono=?, email=?, centro=?, anio=?, curso=?, centro_codigo=? WHERE id=?"), (f.get('nombre'),f.get('apellidos'),f.get('lugar_nacimiento'),f.get('distrito'),f.get('provincia'),f.get('telefono'),f.get('email'),f.get('centro'),f.get('anio'),f.get('curso'),f.get('centro_codigo') or d['centro_codigo'], id))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect(f'/alumno/{id}')
    try: cur.close(); conn.close()
    except: pass
    return render_template_string(BASE, content=f"<a href='/alumnos' class='btn btn-sm btn-secondary mb-2'>Volver al listado</a> <a href='/dashboard' class='btn btn-sm btn-warning mb-2'>Menu Principal</a><h4>Editar Alumno {d['codigo_alumno']}</h4><form method='post' class='row g-2'><div class='col-md-6'><label>Nombre</label><input name='nombre' value='{d.get('nombre','')}' class='form-control' required></div><div class='col-md-6'><label>Apellidos</label><input name='apellidos' value='{d.get('apellidos','')}' class='form-control' required></div><div class='col-md-4'><label>Lugar Nacimiento</label><input name='lugar_nacimiento' value='{d.get('lugar_nacimiento','')}' class='form-control'></div><div class='col-md-4'><label>Distrito</label><input name='distrito' value='{d.get('distrito','')}' class='form-control'></div><div class='col-md-4'><label>Provincia</label><input name='provincia' value='{d.get('provincia','')}' class='form-control'></div><div class='col-md-4'><label>Telefono</label><input name='telefono' value='{d.get('telefono','')}' class='form-control'></div><div class='col-md-4'><label>Email</label><input name='email' value='{d.get('email','')}' class='form-control'></div><div class='col-md-4'><label>Curso</label><input name='curso' value='{d.get('curso','')}' class='form-control'></div><div class='col-md-4'><label>Centro</label><input name='centro' value='{d.get('centro','')}' class='form-control'></div><div class='col-md-4'><label>Anio</label><input name='anio' value='{d.get('anio','')}' class='form-control'></div><div class='col-md-4'><label>Codigo Centro</label><input name='centro_codigo' value='{d.get('centro_codigo','')}' class='form-control'></div><div class='col-12'><button class='btn btn-success'>Guardar Cambios</button> <a href='/alumno/{id}' class='btn btn-secondary'>Cancelar</a></div></form>")

@app.route('/alumno/<int:id>')
def alumno_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'lugar_nacimiento':r[3],'distrito':r[4],'provincia':r[5],'telefono':r[6],'email':r[7],'centro':r[8],'anio':r[9],'codigo_alumno':r[10],'foto':r[11],'centro_codigo':r[12],'curso':r[13]}
    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=?"), (d['codigo_alumno'],)); nt_row=cur.fetchone()
    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=?"), (d['codigo_alumno'],)); sel_rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    qr=gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html=f"<img src='/fotos/{d['foto']}' style='width:150px'>" if d.get('foto') else "Sin foto"
    import json
    datos_trim = {}
    curso_actual = d.get('curso') or ''
    if nt_row:
        nd = dict(nt_row) if isinstance(nt_row,dict) else {'datos':nt_row[3],'curso':nt_row[2]}
        curso_actual = nd.get('curso') or curso_actual
        try: datos_trim = json.loads(nd.get('datos') or '{}')
        except: datos_trim={}
    materias_curso = PLAN.get(curso_actual) or []
    if not materias_curso:
        for k,v in PLAN.items():
            if curso_actual.lower() in k.lower() or k.lower() in curso_actual.lower(): materias_curso=v; break
    if not materias_curso: materias_curso=["Lengua Espanola","Matematicas","Historia","Ingles"]
    trim_html = ""
    for mat in materias_curso:
        vals = datos_trim.get(mat, {})
        trim_html+=f"<tr><td><b>{mat}</b></td><td><input name='T1_{mat}' value='{vals.get('T1','')}' class='form-control form-control-sm'></td><td><input name='T2_{mat}' value='{vals.get('T2','')}' class='form-control form-control-sm'></td><td><input name='T3_{mat}' value='{vals.get('T3','')}' class='form-control form-control-sm'></td><td><input name='JUN_{mat}' value='{vals.get('JUN','')}' class='form-control form-control-sm' style='font-weight:bold;background:#e7f3ff'></td></tr>"
    sel_html = "".join([f"<tr><td>{(dict(s)['fase'] if isinstance(s,dict) else s[2])}</td><td>{(dict(s)['asignatura'] if isinstance(s,dict) else s[3])}</td><td><b>{(dict(s)['nota'] if isinstance(s,dict) else s[4])}</b></td></tr>" for s in sel_rows]) or "<tr><td colspan=3>Sin notas de Selectividad</td></tr>"
    return render_template_string(BASE, content=f"<div class='d-flex gap-2 mb-2'><a href='/alumnos' class='btn btn-secondary btn-sm'>Volver Listado</a><a href='/dashboard' class='btn btn-warning btn-sm'>Menu Principal</a><a href='/alumno/{id}/editar' class='btn btn-warning btn-sm'>Editar Datos</a><a href='/alumno/{id}/notas' class='btn btn-primary btn-sm'>Ver Boletin</a><a href='/alumno/{id}/selectividad' class='btn btn-dark btn-sm'>Selectividad</a></div><div class='row'><div class='col-md-8'><h4>{d['nombre']} {d['apellidos']} <small>({d['codigo_alumno']})</small></h4><p>Centro:{d.get('centro')} Curso:<b>{d.get('curso')}</b></p><h5>Notas Trimestrales: Curso -> Materia -> 1T 2T 3T Junio</h5><form method='post' action='/alumno/{id}/notas_trimestre/guardar'><select name='curso_trim' class='form-control mb-2' style='max-width:300px'><option>{curso_actual}</option>{''.join([f'<option>{k}</option>' for k in PLAN.keys()])}</select><table class='table table-bordered table-sm'><tr><th>Materia</th><th>1er Trim</th><th>2do Trim</th><th>3er Trim</th><th>Junio Final</th></tr>{trim_html}</table><button class='btn btn-success'>Guardar Notas Trimestrales</button></form><hr><h5>Selectividad</h5><table class='table'><tr><th>Fase</th><th>Asignatura</th><th>Nota</th></tr>{sel_html}</table></div><div class='col-md-4 text-center'>{foto_html}<br><br><div class='card p-2'><b>QR</b><br><img src='{qr}' style='width:180px'></div></div></div>")

@app.route('/alumno/<int:id>/notas_trimestre/guardar', methods=['POST'])
def guardar_trimestres(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
    curso=request.form.get('curso_trim') or ''
    import json
    datos={}
    for k,v in request.form.items():
        if k.startswith(('T1_','T2_','T3_','JUN_')):
            parts=k.split('_',1); trim=parts[0]; mat=parts[1]
            if mat not in datos: datos[mat]={}
            datos[mat][trim]=v.strip()
    datos = {m:vals for m,vals in datos.items() if any(vals.values())}
    json_data=json.dumps(datos, ensure_ascii=False)
    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=?"), (d['codigo_alumno'],))
    existe=cur.fetchone()
    if existe: cur.execute(adapt("UPDATE notas_trimestres SET curso=?, datos=?, centro_codigo=? WHERE alumno_codigo=?"), (curso, json_data, d['centro_codigo'], d['codigo_alumno']))
    else: cur.execute(adapt("INSERT INTO notas_trimestres (alumno_codigo, curso, datos, centro_codigo) VALUES (?,?,?,?)"), (d['codigo_alumno'], curso, json_data, d['centro_codigo']))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect(f'/alumno/{id}')

@app.route('/alumno/<int:id>/notas')
def alumno_notas(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13]}
    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=?"), (d['codigo_alumno'],)); nt_row=cur.fetchone()
    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=?"), (d['codigo_alumno'],)); sel_rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    import json
    html=""
    if nt_row:
        nd=dict(nt_row) if isinstance(nt_row,dict) else {'datos':nt_row[3],'curso':nt_row[2]}
        try:
            datos=json.loads(nd.get('datos') or '{}')
            html+=f"<h4>Notas Trimestrales - {nd.get('curso','')}</h4><table class='table table-bordered'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
            for mat,vals in datos.items(): html+=f"<tr><td>{mat}</td><td>{vals.get('T1','')}</td><td>{vals.get('T2','')}</td><td>{vals.get('T3','')}</td><td><b>{vals.get('JUN','')}</b></td></tr>"
            html+="</table>"
        except: pass
    if sel_rows:
        html+="<h4>SELECTIVIDAD</h4><table class='table table-bordered'><tr><th>Fase</th><th>Asignatura</th><th>Nota</th></tr>"
        for s in sel_rows:
            sd=dict(s) if isinstance(s,dict) else {'fase':s[2],'asignatura':s[3],'nota':s[4]}
            html+=f"<tr><td>{sd['fase']}</td><td>{sd['asignatura']}</td><td><b>{sd['nota']}</b></td></tr>"
        html+="</table>"
    if not html: html="<p>Sin notas</p>"
    return render_template_string(BASE, content=f"<a href='/alumno/{id}' class='btn btn-secondary'>Volver</a> <a href='/dashboard' class='btn btn-warning'>Menu</a> <button onclick='window.print()' class='btn btn-primary'>Imprimir</button><div class='card p-4 mt-3'><h3 class='text-center'>BOLETIN OFICIAL CEACGE V24</h3><p><b>Alumno:</b>{d['nombre']} {d['apellidos']} | <b>Codigo:</b>{d['codigo_alumno']} | <b>Curso:</b>{d.get('curso')}</p>{html}</div>")

@app.route('/alumno/<int:id>/selectividad')
def alumno_selectividad(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13]}
    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase"), (d['codigo_alumno'],)); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html_rows="".join([f"<tr><td>{(dict(s)['fase'] if isinstance(s,dict) else s[2])}</td><td>{(dict(s)['asignatura'] if isinstance(s,dict) else s[3])}</td><td><b>{(dict(s)['nota'] if isinstance(s,dict) else s[4])}</b></td><td><a href='/selectividad/{(dict(s)['id'] if isinstance(s,dict) else s[0])}/borrar' class='btn btn-sm btn-danger'>Borrar</a></td></tr>" for s in rows]) or "<tr><td colspan=4>Sin datos</td></tr>"
    return render_template_string(BASE, content=f"<a href='/alumno/{id}' class='btn btn-secondary btn-sm'>Volver a Ficha</a> <a href='/dashboard' class='btn btn-warning btn-sm'>Menu Principal</a><h4 class='mt-3'>Selectividad - {d['nombre']} {d['apellidos']} ({d['codigo_alumno']})</h4><div class='card p-3 mt-3'><table class='table table-bordered'><tr><th>Fase</th><th>Asignatura</th><th>Nota</th><th></th></tr>{html_rows}</table><hr><h5>Anadir Nota Selectividad</h5><form method='post' action='/alumno/{id}/selectividad/add' class='row g-2'><div class='col-md-3'><label>Fase</label><select name='fase' class='form-control'><option value='Fase General'>Fase General</option><option value='LETRAS Y CCSS / HUMANIDADES'>Letras y CCSS / Humanidades</option><option value='CIENCIAS Y TECNOLOGIA'>Ciencias y Tecnologia</option><option value='CIENCIAS DE LA NATURALEZA Y SALUD'>Ciencias Naturaleza y Salud</option></select></div><div class='col-md-4'><label>Asignatura</label><select name='asignatura' class='form-control'><option>Lengua Espanola</option><option>Historia</option><option>Historia de la Filosofia</option><option>Idioma (Ingles/Frances)</option><option>Historia de Africa y de G.E</option><option>Literatura Universal</option><option>Historia de Arte</option><option>Geografia</option><option>Matematicas Aplicadas a CS</option><option>Latin</option><option>Griego</option><option>Matematicas</option><option>Fisica</option><option>Quimica</option><option>Dibujo Tecnico</option><option>Informatica</option><option>Tecnologia Industrial</option><option>Electrotecnia</option><option>Biologia y Geologia</option><option>C.N y Salud</option></select></div><div class='col-md-2'><label>Nota</label><input name='nota' class='form-control' required></div><div class='col-md-3'><label>Convocatoria</label><input name='convocatoria' class='form-control' value='Junio 2025'></div><div class='col-12'><button class='btn btn-dark'>Guardar</button></div></form></div>")

@app.route('/alumno/<int:id>/selectividad/add', methods=['POST'])
def selectividad_add(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone(); d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
    cur.execute(adapt("INSERT INTO selectividad (alumno_codigo, fase, asignatura, nota, convocatoria, centro_codigo) VALUES (?,?,?,?,?,?)"), (d['codigo_alumno'], request.form.get('fase'), request.form.get('asignatura'), request.form.get('nota'), request.form.get('convocatoria'), d['centro_codigo']))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect(f'/alumno/{id}/selectividad')

@app.route('/selectividad/<int:sid>/borrar')
def selectividad_borrar(sid):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("DELETE FROM selectividad WHERE id=?"), (sid,))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect('/alumnos')

@app.route('/primaria')
def primaria():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM alumnos_primaria ORDER BY id DESC"); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html="<div class='d-flex justify-content-between'><h4>Primaria <a href='/primaria/nuevo' class='btn btn-sm btn-success'>+ Nuevo</a></h4><a href='/dashboard' class='btn btn-sm btn-secondary'>Volver al Menu Principal</a></div><div class='row mt-2'>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[4]}
        html+=f"<div class='col-md-3 mb-3'><div class='card p-2 text-center'><b>{d['nombre']} {d['apellidos']}</b><br><small>{d['codigo_alumno']}</small><br><a href='/primaria/{d['id']}' class='btn btn-sm btn-success mt-1'>Ver/QR</a> <a href='/primaria/{d['id']}/editar' class='btn btn-sm btn-warning mt-1'>Editar</a></div></div>"
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
        except:
            conn.rollback()
            codigo = gen_codigo("PRI")
            cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,foto,codigo_alumno,centro,anio,centro_codigo) VALUES (?,?,?,?,?,?,?)"), (request.form.get('nombre'),request.form.get('apellidos'),foto_name,codigo,request.form.get('centro'),request.form.get('anio'),cc))
            conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect('/primaria')
    extra = "<input name='centro_codigo' placeholder='Codigo centro (admin)' class='form-control mb-2'>" if session.get('rol')=='admin' else ""
    return render_template_string(BASE, content=f"<a href='/primaria' class='btn btn-sm btn-secondary mb-2'>Volver</a> <a href='/dashboard' class='btn btn-sm btn-warning mb-2'>Menu Principal</a><h4>Nuevo Primaria</h4><form method='post' enctype='multipart/form-data'><input name='nombre' placeholder='Nombre' class='form-control mb-2' required><input name='apellidos' placeholder='Apellidos' class='form-control mb-2' required><input name='centro' placeholder='Centro' class='form-control mb-2'><input name='anio' placeholder='Anio' class='form-control mb-2'><input name='codigo_alumno' placeholder='Codigo auto (deja en blanco)' class='form-control mb-2'>{extra}<input type='file' name='foto' class='form-control mb-2' accept='image/*' required><button class='btn btn-success'>Guardar</button></form>")

@app.route('/primaria/<int:id>')
def primaria_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"), (id,)); r=cur.fetchone()
    try: cur.close(); conn.close()
    except: pass
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'foto':r[3],'codigo_alumno':r[4],'centro':r[5],'centro_codigo':r[7]}
    qr=gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html=f"<img src='/fotos/{d['foto']}' style='width:200px'>" if d.get('foto') else "Sin foto"
    return render_template_string(BASE, content=f"<a href='/primaria' class='btn btn-sm btn-secondary'>Volver</a> <a href='/dashboard' class='btn btn-sm btn-warning'>Menu Principal</a><h4 class='mt-2'>{d['nombre']} {d['apellidos']} - {d['codigo_alumno']}</h4><div class='row'><div class='col-md-6'>{foto_html}<p>Centro:{d.get('centro')} ({d.get('centro_codigo')})</p><a href='/primaria/{d['id']}/editar' class='btn btn-warning'>Editar</a></div><div class='col-md-6 text-center'><div class='card p-3'><b>QR</b><br><img src='{qr}' style='width:200px'></div></div></div>")

@app.route('/primaria/<int:id>/editar', methods=['GET','POST'])
def primaria_editar(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"), (id,)); r=cur.fetchone()
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[4],'centro':r[5],'anio':r[6],'centro_codigo':r[7]}
    if request.method=='POST':
        cur.execute(adapt("UPDATE alumnos_primaria SET nombre=?, apellidos=?, centro=?, anio=?, centro_codigo=? WHERE id=?"), (request.form.get('nombre'), request.form.get('apellidos'), request.form.get('centro'), request.form.get('anio'), request.form.get('centro_codigo') or d.get('centro_codigo'), id))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect(f'/primaria/{id}')
    try: cur.close(); conn.close()
    except: pass
    return render_template_string(BASE, content=f"<a href='/primaria/{id}' class='btn btn-secondary btn-sm'>Volver</a> <a href='/dashboard' class='btn btn-sm btn-warning'>Menu Principal</a><h4>Editar Primaria {d['codigo_alumno']}</h4><form method='post' class='row g-2'><div class='col-md-6'><input name='nombre' value='{d.get('nombre','')}' class='form-control'></div><div class='col-md-6'><input name='apellidos' value='{d.get('apellidos','')}' class='form-control'></div><div class='col-md-4'><input name='centro' value='{d.get('centro','')}' class='form-control'></div><div class='col-md-4'><input name='anio' value='{d.get('anio','')}' class='form-control'></div><div class='col-md-4'><input name='centro_codigo' value='{d.get('centro_codigo','')}' class='form-control'></div><div class='col-12'><button class='btn btn-success'>Guardar</button></div></form>")

@app.route('/centros')
def centros():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM centros ORDER BY id DESC"); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html="<div class='d-flex justify-content-between'><h4>Centros <a href='/centros/nuevo' class='btn btn-sm btn-warning'>+ Nuevo</a></h4><a href='/dashboard' class='btn btn-sm btn-secondary'>Volver al Menu Principal</a></div><table class='table mt-2'><tr><th>Nombre</th><th>Codigo</th></tr>"
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
        cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email) VALUES (?,?,?,?,?)"), (request.form.get('nombre'),codigo,request.form.get('localidad'),request.form.get('contacto'),request.form.get('email')))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect('/centros')
    return render_template_string(BASE, content="<a href='/centros' class='btn btn-sm btn-secondary mb-2'>Volver</a> <a href='/dashboard' class='btn btn-sm btn-warning mb-2'>Menu Principal</a><h4>Nuevo Centro</h4><form method='post'><input name='nombre' placeholder='Nombre' class='form-control mb-2' required><input name='codigo' placeholder='Codigo auto' class='form-control mb-2'><input name='localidad' placeholder='Localidad' class='form-control mb-2'><input name='contacto' placeholder='Contacto' class='form-control mb-2'><input name='email' placeholder='Email' class='form-control mb-2'><button class='btn btn-warning'>Guardar</button></form>")

@app.route('/usuarios')
def usuarios():
    if 'usuario' not in session or session.get('rol')!='admin': return "Solo admin",403
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM usuarios ORDER BY id"); rows=cur.fetchall()
    cur.execute("SELECT codigo,nombre FROM centros"); centros_list=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    opts="".join([f"<option value='{c['codigo'] if isinstance(c,dict) else c[0]}'>{c['codigo'] if isinstance(c,dict) else c[0]} - {c['nombre'] if isinstance(c,dict) else c[1]}</option>" for c in centros_list])
    html="<div class='d-flex justify-content-between'><h4>Usuarios</h4><a href='/dashboard' class='btn btn-sm btn-secondary'>Volver al Menu Principal</a></div><table class='table'><tr><th>Usuario</th><th>Rol</th><th>Centro</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'usuario':r[1],'rol':r[3],'centro_codigo':r[4]}
        html+=f"<tr><td>{d['usuario']}</td><td>{d['rol']}</td><td>{d['centro_codigo']}</td></tr>"
    html+=f"</table><hr><h5>Crear usuario centro</h5><form method='post' action='/usuarios/nuevo' class='row g-2'><div class='col-md-3'><input name='usuario' placeholder='Usuario' class='form-control' required></div><div class='col-md-3'><input name='password' placeholder='Pass' class='form-control' required></div><div class='col-md-3'><select name='centro_codigo' class='form-control' required><option value=''>Elige centro</option>{opts}</select></div><div class='col-md-3'><button class='btn btn-dark'>Crear</button></div></form>"
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
    alumno=None
    nt_data=None; sel_data=[]
    if codigo:
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("SELECT * FROM alumnos WHERE codigo_alumno=?"), (codigo.strip(),))
        alumno=cur.fetchone()
        if not alumno:
            cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE codigo_alumno=?"), (codigo.strip(),))
            alumno=cur.fetchone()
        if alumno:
            ad=dict(alumno) if isinstance(alumno,dict) else {'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4]}
            cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=?"), (ad['codigo_alumno'],))
            nt_data=cur.fetchone()
            cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=?"), (ad['codigo_alumno'],))
            sel_data=cur.fetchall()
        try: cur.close(); conn.close()
        except: pass
    content=f"<h3 class='text-center'>Consulta Publica</h3><form method='post' class='d-flex justify-content-center gap-2 mt-4'><input name='codigo' value='{codigo or ''}' placeholder='Codigo Alumno' class='form-control' style='max-width:350px' required><button class='btn btn-primary'>Buscar</button></form>"
    if codigo and not alumno: content+=f"<div class='alert alert-danger mt-4 text-center'>Codigo {codigo} no encontrado</div>"
    if alumno:
        d=dict(alumno) if isinstance(alumno,dict) else {'nombre':alumno[1],'apellidos':alumno[2],'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4],'centro':alumno[8] if len(alumno)>8 else alumno[5],'foto':alumno[11] if len(alumno)>10 else alumno[3],'curso':alumno[13] if len(alumno)>13 else ''}
        import json
        html=""
        if nt_data:
            nd=dict(nt_data) if isinstance(nt_data,dict) else {'datos':nt_data[3],'curso':nt_data[2]}
            try:
                datos=json.loads(nd.get('datos') or '{}')
                html+=f"<h5>Notas Trimestrales - {nd.get('curso','')}</h5><table class='table table-bordered'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
                for mat,vals in datos.items(): html+=f"<tr><td>{mat}</td><td>{vals.get('T1','')}</td><td>{vals.get('T2','')}</td><td>{vals.get('T3','')}</td><td><b>{vals.get('JUN','')}</b></td></tr>"
                html+="</table>"
            except: pass
        if sel_data:
            html+="<h5>SELECTIVIDAD</h5><table class='table table-bordered'><tr><th>Fase</th><th>Asignatura</th><th>Nota</th></tr>"
            for s in sel_data:
                sd=dict(s) if isinstance(s,dict) else {'fase':s[2],'asignatura':s[3],'nota':s[4]}
                html+=f"<tr><td>{sd['fase']}</td><td>{sd['asignatura']}</td><td><b>{sd['nota']}</b></td></tr>"
            html+="</table>"
        if not html: html="<div class='alert alert-info'>Aun no tiene notas cargadas</div>"
        foto=f"<img src='/fotos/{d.get('foto')}' style='width:140px;border-radius:8px'>" if d.get('foto') else ""
        content+=f"<div class='card p-4 mt-4 shadow'><div class='row'><div class='col-md-8'><h4>{d.get('nombre')} {d.get('apellidos','')}</h4><p><b>Codigo:</b> {d.get('codigo_alumno')} | <b>Centro:</b> {d.get('centro')} | <b>Curso:</b> {d.get('curso','')}</p><hr>{html}</div><div class='col-md-4 text-center'>{foto}</div></div></div>"
    return render_template_string(BASE, content=content)

@app.route('/fotos/<path:filename>')
def fotos(filename): return send_from_directory(UPLOAD_FOLDER, filename)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
