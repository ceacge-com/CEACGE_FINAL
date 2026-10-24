import os, secrets, io, base64, json
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'CEACGE-V28-11-HISTORIAL-OK'
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
    "1 BACH - Ciencias": ["Lengua y Literatura","Matematicas I","Fisica","Quimica","Biologia","Ingles","Filosofia","Ed. Fisica","Informatica","Historia de Africa y de G.E","Literatura Universal"],
    "1 BACH - Letras": ["Lengua y Literatura","Historia del Mundo","Filosofia","Literatura Universal","Ingles","Frances","Geografia Humana","Economia","Latin","Historia de Africa y de G.E"],
    "1 BACH - Tecnico": ["Lengua y Literatura","Matematicas Aplicadas","Contabilidad","Economia de Empresa","Informatica de Gestion","Ingles","Filosofia","Tecnologia Industrial"],
    "2 BACH - Ciencias": ["Lengua y Literatura","Matematicas II","Fisica II","Quimica II","Biologia II","Ingles II","Historia de GE","Filosofia II","Lengua Espanola","Historia","Historia de la Filosofia","Idioma"],
    "2 BACH - Letras": ["Lengua y Literatura II","Historia de GE","Filosofia II","Literatura Espanola","Ingles II","Latin II","Geografia de GE","Historia del Arte","Lengua Espanola","Historia","Idioma"],
    "2 BACH - Tecnico": ["Matematicas Financieras","Contabilidad II","Informatica II","Economia y Organizacion","Derecho Empresarial","Ingles II","Historia de GE","Proyecto Final"],
}
ANIOS_ACADEMICOS = ["1 ESBA","2 ESBA","3 ESBA","4 ESBA","1 BACH - Ciencias","1 BACH - Letras","1 BACH - Tecnico","2 BACH - Ciencias","2 BACH - Letras","2 BACH - Tecnico"]

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
        return f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(txt)}"
def get_foto_html(d, width=220, height=270):
    foto_nombre = d.get('foto') if isinstance(d,dict) else None
    foto_data = d.get('foto_data') if isinstance(d,dict) else None
    if foto_data and len(foto_data) > 100:
        if foto_data.startswith('data:'): return f"<img src='{foto_data}' style='width:{width}px;height:{height}px;object-fit:cover;border-radius:8px;border:3px solid #0d6efd'>"
        else: return f"<img src='data:image/jpeg;base64,{foto_data}' style='width:{width}px;height:{height}px;object-fit:cover;border-radius:8px;border:3px solid #0d6efd'>"
    if foto_nombre:
        ruta = os.path.join(UPLOAD_FOLDER, foto_nombre)
        if os.path.exists(ruta): return f"<img src='/fotos/{foto_nombre}' style='width:{width}px;height:{height}px;object-fit:cover;border-radius:8px;border:3px solid #0d6efd'>"
    return "<div class='border p-5 text-muted text-center' style='width:220px'>Sin foto</div>"

