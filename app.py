import os, secrets, io, base64
from flask import Flask, request, redirect, session, render_template_string, send_from_directory, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'CEACGE-V20-QR-FINAL-2026'
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

def gen_codigo(prefix="CEACGE"):
    return f"{prefix}{secrets.token_hex(3).upper()}"

def gen_qr_data(text):
    try:
        import qrcode
        qr = qrcode.make(text)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except:
        # fallback si no hay libreria, usa API
        import urllib.parse
        return f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(text)}"

def init_db():
    conn = get_conn(); cur = conn.cursor()
    try:
        # tabla usuarios
        if USE_POSTGRES:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT, codigo_acceso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, alumno_codigo TEXT, asignatura TEXT, nota TEXT, periodo TEXT, observaciones TEXT, centro_codigo TEXT)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT UNIQUE, localidad TEXT, contacto TEXT, email TEXT, codigo_acceso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, lugar_nacimiento TEXT, distrito TEXT, provincia TEXT, telefono TEXT, email TEXT, centro TEXT, anio TEXT, codigo_alumno TEXT UNIQUE, foto TEXT, centro_codigo TEXT, curso TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, foto TEXT, codigo_alumno TEXT UNIQUE, centro TEXT, anio TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, alumno_codigo TEXT, asignatura TEXT, nota TEXT, periodo TEXT, observaciones TEXT, centro_codigo TEXT)")

        # asegurar columnas nuevas
        for col in ["codigo_alumno TEXT", "lugar_nacimiento TEXT", "distrito TEXT", "provincia TEXT", "telefono TEXT", "email TEXT", "centro_codigo TEXT", "curso TEXT"]:
            try:
                cur.execute(f"ALTER TABLE alumnos ADD COLUMN {col}")
            except: pass
            try: conn.rollback()
            except: pass
        for col in ["codigo_alumno TEXT", "centro_codigo TEXT"]:
            try: cur.execute(f"ALTER TABLE alumnos_primaria ADD COLUMN {col}")
            except: pass
            try: conn.rollback()
            except: pass
        try:
            cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
            if not cur.fetchone():
                cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
        except: pass
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

def can_edit(row_centro_codigo):
    if session.get('rol') == 'admin': return True
    return session.get('centro_codigo') == row_centro_codigo or (row_centro_codigo is None and session.get('rol') != 'admin')

