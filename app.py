import os, secrets, io, base64
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'CEACGE-V28-3-FINAL'
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

def nota_color(n):
    try:
        s=str(n).replace(',','.').strip()
        if not s: return ""
        return "color:#d00000;font-weight:bold;background:#ffe0e0" if float(s)<5 else "color:#0a7d00;font-weight:bold;background:#e7f3ff"
    except: return "font-weight:bold"

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
        img=qrcode.make(txt)
        b=io.BytesIO(); img.save(b,format='PNG')
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
            cur.execute("CREATE TABLE IF NOT EXISTS notas_trimestres (id SERIAL PRIMARY KEY, alumno_codigo TEXT UNIQUE, curso TEXT, datos TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS selectividad (id SERIAL PRIMARY KEY, alumno_codigo TEXT, fase TEXT, asignatura TEXT, nota TEXT, nota2 TEXT, convocatoria TEXT, centro_codigo TEXT, bloque TEXT)")
            try: cur.execute("ALTER TABLE selectividad ADD COLUMN IF NOT EXISTS bloque TEXT")
            except: pass
            try: cur.execute("ALTER TABLE selectividad ADD COLUMN IF NOT EXISTS nota2 TEXT")
            except: pass
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas_trimestres (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_codigo TEXT UNIQUE, curso TEXT, datos TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS selectividad (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_codigo TEXT, fase TEXT, asignatura TEXT, nota TEXT, nota2 TEXT, convocatoria TEXT, centro_codigo TEXT, bloque TEXT)")
            try: cur.execute("ALTER TABLE selectividad ADD COLUMN bloque TEXT")
            except: pass
            try: cur.execute("ALTER TABLE selectividad ADD COLUMN nota2 TEXT")
            except: pass
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
        if not cur.fetchone():
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
        conn.commit()
    except Exception as e: print(e)
    finally:
        try: cur.close(); conn.close()
        except: pass
init_db()

BASE="<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CEACGE</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body><nav class='navbar navbar-dark bg-primary'><div class='container'><a class='navbar-brand' href='/dashboard'>CEACGE V28.3</a><div><a href='/dashboard' class='btn btn-sm btn-warning me-2'>Menu</a><a href='/consulta' class='btn btn-sm btn-light me-2'>Consulta</a><span class='text-white me-2'>{{session.usuario}} ({{session.rol}})</span><a href='/logout' class='text-white'>Salir</a></div></div></nav><div class='container mt-4'>{{content|safe}}</div></body></html>"

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
    return render_template_string("<html><head><meta charset='utf-8'><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body class='bg-light'><div class='container d-flex justify-content-center align-items-center vh-100'><div class='card p-4' style='width:360px'><h4 class='text-center'>CEACGE V28.3</h4>{% if err %}<div class='alert alert-danger'>{{err}}</div>{% endif %}<form method='post'><input class='form-control mb-2' name='usuario' placeholder='Usuario' required><input class='form-control mb-3' type='password' name='password' placeholder='Pass' required><button class='btn btn-primary w-100'>Entrar</button></form><hr><a href='/consulta' class='btn btn-outline-secondary w-100'>Consulta por Codigo</a></div></div></body></html>", err=err)
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
    return render_template_string(BASE, content=f"<h3>Panel {session['usuario']}</h3><div class='row g-3 mt-2'><div class='col-md-4'><div class='card p-3'><h5>Secundaria y Bachillerato</h5><h2>{sec}</h2><a href='/alumnos' class='btn btn-primary btn-sm'>Ver Listado</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Primaria</h5><h2>{pri}</h2><a href='/primaria' class='btn btn-success btn-sm'>Ver</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Centros</h5><h2>{cen}</h2><a href='/centros' class='btn btn-warning btn-sm'>Ver</a></div></div></div>")

@app.route('/alumnos')
def alumnos():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html="<div class='d-flex justify-content-between'><h4>Secundaria y Bach <a href='/alumnos/nuevo' class='btn btn-sm btn-primary'>+ Nuevo</a></h4><a href='/dashboard' class='btn btn-sm btn-secondary'>Menu Principal</a></div><table class='table table-hover'><tr><th>Codigo</th><th>Nombre</th><th>Accion</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10]}
        html+=f"<tr><td><b>{d['codigo_alumno']}</b></td><td>{d['nombre']} {d['apellidos']}</td><td><a href='/alumno/{d['id']}' class='btn btn-sm btn-primary'>Ver</a> <a href='/alumno/{d['id']}/selectividad' class='btn btn-sm btn-dark'>Selectividad</a></td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)

@app.route('/alumno/<int:id>/selectividad')
def alumno_selectividad(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13]}
    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (d['codigo_alumno'],)); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html_rows=""
    for s in rows:
        sd=dict(s) if isinstance(s,dict) else {}
        if sd: n1=sd.get('nota',''); n2=sd.get('nota2',''); sid=sd.get('id',''); fase=sd.get('fase',''); asig=sd.get('asignatura',''); bloque=sd.get('bloque','')
        else: sid=s[0] if len(s)>0 else ''; fase=s[2] if len(s)>2 else ''; asig=s[3] if len(s)>3 else ''; n1=s[4] if len(s)>4 else ''; n2=s[5] if len(s)>5 else ''; bloque=s[8] if len(s)>8 else (s[7] if len(s)>7 else '')
        html_rows+=f"<tr><td><b>{fase}</b><br><small>{bloque}</small></td><td>{asig}</td><td style='{nota_color(n1)}'>{n1}</td><td style='{nota_color(n2)}'>{n2}</td><td><a href='/selectividad/{sid}/borrar' class='btn btn-sm btn-danger'>Borrar</a></td></tr>"
    if not html_rows: html_rows="<tr><td colspan=5>Sin datos</td></tr>"
    page = f"""
<a href='/alumno/{id}' class='btn btn-secondary btn-sm'>Volver a Ficha</a> <a href='/dashboard' class='btn btn-warning btn-sm'>Menu Principal</a>
<h4 class='mt-3'>Selectividad - {d['nombre']} {d['apellidos']} ({d['codigo_alumno']})</h4>
<div class='alert alert-info py-2'><small><b>Fase General:</b> Lengua Espanola, Historia, Historia de la Filosofia, Idioma.<br>
<b>Fase Especial - 3 Bloques:</b> BLOQUE 1: LITERATURA Y CCSS, BLOQUE 2: CIENCIAS Y TECNOLOGIA, BLOQUE 3: NATURALEZA Y SALUD<br>
<span style='color:red;font-weight:bold'>Notas inferiores a 5 en ROJO - Nota Fase 1 y Nota Fase 2</span></small></div>
<div class='card p-3 mt-3'>
<table class='table table-bordered'><tr><th>Fase</th><th>Asignatura</th><th>Nota Fase 1</th><th>Nota Fase 2</th><th></th></tr>{html_rows}</table>
<hr>
<h5>Anadir Nota - 2 Fases - 2 Notas</h5>
<form method='post' action='/alumno/{id}/selectividad/add' class='row g-2'>
<div class='col-md-2'><label>Fase</label><select name='fase' id='faseSel' class='form-control' onchange='cambiar()'><option value='GENERAL'>Fase General</option><option value='ESPECIAL'>Fase Especial</option></select></div>
<div class='col-md-3'><label>Asignatura</label><select name='asignatura_bloque' id='asigSel' class='form-control'></select></div>
<div class='col-md-2'><label>Nota Fase 1</label><input name='nota' class='form-control' required placeholder='Ej: 6,5'></div>
<div class='col-md-2'><label>Nota Fase 2</label><input name='nota2' class='form-control' placeholder='Ej: 7'></div>
<div class='col-md-3'><label>Convocatoria</label><input name='convocatoria' class='form-control' value='Junio 2025'></div>
<div class='col-12'><button class='btn btn-dark'>Guardar</button></div>
</form>
</div>
<script>
const generalList = ["Lengua Espanola", "Historia", "Historia de la Filosofia", "Idioma"];
const especialBloques = {{"BLOQUE 1: LITERATURA Y CIENCIAS SOCIALES": ["Historia de Africa y de G.E", "Literatura Universal", "Historia de Arte", "Geografia", "Matematicas Aplicadas a CS", "Latin", "Griego"], "BLOQUE 2: CIENCIAS Y TECNOLOGIA": ["Matematicas", "Fisica", "Quimica", "Dibujo Tecnico", "Informatica", "Tecnologia Industrial", "Electrotecnia"], "BLOQUE 3: CIENCIAS DE LA NATURALEZA Y SALUD": ["Biologia y Geologia", "C.N y Salud", "Fisica y Quimica"]}};
function cambiar(){{
  const fase=document.getElementById('faseSel').value;
  const sel=document.getElementById('asigSel');
  sel.innerHTML='';
  if(fase==='GENERAL'){{
    generalList.forEach(m=>{{ let o=document.createElement('option'); o.value=m; o.text=m; sel.add(o); }});
  }} else {{
    for(const [bloque, mats] of Object.entries(especialBloques)){{
      let g=document.createElement('optgroup'); g.label=bloque;
      mats.forEach(m=>{{ let o=document.createElement('option'); o.value=m+'|'+bloque; o.text=m; g.appendChild(o); }});
      sel.appendChild(g);
    }}
  }}
}}
cambiar();
</script>
"""
    return render_template_string(BASE, content=page)