def init_db():
    conn=get_conn(); cur=conn.cursor()
    try:
        if USE_PG:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT, observaciones TEXT, foto_data TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT, foto_data TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas_trimestres (id SERIAL PRIMARY KEY, alumno_codigo TEXT, curso TEXT, datos TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas_historico (id SERIAL PRIMARY KEY, alumno_codigo TEXT, anio_academico TEXT, curso TEXT, datos TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS selectividad (id SERIAL PRIMARY KEY, alumno_codigo TEXT, fase TEXT, asignatura TEXT, nota TEXT, nota2 TEXT, convocatoria TEXT, centro_codigo TEXT, bloque TEXT)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT, observaciones TEXT, foto_data TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT, foto_data TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas_trimestres (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_codigo TEXT, curso TEXT, datos TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas_historico (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_codigo TEXT, anio_academico TEXT, curso TEXT, datos TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS selectividad (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_codigo TEXT, fase TEXT, asignatura TEXT, nota TEXT, nota2 TEXT, convocatoria TEXT, centro_codigo TEXT, bloque TEXT)")
        cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
        if not cur.fetchone():
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
        conn.commit()
    except Exception as e: print(e)
    finally:
        try: cur.close(); conn.close()
        except: pass
init_db()

BASE="<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CEACGE</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body><nav class='navbar navbar-dark bg-primary'><div class='container'><a class='navbar-brand' href='/dashboard'>CEACGE V28.11</a><div><a href='/dashboard' class='btn btn-sm btn-warning me-2'>Menu</a><a href='/consulta' class='btn btn-sm btn-light me-2'>Consulta</a><span class='text-white me-2'>{{session.usuario}} ({{session.rol}})</span><a href='/logout' class='text-white'>Salir</a></div></div></nav><div class='container mt-4'>{{content|safe}}</div></body></html>"

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
    return render_template_string("<html><head><meta charset='utf-8'><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'></head><body class='bg-light'><div class='container d-flex justify-content-center align-items-center vh-100'><div class='card p-4' style='width:360px'><h4 class='text-center'>CEACGE V28.11</h4>{% if err %}<div class='alert alert-danger'>{{err}}</div>{% endif %}<form method='post'><input class='form-control mb-2' name='usuario' placeholder='Usuario' required><input class='form-control mb-3' type='password' name='password' placeholder='Pass' required><button class='btn btn-primary w-100'>Entrar</button></form><hr><a href='/consulta' class='btn btn-outline-secondary w-100'>Consulta por Codigo</a></div></div></body></html>", err=err)
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
    return render_template_string(BASE, content=f"<h3>Panel {session['usuario']}</h3><div class='row g-3 mt-2'><div class='col-md-4'><div class='card p-3'><h5>Secundaria y Bach</h5><h2>{sec}</h2><a href='/alumnos' class='btn btn-primary btn-sm'>Ver</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Primaria</h5><h2>{pri}</h2><a href='/primaria' class='btn btn-success btn-sm'>Ver</a></div></div><div class='col-md-4'><div class='card p-3'><h5>Centros</h5><h2>{cen}</h2><a href='/centros' class='btn btn-warning btn-sm'>Ver</a></div></div></div><div class='mt-4'><a href='/alumnos/nuevo' class='btn btn-primary'>+ Sec/Bach</a> <a href='/centros/nuevo' class='btn btn-warning'>+ Centro</a> <a href='/usuarios' class='btn btn-dark'>Usuarios</a></div>")

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
        html+=f"<tr><td><b>{d['codigo_alumno']}</b></td><td>{d['nombre']} {d['apellidos']}</td><td><a href='/alumno/{d['id']}' class='btn btn-sm btn-primary'>Ver</a> <a href='/alumno/{d['id']}/editar' class='btn btn-sm btn-warning'>Editar</a> <a href='/alumno/{d['id']}/selectividad' class='btn btn-sm btn-dark'>Selectividad</a> <a href='/alumno/{d['id']}/eliminar' class='btn btn-sm btn-danger' onclick=\"return confirm('Eliminar a {d['nombre']}?')\">Eliminar</a></td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)

@app.route('/alumnos/nuevo', methods=['GET','POST'])
def alumno_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        f=request.form; codigo=f.get('codigo_alumno','').strip() or gen_codigo("SEC")
        foto_name=None; foto_data_b64=None
        if 'foto' in request.files:
            up=request.files['foto']
            if up.filename:
                foto_name=secure_filename(f"{codigo}_{up.filename}")
                file_bytes = up.read()
                try: open(os.path.join(UPLOAD_FOLDER, foto_name), 'wb').write(file_bytes)
                except: pass
                try: foto_data_b64 = base64.b64encode(file_bytes).decode()
                except: pass
        cc=session.get('centro_codigo') if session.get('rol')!='admin' else f.get('centro_codigo') or f.get('centro')
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,lugar_nacimiento,distrito,provincia,telefono,email,centro,anio,codigo_alumno,foto,centro_codigo,curso,observaciones,foto_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"), (f.get('nombre'),f.get('apellidos'),f.get('lugar_nacimiento'),f.get('distrito'),f.get('provincia'),f.get('telefono'),f.get('email'),f.get('centro'),f.get('anio'),codigo,foto_name,cc,f.get('curso'),f.get('observaciones'),foto_data_b64))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect('/alumnos')
    extra = "<input name='centro_codigo' placeholder='Codigo centro' class='form-control mb-2'>" if session.get('rol')=='admin' else ""
    return render_template_string(BASE, content=f"<a href='/alumnos' class='btn btn-secondary btn-sm'>Volver</a><h4>Nuevo Sec/Bach</h4><form method='post' enctype='multipart/form-data' class='row g-2'><div class='col-md-6'><input name='nombre' class='form-control' placeholder='Nombre' required></div><div class='col-md-6'><input name='apellidos' class='form-control' placeholder='Apellidos' required></div><div class='col-md-4'><input name='lugar_nacimiento' class='form-control' placeholder='Lugar Nac'></div><div class='col-md-4'><input name='distrito' class='form-control' placeholder='Distrito'></div><div class='col-md-4'><input name='provincia' class='form-control' placeholder='Provincia'></div><div class='col-md-4'><input name='telefono' class='form-control' placeholder='Contacto'></div><div class='col-md-4'><input name='email' class='form-control' placeholder='Email'></div><div class='col-md-4'><select name='curso' class='form-control'><option>1 ESBA</option><option>2 ESBA</option><option>3 ESBA</option><option>4 ESBA</option><option>1 BACH - Ciencias</option><option>2 BACH - Ciencias</option></select></div><div class='col-md-4'><input name='centro' class='form-control' placeholder='Centro'></div><div class='col-md-2'><input name='anio' class='form-control' value='2026-2027'></div><div class='col-md-3'><input name='codigo_alumno' class='form-control' placeholder='Codigo'></div><div class='col-md-3'>{extra}</div><div class='col-12'><textarea name='observaciones' class='form-control' placeholder='Observaciones'></textarea></div><div class='col-md-6'><input type='file' name='foto' class='form-control'></div><div class='col-12'><button class='btn btn-primary'>Guardar</button></div></form>")

@app.route('/alumno/<int:id>/editar', methods=['GET','POST'])
def alumno_editar(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'lugar_nacimiento':r[3],'distrito':r[4],'provincia':r[5],'telefono':r[6],'email':r[7],'centro':r[8],'anio':r[9],'codigo_alumno':r[10],'foto':r[11],'centro_codigo':r[12],'curso':r[13],'observaciones':r[14] if len(r)>14 else '', 'foto_data':r[15] if len(r)>15 else ''}
    if request.method=='POST':
        f=request.form; foto_name=d.get('foto'); foto_data_b64=d.get('foto_data')
        if 'foto' in request.files:
            up=request.files['foto']
            if up.filename:
                foto_name=secure_filename(f"{d.get('codigo_alumno')}_{up.filename}"); file_bytes=up.read()
                try: open(os.path.join(UPLOAD_FOLDER, foto_name), 'wb').write(file_bytes)
                except: pass
                try: foto_data_b64=base64.b64encode(file_bytes).decode()
                except: pass
        cur.execute(adapt("UPDATE alumnos SET nombre=?, apellidos=?, lugar_nacimiento=?, distrito=?, provincia=?, telefono=?, email=?, centro=?, anio=?, curso=?, centro_codigo=?, observaciones=?, foto=?, foto_data=? WHERE id=?"), (f.get('nombre'),f.get('apellidos'),f.get('lugar_nacimiento'),f.get('distrito'),f.get('provincia'),f.get('telefono'),f.get('email'),f.get('centro'),f.get('anio'),f.get('curso'),f.get('centro_codigo') or d['centro_codigo'], f.get('observaciones'), foto_name, foto_data_b64, id))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect(f'/alumno/{id}')
    try: cur.close(); conn.close()
    except: pass
    return render_template_string(BASE, content=f"<a href='/alumno/{id}' class='btn btn-secondary btn-sm'>Volver</a><h4>Editar {d['codigo_alumno']}</h4><form method='post' enctype='multipart/form-data' class='row g-2'><div class='col-md-6'><input name='nombre' value='{d.get('nombre','')}' class='form-control'></div><div class='col-md-6'><input name='apellidos' value='{d.get('apellidos','')}' class='form-control'></div><div class='col-md-4'><input name='lugar_nacimiento' value='{d.get('lugar_nacimiento','')}' class='form-control'></div><div class='col-md-4'><input name='distrito' value='{d.get('distrito','')}' class='form-control'></div><div class='col-md-4'><input name='provincia' value='{d.get('provincia','')}' class='form-control'></div><div class='col-md-4'><input name='telefono' value='{d.get('telefono','')}' class='form-control'></div><div class='col-md-4'><input name='email' value='{d.get('email','')}' class='form-control'></div><div class='col-md-4'><input name='curso' value='{d.get('curso','')}' class='form-control'></div><div class='col-md-4'><input name='centro' value='{d.get('centro','')}' class='form-control'></div><div class='col-md-4'><input name='anio' value='{d.get('anio','')}' class='form-control'></div><div class='col-md-4'><input name='centro_codigo' value='{d.get('centro_codigo','')}' class='form-control'></div><div class='col-12'><textarea name='observaciones' class='form-control'>{d.get('observaciones','')}</textarea></div><div class='col-md-6'><input type='file' name='foto' class='form-control'></div><div class='col-12'><button class='btn btn-success'>Guardar</button></div></form>")

@app.route('/alumno/<int:id>/eliminar')
def alumno_eliminar(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
        if r:
            d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10]}; codigo=d.get('codigo_alumno')
            cur.execute(adapt("DELETE FROM notas_historico WHERE alumno_codigo=?"), (codigo,))
            cur.execute(adapt("DELETE FROM notas_trimestres WHERE alumno_codigo=?"), (codigo,))
            cur.execute(adapt("DELETE FROM selectividad WHERE alumno_codigo=?"), (codigo,))
            cur.execute(adapt("DELETE FROM alumnos WHERE id=?"), (id,))
            conn.commit()
    except Exception as e: print(e)
    finally:
        try: cur.close(); conn.close()
        except: pass
    return redirect('/alumnos')

@app.route('/alumno/<int:id>')
def alumno_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13],'foto':r[11],'centro_codigo':r[12],'anio':r[9],'observaciones':r[14] if len(r)>14 else '', 'foto_data':r[15] if len(r)>15 else ''}
    cur.execute(adapt("SELECT * FROM notas_historico WHERE alumno_codigo=? ORDER BY anio_academico"), (d['codigo_alumno'],)); hist_rows=cur.fetchall()
    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=? ORDER BY curso"), (d['codigo_alumno'],)); old_rows=cur.fetchall()
    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (d['codigo_alumno'],)); sel_rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    qr=gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html=get_foto_html(d, 150, 200)
    hist_html=""
    # Primero historial nuevo
    for hr in hist_rows:
        h=dict(hr) if isinstance(hr,dict) else {'anio_academico':hr[2],'curso':hr[3],'datos':hr[4]}
        try:
            datos=json.loads(h.get('datos') or '{}')
            if not datos: continue
            hist_html+=f"<div class='card p-2 mb-2 border-primary'><b>Año: {h.get('anio_academico')} - {h.get('curso')}</b><table class='table table-sm'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
            for mat,vals in datos.items():
                def _col(v):
                    try:
                        if not v: return ""
                        return "color:#d00000;font-weight:bold;background:#ffe0e0" if float(str(v).replace(',','.'))<5 else "color:#0a7d00;font-weight:bold;background:#e7f3ff"
                    except: return ""
                hist_html+=f"<tr><td>{mat}</td><td style='{_col(vals.get('T1',''))}'>{vals.get('T1','')}</td><td style='{_col(vals.get('T2',''))}'>{vals.get('T2','')}</td><td style='{_col(vals.get('T3',''))}'>{vals.get('T3','')}</td><td style='{_col(vals.get('JUN',''))}'><b>{vals.get('JUN','')}</b></td></tr>"
            hist_html+="</table></div>"
        except: pass
    # Si no hay historial nuevo, mostrar el viejo ya registrado
    if not hist_html:
        for hr in old_rows:
            h=dict(hr) if isinstance(hr,dict) else {'curso':hr[2] if len(hr)>2 else '', 'datos':hr[3] if len(hr)>3 else ''}
            try:
                datos=json.loads(h.get('datos') or '{}')
                if not datos: continue
                hist_html+=f"<div class='card p-2 mb-2 border-success'><b>Historial registrado: {h.get('curso')} (antiguo)</b><table class='table table-sm'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
                for mat,vals in datos.items():
                    if isinstance(vals, dict):
                        def _col(v):
                            try:
                                if not v: return ""
                                return "color:#d00000;font-weight:bold;background:#ffe0e0" if float(str(v).replace(',','.'))<5 else "color:#0a7d00;font-weight:bold;background:#e7f3ff"
                            except: return ""
                        hist_html+=f"<tr><td>{mat}</td><td style='{_col(vals.get('T1',''))}'>{vals.get('T1','')}</td><td style='{_col(vals.get('T2',''))}'>{vals.get('T2','')}</td><td style='{_col(vals.get('T3',''))}'>{vals.get('T3','')}</td><td style='{_col(vals.get('JUN',''))}'><b>{vals.get('JUN','')}</b></td></tr>"
                    else:
                        hist_html+=f"<tr><td>{mat}</td><td colspan=4><b>{vals}</b></td></tr>"
                hist_html+="</table></div>"
            except: pass
    if not hist_html: hist_html="<div class='alert alert-warning'>Sin historial - Añade notas abajo</div>"
    options_anio = "".join([f"<option value='{a}'>{a}</option>" for a in ANIOS_ACADEMICOS])
    form_html = f"<div class='card p-3 mt-4 border-primary'><h5>Añadir Notas Año</h5><form method='post' action='/alumno/{id}/notas_historico/guardar'><select name='anio_academico' class='form-control mb-2'>{options_anio}</select><input name='curso_detalle' class='form-control mb-2' placeholder='Curso'><div id='materiasContainer'></div><button class='btn btn-success mt-2'>Guardar</button></form></div><script>const PLAN={json.dumps(PLAN)};function cargar(){{let s=document.querySelector('select[name=anio_academico]').value;let m=PLAN[s]||[];let h=\"<table class='table table-sm'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>\";m.forEach(x=>{{h+=`<tr><td>${{x}}</td><td><input name='T1_${{x}}' class='form-control form-control-sm'></td><td><input name='T2_${{x}}' class='form-control form-control-sm'></td><td><input name='T3_${{x}}' class='form-control form-control-sm'></td><td><input name='JUN_${{x}}' class='form-control form-control-sm'></td></tr>`}});h+=\"</table>\";document.getElementById('materiasContainer').innerHTML=h}}document.querySelector('select[name=anio_academico]').addEventListener('change',cargar);cargar();</script>"
    return render_template_string(BASE, content=f"<div class='d-flex gap-2 mb-2'><a href='/alumnos' class='btn btn-secondary btn-sm'>Volver</a><a href='/alumno/{id}/editar' class='btn btn-warning btn-sm'>Editar</a><a href='/alumno/{id}/selectividad' class='btn btn-dark btn-sm'>Selectividad</a><a href='/alumno/{id}/eliminar' class='btn btn-danger btn-sm' onclick=\"return confirm('Eliminar definitivamente?')\">Eliminar Alumno</a></div><div class='row mt-3'><div class='col-md-8'><h4>{d['nombre']} {d['apellidos']} ({d['codigo_alumno']})</h4>{hist_html}{form_html}</div><div class='col-md-4 text-center'>{foto_html}<br><br><img src='{qr}' style='width:180px'></div></div>")