BASE = """
<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CEACGE V20</title>
<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
<style>@media print{.no-print{display:none}}</style>
</head><body>
<nav class='navbar navbar-dark bg-primary no-print'><div class='container'>
<a class='navbar-brand' href='/dashboard'>CEACGE V20</a>
<div>
<a href='/consulta' class='btn btn-sm btn-light me-2'>Consulta Pública</a>
<span class='text-white me-2'>{{session.usuario}} ({{session.rol}})</span>
<a href='/logout' class='text-white'>Salir</a>
</div></div></nav>
<div class='container mt-4'>{{content|safe}}</div>
<script src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'></script>
</body></html>
"""

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
            try: cur.close()
            except: pass
            try: conn.close()
            except: pass
    return render_template_string("""
    <html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'><title>CEACGE</title></head>
    <body class='bg-light'><div class='container d-flex justify-content-center align-items-center vh-100'><div class='card p-4' style='width:360px'><h4 class='text-center'>CEACGE V20</h4>
    {% if error %}<div class='alert alert-danger'>{{error}}</div>{% endif %}
    <form method='post'><input class='form-control mb-2' name='usuario' placeholder='Usuario' required><input class='form-control mb-3' type='password' name='password' placeholder='Contraseña' required><button class='btn btn-primary w-100'>Entrar</button></form>
    <hr><a href='/consulta' class='btn btn-outline-secondary w-100'>Consulta Pública por Código</a>
    <small class='text-muted d-block text-center mt-2'>admin / ceacge2025</small></div></div></body></html>
    """, error=error)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM alumnos"); sec=cur.fetchone(); sec=list(sec.values())[0] if isinstance(sec,dict) else sec[0]
        cur.execute("SELECT COUNT(*) FROM alumnos_primaria"); prim=cur.fetchone(); prim=list(prim.values())[0] if isinstance(prim,dict) else prim[0]
        cur.execute("SELECT COUNT(*) FROM centros"); cen=cur.fetchone(); cen=list(cen.values())[0] if isinstance(cen,dict) else cen[0]
    except: sec=prim=cen=0
    finally:
        try: cur.close(); conn.close()
        except: pass
    rol = session.get('rol')
    content=f"""
    <h3>Panel - {session['usuario']} ({rol})</h3>
    <div class='row g-3 mt-2'>
      <div class='col-md-4'><div class='card p-3'><h5>Secundaria / Bachillerato</h5><h2>{sec}</h2><a href='/alumnos' class='btn btn-sm btn-primary'>Ver alumnos</a></div></div>
      <div class='col-md-4'><div class='card p-3'><h5>Primaria</h5><h2>{prim}</h2><a href='/primaria' class='btn btn-sm btn-success'>Ver primaria</a></div></div>
      <div class='col-md-4'><div class='card p-3'><h5>Centros</h5><h2>{cen}</h2><a href='/centros' class='btn btn-sm btn-warning'>Ver centros</a></div></div>
    </div>
    <div class='mt-4'>
      <a href='/alumnos/nuevo' class='btn btn-primary'>+ Nuevo Secundaria</a>
      <a href='/primaria/nuevo' class='btn btn-success'>+ Nuevo Primaria</a>
      <a href='/centros/nuevo' class='btn btn-warning'>+ Nuevo Centro</a>
      <a href='/usuarios' class='btn btn-dark'>Usuarios Centros</a>
      <a href='/consulta' class='btn btn-secondary'>Consulta Pública</a>
    </div>
    <div class='alert alert-info mt-4'>Centro <b>{session.get('centro_codigo') or 'ADMIN CENTRAL'}</b> : Los centros solo pueden editar lo que ellos registraron. La central edita todo.</div>
    """
    return render_template_string(BASE, content=content)

# --- ALUMNOS SECUNDARIA ---
@app.route('/alumnos')
def alumnos():
    if 'usuario' not in session: return redirect('/login')
    q=request.args.get('q','')
    conn=get_conn(); cur=conn.cursor()
    try:
        if q:
            cur.execute(adapt("SELECT * FROM alumnos WHERE nombre LIKE ? OR apellidos LIKE ? OR codigo_alumno LIKE ? ORDER BY id DESC") if not USE_POSTGRES else adapt("SELECT * FROM alumnos WHERE nombre ILIKE ? OR apellidos ILIKE ? OR codigo_alumno ILIKE ? ORDER BY id DESC"), (f"%{q}%",f"%{q}%",f"%{q}%"))
        else:
            cur.execute("SELECT * FROM alumnos ORDER BY id DESC")
        rows=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    html=f"""
    <h4>Secundaria / Bachillerato <a href='/alumnos/nuevo' class='btn btn-sm btn-primary'>+ Nuevo</a></h4>
    <form class='mb-3 row g-2'><div class='col-auto'><input name='q' value='{q}' placeholder='Buscar código, nombre...' class='form-control'></div><div class='col-auto'><button class='btn btn-secondary'>Buscar</button></div></form>
    <div class='table-responsive'><table class='table table-striped'><tr><th>Foto</th><th>Código</th><th>Nombre</th><th>Centro</th><th>Tel</th><th>Acciones</th></tr>
    """
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'lugar_nacimiento':r[3],'distrito':r[4],'provincia':r[5],'telefono':r[6],'email':r[7],'centro':r[8],'anio':r[9],'codigo_alumno':r[10],'foto':r[11],'centro_codigo':r[12]}
        foto = f"<img src='/fotos/{d.get('foto')}' style='width:50px;height:50px;object-fit:cover;border-radius:5px'>" if d.get('foto') else "—"
        edit_btn = f"<a href='/alumno/{d['id']}/editar' class='btn btn-sm btn-warning'>Editar</a>" if can_edit(d.get('centro_codigo')) else "<span class='badge bg-secondary'>Solo lectura</span>"
        html+=f"<tr><td>{foto}</td><td><b>{d.get('codigo_alumno') or ''}</b></td><td>{d.get('nombre')} {d.get('apellidos')}</td><td>{d.get('centro')} <small>({d.get('centro_codigo') or ''})</small></td><td>{d.get('telefono') or ''}</td><td><a href='/alumno/{d['id']}' class='btn btn-sm btn-outline-primary'>Ver / QR / Notas</a> {edit_btn}</td></tr>"
    html+="</table></div>"
    return render_template_string(BASE, content=html)