@app.route('/alumno/<int:id>/selectividad/add', methods=['POST'])
def selectividad_add(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone(); d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
    fase_raw=request.form.get('fase') or 'GENERAL'
    asig_bloque=request.form.get('asignatura_bloque') or ''
    bloque=""; asignatura=asig_bloque
    if '|' in asig_bloque:
        asignatura, bloque = asig_bloque.split('|',1)
    fase_nombre = "Fase General" if fase_raw=="GENERAL" else "Fase Especial"
    if not bloque and fase_raw=="GENERAL": bloque="GENERAL"
    cur.execute(adapt("INSERT INTO selectividad (alumno_codigo, fase, asignatura, nota, nota2, convocatoria, centro_codigo, bloque) VALUES (?,?,?,?,?,?,?,?)"), (d['codigo_alumno'], fase_nombre, asignatura, request.form.get('nota'), request.form.get('nota2'), request.form.get('convocatoria'), d['centro_codigo'], bloque))
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

@app.route('/alumno/<int:id>')
def alumno_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13],'foto':r[11]}
    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=?"), (d['codigo_alumno'],)); nt_row=cur.fetchone()
    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (d['codigo_alumno'],)); sel_rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    qr=gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html=f"<img src='/fotos/{d['foto']}' style='width:150px;border-radius:8px' onerror=\"this.style.display='none'\">" if d.get('foto') else "<small>Sin foto</small>"
    import json
    datos_trim = {}
    curso_actual = d.get('curso') or ''
    if nt_row:
        nd = dict(nt_row) if isinstance(nt_row,dict) else {'datos':nt_row[3],'curso':nt_row[2]}
        curso_actual = nd.get('curso') or curso_actual
        try: datos_trim = json.loads(nd.get('datos') or '{}')
        except: datos_trim={}
    materias_curso = PLAN.get(curso_actual) or ["Lengua Espanola","Matematicas","Historia","Ingles"]
    trim_html = ""
    for mat in materias_curso:
        vals = datos_trim.get(mat, {})
        def _col(v):
            try:
                if not v: return ""
                return "color:#d00000;font-weight:bold;background:#ffe0e0" if float(str(v).replace(',','.'))<5 else "color:#0a7d00;font-weight:bold;background:#e7f3ff"
            except: return ""
        trim_html+=f"<tr><td><b>{mat}</b></td><td><input name='T1_{mat}' value='{vals.get('T1','')}' class='form-control form-control-sm' style='{_col(vals.get('T1',''))}'></td><td><input name='T2_{mat}' value='{vals.get('T2','')}' class='form-control form-control-sm' style='{_col(vals.get('T2',''))}'></td><td><input name='T3_{mat}' value='{vals.get('T3','')}' class='form-control form-control-sm' style='{_col(vals.get('T3',''))}'></td><td><input name='JUN_{mat}' value='{vals.get('JUN','')}' class='form-control form-control-sm' style='{_col(vals.get('JUN',''))}'></td></tr>"
    sel_html=""
    for s in sel_rows:
        sd=dict(s) if isinstance(s,dict) else {}
        if sd: n1=sd.get('nota',''); n2=sd.get('nota2','')
        else: n1=s[4] if len(s)>4 else ''; n2=s[5] if len(s)>5 else ''; sd={'fase':s[2] if len(s)>2 else '', 'asignatura':s[3] if len(s)>3 else '', 'bloque':s[8] if len(s)>8 else ''}
        sel_html+=f"<tr><td><b>{sd.get('fase','')}</b><br><small>{sd.get('bloque','')}</small></td><td>{sd.get('asignatura','')}</td><td style='{nota_color(n1)}'>{n1}</td><td style='{nota_color(n2)}'>{n2}</td></tr>"
    if not sel_html: sel_html="<tr><td colspan=4>Sin notas</td></tr>"
    return render_template_string(BASE, content=f"<div class='d-flex gap-2 mb-2'><a href='/alumnos' class='btn btn-secondary btn-sm'>Volver Listado</a><a href='/dashboard' class='btn btn-warning btn-sm'>Menu Principal</a><a href='/alumno/{id}/editar' class='btn btn-warning btn-sm'>Editar</a><a href='/alumno/{id}/notas' class='btn btn-primary btn-sm'>Boletin</a><a href='/alumno/{id}/selectividad' class='btn btn-dark btn-sm'>Selectividad</a></div><div class='row'><div class='col-md-8'><h4>{d['nombre']} {d['apellidos']} ({d['codigo_alumno']}) - {curso_actual}</h4><h5>Notas (rojo si &lt;5)</h5><form method='post' action='/alumno/{id}/notas_trimestre/guardar'><table class='table table-bordered table-sm'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>{trim_html}</table><button class='btn btn-success'>Guardar Notas</button></form><hr><h5>Selectividad - Nota Fase 1 y 2</h5><table class='table table-bordered'><tr><th>Fase</th><th>Asignatura</th><th>Nota Fase 1</th><th>Nota Fase 2</th></tr>{sel_html}</table></div><div class='col-md-4 text-center'>{foto_html}<br><br><img src='{qr}' style='width:180px'></div></div>")