@app.route('/alumno/<int:id>/notas_historico/guardar', methods=['POST'])
def guardar_historico(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
    anio_acad = request.form.get('anio_academico') or ''
    curso_det = request.form.get('curso_detalle') or anio_acad
    datos={}
    for k,v in request.form.items():
        if k.startswith(('T1_','T2_','T3_','JUN_')):
            parts=k.split('_',1); trim=parts[0]; mat=parts[1]
            if mat not in datos: datos[mat]={}
            datos[mat][trim]=v.strip()
    datos = {m:vals for m,vals in datos.items() if any(vals.values())}
    json_data=json.dumps(datos, ensure_ascii=False)
    cur.execute(adapt("SELECT * FROM notas_historico WHERE alumno_codigo=? AND anio_academico=?"), (d['codigo_alumno'], anio_acad))
    existe=cur.fetchone()
    if existe: cur.execute(adapt("UPDATE notas_historico SET datos=?, curso=? WHERE alumno_codigo=? AND anio_academico=?"), (json_data, curso_det, d['codigo_alumno'], anio_acad))
    else: cur.execute(adapt("INSERT INTO notas_historico (alumno_codigo, anio_academico, curso, datos, centro_codigo) VALUES (?,?,?,?,?)"), (d['codigo_alumno'], anio_acad, curso_det, json_data, d['centro_codigo']))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect(f'/alumno/{id}')

@app.route('/alumno/<int:id>/selectividad')
def alumno_selectividad(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10]}
    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (d['codigo_alumno'],)); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html_rows=""
    for s in rows:
        sd=dict(s) if isinstance(s,dict) else {}
        if sd: n1=sd.get('nota',''); n2=sd.get('nota2',''); sid=sd.get('id',''); fase=sd.get('fase',''); asig=sd.get('asignatura',''); bloque=sd.get('bloque',''); conv=sd.get('convocatoria','')
        else: sid=s[0]; fase=s[2]; asig=s[3]; n1=s[4]; n2=s[5]; bloque=s[8] if len(s)>8 else ''; conv=s[6] if len(s)>6 else ''
        etiqueta = ""
        if n1 and not n2: etiqueta="<span class='badge bg-primary'>Fase 1</span>"
        elif n2 and not n1: etiqueta="<span class='badge bg-success'>Fase 2</span>"
        elif n1 and n2: etiqueta="<span class='badge bg-dark'>Fase 1 y 2</span>"
        html_rows+=f"<tr><td><b>{fase}</b><br><small>{bloque}</small><br>{etiqueta}</td><td>{asig}<br><small>{conv}</small></td><td style='{nota_color(n1)}'><b>{n1}</b></td><td style='{nota_color(n2)}'><b>{n2}</b></td><td><a href='/selectividad/{sid}/borrar' class='btn btn-sm btn-danger'>Borrar</a></td></tr>"
    if not html_rows: html_rows="<tr><td colspan=5>Sin datos</td></tr>"
    page = f"<a href='/alumno/{id}' class='btn btn-secondary btn-sm'>Volver</a><h4 class='mt-3'>Selectividad - {d['nombre']} {d['apellidos']} - Fase 1 en Fase 1, Fase 2 en Fase 2</h4><div class='card p-3 mt-3'><table class='table table-bordered'><tr><th>Fase</th><th>Asignatura</th><th>Nota F1</th><th>Nota F2</th><th></th></tr>{html_rows}</table><hr><h5>Anadir Nota</h5><form method='post' action='/alumno/{id}/selectividad/add' class='row g-2'><div class='col-md-2'><select name='fase' id='faseSel' class='form-control' onchange='cambiar()'><option value='GENERAL'>Fase General</option><option value='ESPECIAL'>Fase Especial</option></select></div><div class='col-md-3'><select name='asignatura_bloque' id='asigSel' class='form-control'></select></div><div class='col-md-2'><select name='tipo_fase' class='form-control'><option value='FASE1'>Fase 1</option><option value='FASE2'>Fase 2</option><option value='AMBAS'>Ambas</option></select></div><div class='col-md-1'><input name='nota' class='form-control' placeholder='F1'></div><div class='col-md-1'><input name='nota2' class='form-control' placeholder='F2'></div><div class='col-md-3'><input name='convocatoria' class='form-control' value='Junio 2025'></div><div class='col-12'><button class='btn btn-dark'>Guardar</button></div></form></div><script>const generalList=[\"Lengua Espanola\",\"Historia\",\"Historia de la Filosofia\",\"Idioma\"];const especialBloques={{\"BLOQUE 1\":[\"Historia de Africa y de G.E\",\"Literatura Universal\",\"Historia de Arte\",\"Geografia\",\"Matematicas Aplicadas a CS\",\"Latin\",\"Griego\"],\"BLOQUE 2\":[\"Matematicas\",\"Fisica\",\"Quimica\",\"Dibujo Tecnico\",\"Informatica\",\"Tecnologia Industrial\",\"Electrotecnia\"],\"BLOQUE 3\":[\"Biologia y Geologia\",\"C.N y Salud\",\"Fisica y Quimica\"]}};function cambiar(){{let fase=document.getElementById('faseSel').value;let sel=document.getElementById('asigSel');sel.innerHTML='';if(fase==='GENERAL'){{generalList.forEach(m=>{{let o=document.createElement('option');o.value=m;o.text=m;sel.add(o)}})}}else{{for(const [b,mats] of Object.entries(especialBloques)){{let g=document.createElement('optgroup');g.label=b;mats.forEach(m=>{{let o=document.createElement('option');o.value=m+'|'+b;o.text=m;g.appendChild(o)}});sel.appendChild(g)}}}}cambiar();</script>"
    return render_template_string(BASE, content=page)