@app.route('/alumnos/nuevo', methods=['GET','POST'])
def alumno_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        data = {k: request.form.get(k) for k in ['nombre','apellidos','lugar_nacimiento','distrito','provincia','telefono','email','centro','anio','curso']}
        codigo = request.form.get('codigo_alumno') or gen_codigo("SEC")
        foto_name=None
        if 'foto' in request.files:
            f=request.files['foto']
            if f.filename:
                foto_name=secure_filename(f"{codigo}_{f.filename}")
                f.save(os.path.join(UPLOAD_FOLDER, foto_name))
        centro_codigo = session.get('centro_codigo') if session.get('rol')!='admin' else request.form.get('centro_codigo') or data['centro']
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,lugar_nacimiento,distrito,provincia,telefono,email,centro,anio,codigo_alumno,foto,centro_codigo,curso) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"),
                        (data['nombre'],data['apellidos'],data['lugar_nacimiento'],data['distrito'],data['provincia'],data['telefono'],data['email'],data['centro'],data['anio'],codigo,foto_name,centro_codigo,data['curso']))
            conn.commit()
        finally:
            try: cur.close(); conn.close()
            except: pass
        return redirect('/alumnos')
    content="""
    <h4>Nuevo Secundaria / Bachillerato</h4>
    <form method='post' enctype='multipart/form-data' class='row g-2'>
    <div class='col-md-6'><input name='nombre' placeholder='Nombre' class='form-control' required></div>
    <div class='col-md-6'><input name='apellidos' placeholder='Apellidos' class='form-control' required></div>
    <div class='col-md-4'><input name='lugar_nacimiento' placeholder='Lugar nacimiento' class='form-control'></div>
    <div class='col-md-4'><input name='distrito' placeholder='Distrito' class='form-control'></div>
    <div class='col-md-4'><input name='provincia' placeholder='Provincia' class='form-control'></div>
    <div class='col-md-4'><input name='telefono' placeholder='Teléfono contacto' class='form-control'></div>
    <div class='col-md-4'><input name='email' placeholder='Email' class='form-control'></div>
    <div class='col-md-4'><input name='curso' placeholder='Curso (Ej: 3ro Bach)' class='form-control'></div>
    <div class='col-md-4'><input name='centro' placeholder='Centro' class='form-control'></div>
    <div class='col-md-4'><input name='anio' placeholder='Año académico' class='form-control'></div>
    <div class='col-md-4'><input name='codigo_alumno' placeholder='Código (auto si vacío)' class='form-control'></div>
    """+ (f"<div class='col-md-4'><input name='centro_codigo' placeholder='Código centro (para admin)' class='form-control' value='{session.get('centro_codigo') or ''}'></div>" if session.get('rol')=='admin' else "") +"""
    <div class='col-md-6'><input type='file' name='foto' class='form-control' accept='image/*'></div>
    <div class='col-12'><button class='btn btn-primary'>Guardar</button> <a href='/alumnos' class='btn btn-secondary'>Volver</a></div>
    </form>
    """
    return render_template_string(BASE, content=content)