@app.route('/alumno/<int:id>/notas_trimestre/guardar', methods=['POST'])
def guardar_trimestres(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
    import json
    datos={}
    for k,v in request.form.items():
        if k.startswith(('T1_','T2_','T3_','JUN_')):
            parts=k.split('_',1); trim=parts[0]; mat=parts[1]
            if mat not in datos: datos[mat]={}
            datos[mat][trim]=v.strip()
    json_data=json.dumps(datos, ensure_ascii=False)
    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=?"), (d['codigo_alumno'],))
    existe=cur.fetchone()
    if existe: cur.execute(adapt("UPDATE notas_trimestres SET datos=? WHERE alumno_codigo=?"), (json_data, d['codigo_alumno']))
    else: cur.execute(adapt("INSERT INTO notas_trimestres (alumno_codigo, curso, datos, centro_codigo) VALUES (?,?,?,?)"), (d['codigo_alumno'], d.get('curso',''), json_data, d['centro_codigo']))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect(f'/alumno/{id}')

@app.route('/consulta', methods=['GET','POST'])
def consulta():
    codigo=request.args.get('codigo') or request.form.get('codigo')
    alumno=None; nt_data=None; sel_data=[]
    if codigo:
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("SELECT * FROM alumnos WHERE codigo_alumno=?"), (codigo.strip(),))
        alumno=cur.fetchone()
        if not alumno:
            cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE codigo_alumno=?"), (codigo.strip(),))
            alumno=cur.fetchone()
        if alumno:
            ad=dict(alumno) if isinstance(alumno,dict) else {'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4], 'foto':alumno[11] if len(alumno)>10 else alumno[3]}
            cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=?"), (ad['codigo_alumno'],))
            nt_data=cur.fetchone()
            cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (ad['codigo_alumno'],))
            sel_data=cur.fetchall()
        try: cur.close(); conn.close()
        except: pass
    content=f"<h3 class='text-center'>Consulta Publica V28.3 - Alumno ve TODO</h3><form method='post' class='d-flex justify-content-center gap-2 mt-4'><input name='codigo' value='{codigo or ''}' placeholder='Codigo Alumno' class='form-control' style='max-width:350px' required><button class='btn btn-primary'>Buscar</button></form>"
    if codigo and not alumno: content+=f"<div class='alert alert-danger mt-4 text-center'>Codigo {codigo} no encontrado</div>"
    if alumno:
        d=dict(alumno) if isinstance(alumno,dict) else {'nombre':alumno[1],'apellidos':alumno[2],'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4],'centro':alumno[8] if len(alumno)>8 else alumno[5],'foto':alumno[11] if len(alumno)>10 else alumno[3],'curso':alumno[13] if len(alumno)>13 else '', 'lugar_nacimiento':alumno[3] if len(alumno)>10 else '', 'anio':alumno[9] if len(alumno)>10 else ''}
        foto_url = f"/fotos/{d.get('foto')}" if d.get('foto') else ""
        foto_html = f"<img src='{foto_url}' style='width:180px;border-radius:10px;border:2px solid #ddd' onerror=\"this.outerHTML='<small>Sin foto / foto no encontrada</small>'\">" if foto_url else "<small>Sin foto</small>"
        import json
        html=""
        # Info personal
        html+=f"<div class='mb-3'><b>Nombre:</b> {d.get('nombre')} {d.get('apellidos')}<br><b>Codigo:</b> {d.get('codigo_alumno')} | <b>Centro:</b> {d.get('centro')} | <b>Curso:</b> {d.get('curso')} | <b>Anio:</b> {d.get('anio','')}</div><hr>"
        if nt_data:
            nd=dict(nt_data) if isinstance(nt_data,dict) else {'datos':nt_data[3],'curso':nt_data[2]}
            try:
                datos=json.loads(nd.get('datos') or '{}')
                html+=f"<h5>Notas Trimestrales - {nd.get('curso','')}</h5><table class='table table-bordered'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
                for mat,vals in datos.items():
                    def st(v):
                        try:
                            if not v: return ""
                            return "color:red;font-weight:bold;background:#ffe0e0" if float(str(v).replace(',','.'))<5 else "color:green;font-weight:bold"
                        except: return ""
                    html+=f"<tr><td>{mat}</td><td style='{st(vals.get('T1',''))}'>{vals.get('T1','')}</td><td style='{st(vals.get('T2',''))}'>{vals.get('T2','')}</td><td style='{st(vals.get('T3',''))}'>{vals.get('T3','')}</td><td style='{st(vals.get('JUN',''))}'><b>{vals.get('JUN','')}</b></td></tr>"
                html+="</table>"
            except: pass
        if sel_data:
            html+="<h5 class='mt-4'>SELECTIVIDAD - 2 FASES (Bachillerato) - Nota Fase 1 y Nota Fase 2</h5><table class='table table-bordered'><tr><th>Fase</th><th>Bloque</th><th>Asignatura</th><th>Nota Fase 1</th><th>Nota Fase 2</th></tr>"
            for s in sel_data:
                sd=dict(s) if isinstance(s,dict) else {}
                if sd: n1=sd.get('nota',''); n2=sd.get('nota2',''); fase=sd.get('fase',''); asig=sd.get('asignatura',''); bloque=sd.get('bloque','')
                else: n1=s[4] if len(s)>4 else ''; n2=s[5] if len(s)>5 else ''; fase=s[2] if len(s)>2 else ''; asig=s[3] if len(s)>3 else ''; bloque=s[8] if len(s)>8 else ''
                html+=f"<tr><td><b>{fase}</b></td><td>{bloque}</td><td>{asig}</td><td style='{nota_color(n1)}'>{n1}</td><td style='{nota_color(n2)}'>{n2}</td></tr>"
            html+="</table><p><small style='color:red'>Notas en rojo = suspenso &lt;5 - Notas en verde = aprobado</small></p>"
        else:
            html+="<div class='alert alert-warning mt-3'>Este alumno aun no tiene notas de Selectividad cargadas (solo para Bachillerato)</div>"
        if not html or len(html)<50: html="<div class='alert alert-info'>Aun no tiene notas cargadas</div>"
        content+=f"<div class='card p-4 mt-4 shadow'><div class='row'><div class='col-md-8'>{html}</div><div class='col-md-4 text-center'><div class='card p-2'><b>Foto del Alumno</b><br><div class='mt-2'>{foto_html}</div></div><br><button onclick='window.print()' class='btn btn-primary w-100'>Imprimir / Guardar PDF</button></div></div></div>"
    return render_template_string(BASE, content=content)

@app.route('/fotos/<path:filename>')
def fotos(filename): return send_from_directory(UPLOAD_FOLDER, filename)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