@app.route('/alumno/<int:id>/selectividad/add', methods=['POST'])
def selectividad_add(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone(); d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
    fase_raw=request.form.get('fase') or 'GENERAL'; asig_bloque=request.form.get('asignatura_bloque') or ''; tipo_fase=request.form.get('tipo_fase') or 'FASE1'
    bloque=""; asignatura=asig_bloque
    if '|' in asig_bloque: asignatura,bloque=asig_bloque.split('|',1)
    fase_nombre="Fase General" if fase_raw=="GENERAL" else "Fase Especial"
    nota1=request.form.get('nota','').strip(); nota2=request.form.get('nota2','').strip()
    if tipo_fase=='FASE1': nf1,nf2=nota1 or nota2,""
    elif tipo_fase=='FASE2': nf1,nf2="",nota2 or nota1
    else: nf1,nf2=nota1,nota2
    cur.execute(adapt("INSERT INTO selectividad (alumno_codigo, fase, asignatura, nota, nota2, convocatoria, centro_codigo, bloque) VALUES (?,?,?,?,?,?,?,?)"), (d['codigo_alumno'], fase_nombre, asignatura, nf1, nf2, request.form.get('convocatoria'), d['centro_codigo'], bloque))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect(f'/alumno/{id}/selectividad')

@app.route('/selectividad/<int:sid>/borrar')
def selectividad_borrar(sid):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("DELETE FROM selectividad WHERE id=?"), (sid,)); conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect('/alumnos')