@app.route('/alumno/<int:id>')
def alumno_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,))
        r=cur.fetchone()
        if not r: return "No encontrado",404
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'lugar_nacimiento':r[3],'distrito':r[4],'provincia':r[5],'telefono':r[6],'email':r[7],'centro':r[8],'anio':r[9],'codigo_alumno':r[10],'foto':r[11],'centro_codigo':r[12],'curso':r[13] if len(r)>13 else ''}
        cur.execute(adapt("SELECT * FROM notas WHERE alumno_codigo=? ORDER BY periodo DESC"), (d['codigo_alumno'],))
        notas=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    qr_url = gen_qr_data(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html = f"<img src='/fotos/{d['foto']}' style='width:150px;border-radius:10px'>" if d.get('foto') else "Sin foto"
    edit_ok = can_edit(d.get('centro_codigo'))
    notas_html = "<table class='table'><tr><th>Periodo</th><th>Asignatura</th><th>Nota</th><th>Obs</th>"+ ("<th></th>" if edit_ok else "") +"</tr>"
    for n in notas:
        nd=dict(n) if isinstance(n,dict) else {'id':n[0],'asignatura':n[3],'nota':n[4],'periodo':n[5],'observaciones':n[6]}
        notas_html+=f"<tr><td>{nd.get('periodo')}</td><td>{nd.get('asignatura')}</td><td><b>{nd.get('nota')}</b></td><td>{nd.get('observaciones') or ''}</td>"
        if edit_ok: notas_html+=f"<td><a href='/nota/{nd['id']}/borrar' class='btn btn-sm btn-danger'>X</a></td>"
        notas_html+="</tr>"
    notas_html+="</table>"
    content=f"""
    <div class='row'>
      <div class='col-md-8'>
        <h4>{d['nombre']} {d['apellidos']} <small class='text-muted'>({d['codigo_alumno']})</small></h4>
        <p><b>Lugar:</b> {d.get('lugar_nacimiento')} | <b>Distrito:</b> {d.get('distrito')} | <b>Provincia:</b> {d.get('provincia')}<br>
        <b>Tel:</b> {d.get('telefono')} | <b>Email:</b> {d.get('email')}<br>
        <b>Centro:</b> {d.get('centro')} ({d.get('centro_codigo')}) | <b>Curso:</b> {d.get('curso')} | <b>Año:</b> {d.get('anio')}</p>
        <div class='mt-3'>
          <a href='/alumno/{id}/notas' class='btn btn-primary'>Ver Notas / Imprimir</a>
          {f"<a href='/alumno/{id}/editar' class='btn btn-warning'>Editar</a>" if edit_ok else ""}
          <a href='/alumnos' class='btn btn-secondary'>Volver</a>
        </div>
        <hr><h5>Notas</h5>{notas_html}
        {f'''
        <form method='post' action='/alumno/{id}/nota/add' class='row g-2 mt-3 border p-3'>
        <div class='col-md-3'><input name='periodo' placeholder='Periodo Ej: 1er Trim' class='form-control' required></div>
        <div class='col-md-3'><input name='asignatura' placeholder='Asignatura' class='form-control' required></div>
        <div class='col-md-2'><input name='nota' placeholder='Nota' class='form-control' required></div>
        <div class='col-md-4'><input name='observaciones' placeholder='Obs' class='form-control'></div>
        <div class='col-12'><button class='btn btn-success btn-sm'>+ Añadir Nota</button></div>
        </form>
        ''' if edit_ok else "<div class='alert alert-secondary'>Solo lectura para este centro</div>"}
      </div>
      <div class='col-md-4 text-center'>
        {foto_html}<br><br>
        <div class='card p-2'><b>QR Código</b><br><img src='{qr_url}' style='width:180px'><br><small>{d['codigo_alumno']}</small><br><a href='{qr_url}' download='QR_{d['codigo_alumno']}.png' class='btn btn-sm btn-outline-dark mt-2'>Descargar QR</a></div>
      </div>
    </div>
    """
    return render_template_string(BASE, content=content)

@app.route('/alumno/<int:id>/notas')
def alumno_notas(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,))
        r=cur.fetchone()
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13] if len(r)>13 else ''}
        cur.execute(adapt("SELECT * FROM notas WHERE alumno_codigo=? ORDER BY periodo, asignatura"), (d['codigo_alumno'],))
        notas=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    notas_rows=""
    for n in notas:
        nd=dict(n) if isinstance(n,dict) else {'asignatura':n[3],'nota':n[4],'periodo':n[5],'observaciones':n[6]}
        notas_rows+=f"<tr><td>{nd['periodo']}</td><td>{nd['asignatura']}</td><td>{nd['nota']}</td><td>{nd['observaciones'] or ''}</td></tr>"
    content=f"""
    <div class='no-print mb-3'><a href='/alumno/{id}' class='btn btn-secondary'>← Volver</a> <button onclick='window.print()' class='btn btn-primary'>🖨️ Imprimir</button></div>
    <div class='card p-4'>
      <h3 class='text-center'>BOLETÍN DE NOTAS - CEACGE</h3>
      <hr>
      <p><b>Alumno:</b> {d['nombre']} {d['apellidos']} | <b>Código:</b> {d['codigo_alumno']} | <b>Centro:</b> {d['centro']} | <b>Curso:</b> {d.get('curso') or ''}</p>
      <table class='table table-bordered'><tr><th>Periodo</th><th>Asignatura</th><th>Nota</th><th>Observaciones</th></tr>{notas_rows or "<tr><td colspan=4 class='text-center'>Sin notas aún</td></tr>"}</table>
      <div class='mt-5 d-flex justify-content-between'><span>Firma Tutor ______________</span><span>Sello Centro</span><span>Fecha: ___/___/______</span></div>
    </div>
    """
    return render_template_string(BASE, content=content)