@app.route('/usuarios', methods=['GET','POST'])
def usuarios():
    if 'usuario' not in session: return redirect('/login')
    if session.get('rol') != 'admin':
        return render_template_string(BASE, content="<div class='alert alert-danger'><h4>Solo admin puede ver usuarios</h4><p>Tu rol actual es: "+session.get('rol','')+" - Necesitas entrar con usuario <b>admin</b></p><a href='/dashboard' class='btn btn-primary'>Volver</a></div>")
    conn=get_conn(); cur=conn.cursor()
    if request.method=='POST':
        u=request.form.get('usuario'); p=request.form.get('password'); rol=request.form.get('rol'); cc=request.form.get('centro_codigo')
        try:
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"), (u, generate_password_hash(p), rol, cc))
            conn.commit()
        except Exception as e: print(e)
    cur.execute("SELECT * FROM usuarios ORDER BY id")
    rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html="<h4>Usuarios - CEACGE</h4><table class='table'><tr><th>Usuario</th><th>Rol</th><th>Centro Codigo</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'usuario':r[1],'rol':r[3],'centro_codigo':r[4]}
        html+=f"<tr><td>{d['usuario']}</td><td>{d['rol']}</td><td>{d['centro_codigo']}</td></tr>"
    html+="</table><hr><h5>Crear Usuario</h5><form method='post' class='row g-2'><div class='col-md-3'><input name='usuario' placeholder='Usuario' class='form-control' required></div><div class='col-md-3'><input name='password' placeholder='Password' class='form-control' required></div><div class='col-md-2'><select name='rol' class='form-control'><option value='admin'>admin</option><option value='centro'>centro</option></select></div><div class='col-md-2'><input name='centro_codigo' placeholder='Codigo centro' class='form-control'></div><div class='col-md-2'><button class='btn btn-dark'>Crear</button></div></form>"
    return render_template_string(BASE, content=html)