@app.route('/alumno/<int:id>/nota/add', methods=['POST'])
def nota_add(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,))
        r=cur.fetchone()
        if not r: return "No encontrado",404
        d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
        if not can_edit(d['centro_codigo']): return "No autorizado",403
        cur.execute(adapt("INSERT INTO notas (alumno_id, alumno_codigo, asignatura, nota, periodo, observaciones, centro_codigo) VALUES (?,?,?,?,?,?,?)"),
                    (id, d['codigo_alumno'], request.form.get('asignatura'), request.form.get('nota'), request.form.get('periodo'), request.form.get('observaciones'), d['centro_codigo']))
        conn.commit()
    finally:
        try: cur.close(); conn.close()
        except: pass
    return redirect(f'/alumno/{id}')

@app.route('/nota/<int:id>/borrar')
def nota_borrar(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM notas WHERE id=?"), (id,))
        n=cur.fetchone()
        if n:
            nd=dict(n) if isinstance(n,dict) else {'centro_codigo':n[7],'alumno_id':n[1]}
            if can_edit(nd['centro_codigo']):
                cur.execute(adapt("DELETE FROM notas WHERE id=?"), (id,))
                conn.commit()
                return redirect(f"/alumno/{nd['alumno_id']}")
    finally:
        try: cur.close(); conn.close()
        except: pass
    return redirect('/alumnos')

# --- PRIMARIA ---
@app.route('/primaria')
def primaria():
    if 'usuario' not in session: return redirect('/login')
    q=request.args.get('q','')
    conn=get_conn(); cur=conn.cursor()
    try:
        if q:
            cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE nombre LIKE ? OR codigo_alumno LIKE ? ORDER BY id DESC") if not USE_POSTGRES else adapt("SELECT * FROM alumnos_primaria WHERE nombre ILIKE ? OR codigo_alumno ILIKE ? ORDER BY id DESC"), (f"%{q}%",f"%{q}%"))
        else:
            cur.execute("SELECT * FROM alumnos_primaria ORDER BY id DESC")
        rows=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    html=f"<h4>Primaria <a href='/primaria/nuevo' class='btn btn-sm btn-success'>+ Nuevo</a></h4><form class='mb-3'><input name='q' value='{q}' placeholder='Buscar código...' class='form-control' style='max-width:300px;display:inline-block'><button class='btn btn-secondary'>Buscar</button></form><div class='row'>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'foto':r[3],'codigo_alumno':r[4],'centro':r[5],'centro_codigo':r[7] if len(r)>7 else ''}
        foto=f"<img src='/fotos/{d['foto']}' style='width:80px;height:100px;object-fit:cover'>" if d.get('foto') else "Sin foto"
        html+=f"<div class='col-md-3 mb-3'><div class='card p-2 text-center'>{foto}<br><b>{d['nombre']} {d['apellidos']}</b><br><small>{d['codigo_alumno']}</small><br><a href='/primaria/{d['id']}' class='btn btn-sm btn-success mt-1'>Ver / QR</a></div></div>"
    html+="</div>"
    return render_template_string(BASE, content=html)

@app.route('/primaria/nuevo', methods=['GET','POST'])
def primaria_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        nombre=request.form.get('nombre'); apellidos=request.form.get('apellidos'); centro=request.form.get('centro'); anio=request.form.get('anio')
        codigo=request.form.get('codigo_alumno') or gen_codigo("PRI")
        foto_name=None
        if 'foto' in request.files:
            f=request.files['foto']
            if f.filename:
                foto_name=secure_filename(f"{codigo}_{f.filename}")
                f.save(os.path.join(UPLOAD_FOLDER, foto_name))
        centro_codigo = session.get('centro_codigo') if session.get('rol')!='admin' else request.form.get('centro_codigo') or centro
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,foto,codigo_alumno,centro,anio,centro_codigo) VALUES (?,?,?,?,?,?,?)"), (nombre,apellidos,foto_name,codigo,centro,anio,centro_codigo))
            conn.commit()
        finally:
            try: cur.close(); conn.close()
            except: pass
        return redirect('/primaria')
    content=f"""
    <h4>Nuevo Primaria (foto carné)</h4><form method='post' enctype='multipart/form-data' class='row g-2'>
    <div class='col-md-6'><input name='nombre' placeholder='Nombre' class='form-control' required></div>
    <div class='col-md-6'><input name='apellidos' placeholder='Apellidos' class='form-control' required></div>
    <div class='col-md-4'><input name='centro' placeholder='Centro' class='form-control'></div>
    <div class='col-md-4'><input name='anio' placeholder='Año' class='form-control'></div>
    <div class='col-md-4'><input name='codigo_alumno' placeholder='Código auto si vacío' class='form-control'></div>
    {"<div class='col-md-4'><input name='centro_codigo' placeholder='Código centro (admin)' class='form-control'></div>" if session.get('rol')=='admin' else ""}
    <div class='col-md-6'><label>Foto tamaño carné</label><input type='file' name='foto' class='form-control' accept='image/*' required></div>
    <div class='col-12'><button class='btn btn-success'>Guardar</button></div>
    </form>
    """
    return render_template_string(BASE, content=content)

@app.route('/primaria/<int:id>')
def primaria_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"), (id,))
        r=cur.fetchone()
        if not r: return "No encontrado",404
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'foto':r[3],'codigo_alumno':r[4],'centro':r[5],'anio':r[6],'centro_codigo':r[7] if len(r)>7 else ''}
    finally:
        try: cur.close(); conn.close()
        except: pass
    qr_url=gen_qr_data(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html=f"<img src='/fotos/{d['foto']}' style='width:200px;border:1px solid #ccc'>" if d.get('foto') else "Sin foto"
    content=f"""
    <h4>{d['nombre']} {d['apellidos']} - {d['codigo_alumno']}</h4>
    <div class='row'><div class='col-md-6'>{foto_html}<p class='mt-2'><b>Centro:</b> {d['centro']} ({d['centro_codigo']})<br><b>Año:</b> {d['anio']}</p><a href='/primaria' class='btn btn-secondary'>Volver</a></div>
    <div class='col-md-6 text-center'><div class='card p-3'><b>QR Alumno</b><br><img src='{qr_url}' style='width:200px'><br><small>{d['codigo_alumno']}</small></div></div></div>
    """
    return render_template_string(BASE, content=content)

# --- CENTROS Y USUARIOS ---
@app.route('/centros')
def centros():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("SELECT * FROM centros ORDER BY id DESC"); rows=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    html="<h4>Centros <a href='/centros/nuevo' class='btn btn-sm btn-warning'>+ Nuevo</a></h4><table class='table'><tr><th>Nombre</th><th>Código</th><th>Localidad</th><th>Contacto</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'nombre':r[1],'codigo':r[2],'localidad':r[3],'contacto':r[4]}
        html+=f"<tr><td>{d['nombre']}</td><td><b>{d['codigo']}</b></td><td>{d['localidad']}</td><td>{d['contacto']}</td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)

@app.route('/centros/nuevo', methods=['GET','POST'])
def centro_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if session.get('rol')!='admin': return "Solo admin puede crear centros",403
    if request.method=='POST':
        nombre=request.form.get('nombre'); codigo=request.form.get('codigo') or gen_codigo("CEN"); localidad=request.form.get('localidad'); contacto=request.form.get('contacto'); email=request.form.get('email')
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email,codigo_acceso) VALUES (?,?,?,?,?,?)"), (nombre,codigo,localidad,contacto,email,secrets.token_hex(4)))
            conn.commit()
        finally:
            try: cur.close(); conn.close()
            except: pass
        return redirect('/centros')
    return render_template_string(BASE, content="<h4>Nuevo Centro</h4><form method='post'><input name='nombre' placeholder='Nombre centro' class='form-control mb-2' required><input name='codigo' placeholder='Código (auto si vacío)' class='form-control mb-2'><input name='localidad' placeholder='Localidad' class='form-control mb-2'><input name='contacto' placeholder='Contacto teléfono' class='form-control mb-2'><input name='email' placeholder='Email' class='form-control mb-2'><button class='btn btn-warning'>Guardar</button></form>")