@app.route('/centros')
def centros():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM centros ORDER BY id DESC"); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html="<h4>Centros</h4><table class='table'><tr><th>Nombre</th><th>Codigo</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'nombre':r[1],'codigo':r[2]}
        html+=f"<tr><td>{d['nombre']}</td><td>{d['codigo']}</td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)

@app.route('/centros/nuevo', methods=['GET','POST'])
def centro_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if session.get('rol')!='admin': return render_template_string(BASE, content="<div class='alert alert-danger'>Solo admin</div>")
    if request.method=='POST':
        codigo=request.form.get('codigo') or gen_codigo("CEN")
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email) VALUES (?,?,?,?,?)"), (request.form.get('nombre'),codigo,request.form.get('localidad'),request.form.get('contacto'),request.form.get('email')))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect('/centros')
    return render_template_string(BASE, content="<h4>Nuevo Centro</h4><form method='post'><input name='nombre' placeholder='Nombre' class='form-control mb-2' required><input name='codigo' placeholder='Codigo' class='form-control mb-2'><input name='localidad' placeholder='Localidad' class='form-control mb-2'><input name='contacto' placeholder='Contacto' class='form-control mb-2'><input name='email' placeholder='Email' class='form-control mb-2'><button class='btn btn-warning'>Guardar</button></form>")

@app.route('/consulta', methods=['GET','POST'])
def consulta():
    codigo=request.args.get('codigo') or request.form.get('codigo')
    alumno=None; sel_data=[]; hist_rows=[]; old_rows=[]
    if codigo:
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("SELECT * FROM alumnos WHERE codigo_alumno=?"), (codigo.strip(),))
        alumno=cur.fetchone()
        if alumno:
            ad=dict(alumno) if isinstance(alumno,dict) else {'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4]}
            cur.execute(adapt("SELECT * FROM notas_historico WHERE alumno_codigo=? ORDER BY anio_academico"), (ad['codigo_alumno'],))
            hist_rows=cur.fetchall()
            cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=? ORDER BY curso"), (ad['codigo_alumno'],))
            old_rows=cur.fetchall()
            cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (ad['codigo_alumno'],))
            sel_data=cur.fetchall()
        try: cur.close(); conn.close()
        except: pass
    content=f"<h3 class='text-center'>Consulta Publica V28.11</h3><form method='post' class='d-flex justify-content-center gap-2 mt-3'><input name='codigo' value='{codigo or ''}' placeholder='Codigo Alumno' class='form-control' style='max-width:350px' required><button class='btn btn-primary'>Buscar</button></form>"
    if codigo and not alumno: content+=f"<div class='alert alert-danger mt-4 text-center'>Codigo {codigo} no encontrado</div>"
    if alumno:
        d=dict(alumno) if isinstance(alumno,dict) else {'nombre':alumno[1],'apellidos':alumno[2],'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4],'centro':alumno[8] if len(alumno)>8 else '', 'curso':alumno[13] if len(alumno)>13 else '', 'lugar_nacimiento':alumno[3],'distrito':alumno[4],'provincia':alumno[5],'telefono':alumno[6],'email':alumno[7],'anio':alumno[9] if len(alumno)>10 else '', 'observaciones':alumno[14] if len(alumno)>14 else '', 'foto':alumno[11] if len(alumno)>10 else '', 'foto_data':alumno[15] if len(alumno)>15 else ''}
        foto_html = get_foto_html(d, 220, 270)
        qr_img = gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d.get('codigo_alumno')}")
        html_datos = f"<div class='text-center mb-4'><b>Foto carnet</b><div class='mt-2'>{foto_html}</div></div><div class='text-center mb-4'><b>Codigo QR</b><div class='mt-2'><img src='{qr_img}' style='width:200px'></div><small>{d.get('codigo_alumno')}</small></div><div class='card p-3 bg-light'><b>Nombre:</b> {d.get('nombre')} {d.get('apellidos')}<br><b>Codigo:</b> {d.get('codigo_alumno')} | <b>Curso:</b> {d.get('curso')}<br><b>Lugar Nac:</b> {d.get('lugar_nacimiento','')} | <b>Distrito:</b> {d.get('distrito','')} | <b>Provincia:</b> {d.get('provincia','')}<br><b>Contacto:</b> {d.get('telefono','')} | <b>Email:</b> {d.get('email','')}<br><b>Centro:</b> {d.get('centro')} | <b>Año:</b> {d.get('anio','')}<br><b>Obs:</b> {d.get('observaciones','')}</div>"
        html_notas=""
        all_hist = hist_rows if hist_rows else old_rows
        for hr in all_hist:
            h=dict(hr) if isinstance(hr,dict) else {'anio_academico':hr[2] if len(hr)>2 else hr[2] if len(hr)>2 else '', 'curso':hr[3] if len(hr)>3 else hr[2], 'datos':hr[4] if len(hr)>4 else hr[3]}
            try:
                datos=json.loads(h.get('datos') or '{}')
                if not datos: continue
                titulo = h.get('anio_academico') or h.get('curso')
                html_notas+=f"<h5 class='mt-4'>Año academico: {titulo}</h5><table class='table table-bordered'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
                for mat,vals in datos.items():
                    def st(v):
                        try:
                            if not v: return ""
                            return "color:red;font-weight:bold;background:#ffe0e0" if float(str(v).replace(',','.'))<5 else "color:green;font-weight:bold"
                        except: return ""
                    if isinstance(vals, dict):
                        html_notas+=f"<tr><td>{mat}</td><td style='{st(vals.get('T1',''))}'>{vals.get('T1','')}</td><td style='{st(vals.get('T2',''))}'>{vals.get('T2','')}</td><td style='{st(vals.get('T3',''))}'>{vals.get('T3','')}</td><td style='{st(vals.get('JUN',''))}'><b>{vals.get('JUN','')}</b></td></tr>"
                    else:
                        html_notas+=f"<tr><td>{mat}</td><td colspan=4><b>{vals}</b></td></tr>"
                html_notas+="</table>"
            except: pass
        if sel_data:
            html_notas+="<h5 class='mt-4'>SELECTIVIDAD - Fase 1 y Fase 2</h5><table class='table table-bordered'><tr><th>Fase</th><th>Bloque</th><th>Asignatura</th><th>Nota F1</th><th>Nota F2</th></tr>"
            for s in sel_data:
                sd=dict(s) if isinstance(s,dict) else {}
                if sd: n1=sd.get('nota',''); n2=sd.get('nota2',''); fase=sd.get('fase',''); asig=sd.get('asignatura',''); bloque=sd.get('bloque','')
                else: n1=s[4] if len(s)>4 else ''; n2=s[5] if len(s)>5 else ''; fase=s[2] if len(s)>2 else ''; asig=s[3] if len(s)>3 else ''; bloque=s[8] if len(s)>8 else ''
                html_notas+=f"<tr><td><b>{fase}</b></td><td>{bloque}</td><td>{asig}</td><td style='{nota_color(n1)}'><b>{n1}</b></td><td style='{nota_color(n2)}'><b>{n2}</b></td></tr>"
            html_notas+="</table>"
        content+=f"<div class='card p-4 mt-4 shadow'>{html_datos}<hr>{html_notas}<div class='text-center mt-4'><button onclick='window.print()' class='btn btn-primary'>Imprimir</button></div></div>"
    return render_template_string(BASE, content=content)

@app.route('/fotos/<path:filename>')
def fotos(filename):
    try: return send_from_directory(UPLOAD_FOLDER, filename)
    except: return "Foto no encontrada", 404

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