@app.route('/usuarios')
def usuarios():
    if 'usuario' not in session: return redirect('/login')
    if session.get('rol')!='admin': return "Solo admin",403
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("SELECT id,usuario,rol,centro_codigo FROM usuarios ORDER BY id"); rows=cur.fetchall()
        cur.execute("SELECT codigo,nombre FROM centros"); centros=cur.fetchall()
    finally:
        try: cur.close(); conn.close()
        except: pass
    centros_opts="".join([f"<option value='{c['codigo'] if isinstance(c,dict) else c[0]}'>{c['codigo'] if isinstance(c,dict) else c[0]} - {c['nombre'] if isinstance(c,dict) else c[1]}</option>" for c in centros])
    html=f"<h4>Usuarios Centros</h4><table class='table'><tr><th>Usuario</th><th>Rol</th><th>Centro Código</th><th>Acción</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'usuario':r[1],'rol':r[2],'centro_codigo':r[3]}
        html+=f"<tr><td>{d['usuario']}</td><td>{d['rol']}</td><td>{d['centro_codigo']}</td><td>{'' if d['usuario']=='admin' else f\"<a href='/usuarios/{d['id']}/borrar' class='btn btn-sm btn-danger'>Borrar</a>\"}</td></tr>"
    html+=f"</table><hr><h5>Crear usuario para centro</h5><form method='post' action='/usuarios/nuevo' class='row g-2'><div class='col-md-3'><input name='usuario' placeholder='Usuario (ej: centro_bata)' class='form-control' required></div><div class='col-md-3'><input name='password' placeholder='Contraseña' class='form-control' required></div><div class='col-md-3'><select name='centro_codigo' class='form-control' required><option value=''>-- Elige centro --</option>{centros_opts}</select></div><div class='col-md-3'><button class='btn btn-dark'>Crear Usuario Centro</button></div></form><div class='alert alert-warning mt-3'>Este usuario podrá VER todo, pero solo EDITAR alumnos cuyo centro_codigo coincida con el suyo.</div>"
    return render_template_string(BASE, content=html)

@app.route('/usuarios/nuevo', methods=['POST'])
def usuario_nuevo():
    if 'usuario' not in session or session.get('rol')!='admin': return redirect('/login')
    usuario=request.form.get('usuario'); password=request.form.get('password'); centro_codigo=request.form.get('centro_codigo')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"), (usuario, generate_password_hash(password), 'centro', centro_codigo))
        conn.commit()
    except Exception as e:
        return render_template_string(BASE, content=f"<div class='alert alert-danger'>{e}</div><a href='/usuarios'>Volver</a>")
    finally:
        try: cur.close(); conn.close()
        except: pass
    return redirect('/usuarios')

@app.route('/usuarios/<int:id>/borrar')
def usuario_borrar(id):
    if 'usuario' not in session or session.get('rol')!='admin': return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute(adapt("DELETE FROM usuarios WHERE id=? AND usuario!='admin'"), (id,))
        conn.commit()
    finally:
        try: cur.close(); conn.close()
        except: pass
    return redirect('/usuarios')

# --- CONSULTA PÚBLICA ---
@app.route('/consulta', methods=['GET','POST'])
def consulta():
    codigo = request.args.get('codigo') or request.form.get('codigo')
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
                ad=dict(alumno) if isinstance(alumno,dict) else {'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4], 'nombre':alumno[1] if not isinstance(alumno,dict) else alumno.get('nombre'), 'apellidos':alumno[2] if not isinstance(alumno,dict) else alumno.get('apellidos')}
                cur.execute(adapt("SELECT * FROM notas WHERE alumno_codigo=? ORDER BY periodo"), (ad['codigo_alumno'],))
                notas=cur.fetchall()
        finally:
            try: cur.close(); conn.close()
            except: pass
    content=f"""
    <h3 class='text-center'>Consulta Pública Alumno</h3>
    <form method='post' class='d-flex justify-content-center gap-2 mt-4'><input name='codigo' value='{codigo or ''}' placeholder='Pon tu código Ej: SECA1B2C3' class='form-control' style='max-width:350px' required><button class='btn btn-primary'>Buscar</button></form>
    """
    if codigo and not alumno:
        content+=f"<div class='alert alert-danger mt-4 text-center'>Código {codigo} no encontrado</div>"
    if alumno:
        d=dict(alumno) if isinstance(alumno,dict) else {'nombre':alumno[1],'apellidos':alumno[2],'codigo_alumno':alumno[10] if len(alumno)>10 else alumno[4],'centro':alumno[8] if len(alumno)>8 else alumno[5],'foto':alumno[11] if len(alumno)>11 else alumno[3],'curso':alumno[13] if len(alumno)>13 else ''}
        foto = f"<img src='/fotos/{d.get('foto')}' style='width:120px;border-radius:10px'>" if d.get('foto') else ""
        notas_html="<table class='table'><tr><th>Periodo</th><th>Asignatura</th><th>Nota</th></tr>"
        for n in notas:
            nd=dict(n) if isinstance(n,dict) else {'periodo':n[5],'asignatura':n[3],'nota':n[4]}
            notas_html+=f"<tr><td>{nd['periodo']}</td><td>{nd['asignatura']}</td><td><b>{nd['nota']}</b></td></tr>"
        notas_html+="</table>" if notas else "<p>Sin notas publicadas</p>"
        content+=f"<div class='card p-4 mt-4'><div class='row'><div class='col-md-8'><h4>{d.get('nombre')} {d.get('apellidos')}</h4><p><b>Código:</b> {d.get('codigo_alumno')}<br><b>Centro:</b> {d.get('centro')}<br><b>Curso:</b> {d.get('curso') or ''}</p>{notas_html}</div><div class='col-md-4 text-center'>{foto}</div></div></div>"
    return render_template_string(BASE, content=content)

@app.route('/fotos/<path:filename>')
def fotos(filename): return send_from_directory(UPLOAD_FOLDER, filename)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
