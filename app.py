import os, secrets, string, base64
from flask import Flask, render_template_string, request, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2, psycopg2.extras
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','ceacge-v1-2025')
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn=get_db(); cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre VARCHAR(200) UNIQUE NOT NULL, localidad VARCHAR(200), telefono_contacto VARCHAR(100), email VARCHAR(200), codigo_usuario VARCHAR(100));")
    cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, password_hash VARCHAR(300) NOT NULL, rol VARCHAR(20) DEFAULT 'centro', centro_id INTEGER REFERENCES centros(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nivel VARCHAR(20) NOT NULL, nombre VARCHAR(200) NOT NULL, apellidos VARCHAR(200), foto_base64 TEXT, numero_tutor VARCHAR(100), telefono VARCHAR(100), fecha_nacimiento DATE, lugar_nacimiento VARCHAR(150), distrito VARCHAR(150), provincia VARCHAR(150), curso_actual VARCHAR(100), centro_actual VARCHAR(200), anio_escolar VARCHAR(20), email VARCHAR(200), codigo_registro VARCHAR(100) UNIQUE, centro_id INTEGER REFERENCES centros(id), created_at TIMESTAMP DEFAULT NOW());")
    cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER REFERENCES alumnos(id) ON DELETE CASCADE, asignatura VARCHAR(150), nota VARCHAR(20), trimestre VARCHAR(50), curso VARCHAR(50), anio VARCHAR(20));")
    cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'")
    row=cur.fetchone()
    if not row:
        cur.execute("INSERT INTO centros (nombre,localidad,codigo_usuario) VALUES ('CEACGE CENTRAL','CENTRAL','CENTRAL01') RETURNING id")
        cid=cur.fetchone()[0]
    else:
        cid=row[0]
    cur.execute("SELECT id FROM usuarios WHERE username='central'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)", ('central', generate_password_hash('central2025'), 'central', cid))
    cur.execute("SELECT id FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)", ('admin', generate_password_hash('ceacge2025'), 'central', cid))
    conn.commit(); cur.close(); conn.close()

try:
    if DATABASE_URL:
        init_db()
except Exception as e:
    print("init error", e)

def gen_codigo_registro():
    return 'CEACGE-' + ''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(7))

def gen_password():
    return ''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(8))

LOGIN_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CEACGE V1</title><style>body{font-family:Arial;background:#0a1931;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}.card{background:white;padding:28px;border-radius:14px;width:92%;max-width:400px}input{width:100%;padding:13px;margin:8px 0;border:1px solid #ccc;border-radius:8px;box-sizing:border-box}button{width:100%;padding:13px;background:#0a1931;color:white;border:none;border-radius:8px;font-weight:bold}</style></head><body><div class="card"><h2 style="text-align:center;color:#0a1931">CEACGE V1 - LOGIN</h2><p style="font-size:12px;color:#555">Central: central / central2025<br>Admin: admin / ceacge2025</p><form method="post"><input name="username" placeholder="Usuario" required><input name="password" type="password" placeholder="Contrasena" required><button>Entrar</button></form>{% if error %}<p style="color:red;text-align:center">{{error}}</p>{% endif %}</div></body></html>"""

BASE_STYLE = """<style>body{font-family:Arial;background:#f4f6f9;margin:0}.header{background:#0a1931;color:white;padding:12px 15px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap}.header a{color:#ffc107;text-decoration:none;margin-left:10px}.btns{display:flex;gap:8px;flex-wrap:wrap;padding:10px;justify-content:center;background:white}.btn{padding:11px 15px;border-radius:8px;text-decoration:none;color:white;font-weight:bold;font-size:13px}.btn-blue{background:#0a1931}.btn-green{background:#28a745}.btn-orange{background:#ff7f00}.btn-purple{background:#6f42c1}table{width:98%;margin:12px auto;background:white;border-collapse:collapse;border-radius:10px;overflow:hidden;font-size:12px}th{background:#0a1931;color:white;padding:10px 6px}td{padding:8px 6px;border-bottom:1px solid #eee;text-align:center}.foto{width:38px;height:48px;object-fit:cover;border-radius:4px}.action{padding:5px 9px;border-radius:5px;text-decoration:none;color:white;margin:2px;font-size:11px;display:inline-block}.ver{background:#17a2b8}.pdf{background:#dc3545}.notas{background:#6f42c1}.edit{background:#fd7e14}.search-box{width:98%;max-width:600px;margin:10px auto;display:flex;gap:6px}.search-box input{flex:1;padding:11px;border:1px solid #ccc;border-radius:8px}.search-box button{padding:11px 18px;background:#0a1931;color:white;border:none;border-radius:8px;font-weight:bold}</style>"""

@app.route('/login', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        u=request.form['username']; p=request.form['password']
        try:
            conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM usuarios WHERE username=%s", (u,))
            user=cur.fetchone(); cur.close(); conn.close()
            if user and check_password_hash(user['password_hash'], p):
                session['user_id']=user['id']; session['username']=user['username']; session['rol']=user['rol']; session['centro_id']=user['centro_id']
                return redirect('/')
            else:
                error="Usuario o contrasena incorrectos"
        except Exception as e:
            error=str(e)
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    view=request.args.get('view','mis')
    q=request.args.get('q','').strip()
    rol=session['rol']
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT nombre FROM centros WHERE id=%s", (session['centro_id'],)); cr=cur.fetchone()
    centro_nombre=cr['nombre'] if cr else 'CENTRO'
    base_sql = "SELECT a.*, c.nombre as centro_nombre_bd FROM alumnos a JOIN centros c ON a.centro_id=c.id "
    params=[]; where=[]
    if view!='central' and rol!='central':
        where.append("a.centro_id=%s"); params.append(session['centro_id'])
    if q:
        where.append("(LOWER(a.nombre) LIKE LOWER(%s) OR LOWER(a.apellidos) LIKE LOWER(%s) OR LOWER(a.codigo_registro) LIKE LOWER(%s) OR LOWER(a.centro_actual) LIKE LOWER(%s))")
        like=f"%{q}%"; params.extend([like,like,like,like])
    if where:
        base_sql+= "WHERE "+" AND ".join(where)+" "
    base_sql+="ORDER BY a.id DESC"
    cur.execute(base_sql, tuple(params)); alumnos=cur.fetchall(); cur.close(); conn.close()
    def can_edit(alumno):
        if rol=='central': return True
        return alumno['centro_id']==session['centro_id']
    DASH = BASE_STYLE + """<div class="header"><div><b>CEACGE V1 - {{rol|upper}}</b> | {{session.username}} | {{centro_nombre}}</div><div><a href="/">Mis Alumnos</a><a href="/?view=central">BD GENERAL</a><a href="/logout">Salir</a></div></div><div class="btns"><a class="btn btn-orange" href="/nuevo">+ NUEVO ALUMNO</a><a class="btn btn-green" href="/">BUSCAR</a>{% if rol=='central' %}<a class="btn btn-blue" href="/centros">AGREGAR CENTRO</a>{% endif %}</div><form class="search-box" method="get"><input name="q" value="{{q}}" placeholder="Buscar por nombre, codigo registro, centro..."><input type="hidden" name="view" value="{{view}}"><button>Buscar</button></form><p style="text-align:center;font-size:13px;color:#555">Vista: <b>{{ 'BD GENERAL' if view=='central' else 'MIS ALUMNOS' }}</b> - {{alumnos|length}} alumnos</p><table><tr><th>Foto</th><th>Nivel</th><th>Nombre</th><th>Codigo Registro</th><th>Curso</th><th>Centro</th><th>Acciones</th></tr>{% for a in alumnos %}<tr><td>{% if a.foto_base64 %}<img class="foto" src="{{a.foto_base64}}">{% else %}-{% endif %}</td><td><b>{{a.nivel}}</b></td><td style="text-align:left"><b>{{a.nombre}} {{a.apellidos}}</b><br><small>{{a.numero_tutor or a.telefono or ''}}</small></td><td style="color:#c00000;font-weight:bold">{{a.codigo_registro}}</td><td>{{a.curso_actual or ''}}</td><td>{{a.centro_actual}}</td><td><a class="action ver" href="/ver/{{a.id}}">VER</a>{% if can_edit(a) %}<a class="action edit" href="/editar/{{a.id}}">EDITAR</a><a class="action notas" href="/notas/{{a.id}}">NOTAS</a><a class="action pdf" href="/pdf/{{a.id}}">PDF</a>{% else %}<a class="action notas" href="/ver/{{a.id}}" style="background:#28a745">SOLO VER</a>{% endif %}</td></tr>{% endfor %}</table>"""
    return render_template_string(DASH, alumnos=alumnos, centro_nombre=centro_nombre, rol=rol, view=view, q=q, can_edit=can_edit)

@app.route('/nuevo', methods=['GET','POST'])
def nuevo():
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT nombre FROM centros WHERE id=%s", (session['centro_id'],)); r=cur.fetchone(); centro_nombre=r['nombre'] if r else ''; cur.close(); conn.close()
    if request.method=='POST':
        nivel=request.form.get('nivel','SECUNDARIA')
        foto=request.form.get('foto_b64','')
        if len(foto)>2500000: foto=''
        if nivel=='PRIMARIA':
            nombre=request.form.get('nombre_p','').strip()
            apellidos=request.form.get('apellidos_p','').strip()
            centro_actual=request.form.get('centro_actual_p','').strip()
            numero_tutor=request.form.get('numero_tutor','').strip()
            telefono=''; email=''; fecha_nac=None; lugar=''; distrito=''; provincia=''; curso_actual='PRIMARIA'; anio_escolar='2025-2026'
        else:
            nombre=request.form.get('nombre','').strip()
            apellidos=request.form.get('apellidos','').strip()
            numero_tutor=''
            telefono=request.form.get('telefono','').strip()
            email=request.form.get('email','').strip()
            fecha_nac=request.form.get('fecha_nacimiento') or None
            lugar=request.form.get('lugar_nacimiento','').strip()
            distrito=request.form.get('distrito','').strip()
            provincia=request.form.get('provincia','').strip()
            curso_actual=request.form.get('curso_actual','').strip()
            anio_escolar=request.form.get('anio_escolar','').strip()
            centro_actual=request.form.get('centro_actual','').strip()
        codigo_registro=request.form.get('codigo_registro','').strip() or gen_codigo_registro()
        conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO alumnos (nivel,nombre,apellidos,foto_base64,numero_tutor,telefono,fecha_nacimiento,lugar_nacimiento,distrito,provincia,curso_actual,centro_actual,anio_escolar,email,codigo_registro,centro_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (nivel,nombre,apellidos,foto,numero_tutor,telefono,fecha_nac,lugar,distrito,provincia,curso_actual,centro_actual,anio_escolar,email,codigo_registro,session['centro_id']))
        nid=cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
        return redirect(f'/ver/{nid}')
    NUEVO = BASE_STYLE + """<div class="header"><div><b>NUEVO ALUMNO V1</b></div><div><a href="/">Volver</a></div></div><div style="max-width:900px;margin:15px auto;background:white;border-radius:12px;padding:18px"><h2 style="text-align:center;color:#0a1931">REGISTRAR ALUMNO</h2><div style="display:flex;gap:8px;justify-content:center;margin:12px 0" id="nivelBtns"><button type="button" onclick="setNivel('PRIMARIA')" id="b-PRIMARIA" class="btn btn-blue">PRIMARIA</button><button type="button" onclick="setNivel('SECUNDARIA')" id="b-SECUNDARIA" class="btn btn-green">SECUNDARIA</button><button type="button" onclick="setNivel('BACHILLERATO')" id="b-BACHILLERATO" class="btn btn-purple">BACHILLERATO</button></div><form method="post"><input type="hidden" name="nivel" id="nivel" value="SECUNDARIA"><div style="display:flex;gap:10px"><div style="flex:1"><label>Foto Carnet *</label><input type="file" accept="image/*" onchange="previewFoto(event)" required><input type="hidden" name="foto_b64" id="foto_b64" required><img id="prev" style="display:none;width:90px;height:110px;object-fit:cover;border:2px solid #0a1931;border-radius:6px;margin-top:6px"></div><div style="flex:1"><label>QR se genera auto</label><div style="background:#f0f0f0;padding:16px;border-radius:8px;text-align:center">Codigo Registro: auto<br><small>QR al guardar</small></div></div></div><div id="sec-primaria" style="display:none"><h3>DATOS PRIMARIA</h3><div style="display:flex;gap:10px"><div style="flex:1"><label>Nombre *</label><input name="nombre_p" id="nombre_p"></div><div style="flex:1"><label>Apellidos *</label><input name="apellidos_p" id="apellidos_p"></div></div><label>Numero del Tutor *</label><input name="numero_tutor" id="numero_tutor"><label>Centro Actual *</label><input name="centro_actual_p" value="{{centro_nombre}}" id="centro_actual_p"></div><div id="sec-secundaria"><h3>DATOS SECUNDARIA / BACHILLERATO</h3><div style="display:flex;gap:10px"><div style="flex:1"><label>Nombre *</label><input name="nombre" id="nombre"></div><div style="flex:1"><label>Apellidos *</label><input name="apellidos" id="apellidos"></div></div><div style="display:flex;gap:10px"><div style="flex:1"><label>Telefono</label><input name="telefono"></div><div style="flex:1"><label>Email</label><input name="email" type="email"></div></div><div style="display:flex;gap:10px"><div style="flex:1"><label>Fecha Nacimiento</label><input name="fecha_nacimiento" type="date"></div><div style="flex:1"><label>Lugar Nacimiento</label><input name="lugar_nacimiento"></div></div><div style="display:flex;gap:10px"><div style="flex:1"><label>Distrito</label><input name="distrito"></div><div style="flex:1"><label>Provincia</label><input name="provincia"></div></div><div style="display:flex;gap:10px"><div style="flex:1"><label>Curso Actual (1 ESBA a 2 BACH)</label><input name="curso_actual" placeholder="1 ESBA - 2 BACH" required></div><div style="flex:1"><label>Ano Escolar</label><input name="anio_escolar" value="2025-2026"></div></div><label>Centro Actual *</label><input name="centro_actual" value="{{centro_nombre}}"><label>Codigo Registro (vacio=auto)</label><input name="codigo_registro" placeholder="CEACGE-XXXXXXX"></div><button style="width:100%;padding:14px;background:#28a745;color:white;border:none;border-radius:8px;font-weight:bold;margin-top:15px;font-size:16px">GUARDAR ALUMNO + GENERAR QR</button></form></div><script>function setNivel(n){document.getElementById('nivel').value=n;document.querySelectorAll('#nivelBtns button').forEach(b=>{b.style.opacity=0.6});document.getElementById('b-'+n).style.opacity=1;if(n=='PRIMARIA'){document.getElementById('sec-primaria').style.display='block';document.getElementById('sec-secundaria').style.display='none';}else{document.getElementById('sec-primaria').style.display='none';document.getElementById('sec-secundaria').style.display='block';}}function previewFoto(e){const f=e.target.files[0];if(f){const r=new FileReader();r.onload=function(ev){document.getElementById('prev').src=ev.target.result;document.getElementById('prev').style.display='block';document.getElementById('foto_b64').value=ev.target.result;};r.readAsDataURL(f);}}setNivel('SECUNDARIA');</script>"""
    return render_template_string(NUEVO, centro_nombre=centro_nombre)

@app.route('/ver/<int:id>')
def ver_alumno(id):
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT a.*, c.nombre as centro_nombre_bd FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.id=%s", (id,)); a=cur.fetchone()
    cur.execute("SELECT * FROM notas WHERE alumno_id=%s ORDER BY curso, trimestre, id", (id,)); notas=cur.fetchall()
    cur.close(); conn.close()
    if not a: return "No encontrado",404
    qr=qrcode.make(f"https://ceacge-final.onrender.com/ver/{id} - {a['codigo_registro']}"); buf=BytesIO(); qr.save(buf, format='PNG'); qr_b64=base64.b64encode(buf.getvalue()).decode()
    can_edit = session['rol']=='central' or a['centro_id']==session['centro_id']
    VER = BASE_STYLE + """<div class="header"><div><b>FICHA ALUMNO</b></div><div><a href="/">Volver</a></div></div><div style="max-width:900px;margin:15px auto;background:white;border-radius:15px;padding:20px"><div style="display:flex;gap:15px;align-items:flex-start;border-bottom:3px solid #0a1931;padding-bottom:12px;flex-wrap:wrap"><div>{% if a.foto_base64 %}<img style="width:120px;height:150px;object-fit:cover;border-radius:8px;border:3px solid #0a1931" src="{{a.foto_base64}}">{% else %}Sin foto{% endif %}</div><div style="flex:1"><h2 style="margin:0;color:#0a1931">{{a.nombre}} {{a.apellidos}} - {{a.nivel}}</h2><p><b style="color:#c00000">{{a.codigo_registro}}</b><br>Centro: {{a.centro_actual}}<br>Curso: {{a.curso_actual}} | Ano: {{a.anio_escolar}}<br>{% if a.nivel=='PRIMARIA' %}Tutor: {{a.numero_tutor}}{% else %}Tel: {{a.telefono}} | Email: {{a.email}}<br>Nac: {{a.fecha_nacimiento}} - {{a.lugar_nacimiento}}<br>{{a.distrito}} / {{a.provincia}}{% endif %}</p></div><div style="text-align:center"><img src="data:image/png;base64,{{qr_b64}}" width="130" style="border:2px solid #0a1931;border-radius:8px"><br><small>{{a.codigo_registro}}<br>QR</small></div></div><h3>NOTAS - 1 ESBA A 2 BACH</h3><table style="width:100%"><tr><th>Asignatura</th><th>Nota</th><th>Trimestre</th><th>Curso</th><th>Ano</th>{% if can_edit %}<th>X</th>{% endif %}</tr>{% for n in notas %}<tr><td style="text-align:left">{{n.asignatura}}</td><td><b>{{n.nota}}</b></td><td>{{n.trimestre}}</td><td>{{n.curso}}</td><td>{{n.anio}}</td>{% if can_edit %}<td><a href="/borrar_nota/{{n.id}}?alumno={{a.id}}" style="color:red">X</a></td>{% endif %}</tr>{% else %}<tr><td colspan=6 style="color:#999">Sin notas</td></tr>{% endfor %}</table><div style="text-align:center;margin-top:15px;display:flex;gap:8px;justify-content:center"><a href="/notas/{{a.id}}" class="btn btn-purple">+ NOTAS</a><a href="/editar/{{a.id}}" class="btn btn-orange">EDITAR</a><a href="/pdf/{{a.id}}" class="btn btn-blue">PDF</a><a href="/" class="btn" style="background:#6c757d">Volver</a></div></div>"""
    return render_template_string(VER, a=a, notas=notas, qr_b64=qr_b64, can_edit=can_edit)

@app.route('/pdf/<int:id>')
def pdf_route(id):
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM alumnos WHERE id=%s", (id,)); a=cur.fetchone()
    cur.execute("SELECT * FROM notas WHERE alumno_id=%s ORDER BY curso,trimestre", (id,)); notas=cur.fetchall()
    cur.close(); conn.close()
    if not a: return "No encontrado",404
    buffer=BytesIO(); c=canvas.Canvas(buffer, pagesize=A4); w,h=A4
    azul=HexColor("#0a1931")
    c.setFillColor(azul); c.rect(0, h-80, w, 80, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF")); c.setFont("Helvetica-Bold", 13); c.drawCentredString(w/2, h-35, f"CEACGE - {a['nivel']} - {a['codigo_registro']}")
    y=h-110
    if a['foto_base64']:
        try:
            d=a['foto_base64'].split(',')[1] if ',' in a['foto_base64'] else a['foto_base64']
            img_bytes=base64.b64decode(d); buf=BytesIO(img_bytes); r=ImageReader(buf)
            c.drawImage(r, 45, y-95, width=70, height=90, preserveAspectRatio=True, mask='auto')
        except: pass
    c.setFillColor(HexColor("#000000")); c.setFont("Helvetica", 10); x=135
    c.drawString(x, y, f"Nombre: {a['nombre']} {a['apellidos']}"); y-=14
    c.drawString(x, y, f"Codigo: {a['codigo_registro']} | Centro: {a['centro_actual']}"); y-=14
    y-=10; c.setFont("Helvetica-Bold", 10); c.drawString(45, y, "NOTAS (1 ESBA A 2 BACH):"); y-=12
    c.setFont("Helvetica", 8.5)
    for n in notas:
        if y<110: c.showPage(); y=h-50
        c.drawString(45, y, f"{n['curso']} | {n['trimestre']} | {n['asignatura']} : {n['nota']} ({n['anio']})"); y-=10
    qr=qrcode.make(f"https://ceacge-final.onrender.com/ver/{a['id']}"); qb=BytesIO(); qr.save(qb, format='PNG'); qb.seek(0); qr_r=ImageReader(qb)
    c.drawImage(qr_r, w-150, 75, width=95, height=95)
    c.setFont("Helvetica", 7); c.drawString(w-150, 65, a['codigo_registro'])
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, as_attachment=False, download_name=f"{a['codigo_registro']}.pdf", mimetype='application/pdf')

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
def notas_route(alumno_id):
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM alumnos WHERE id=%s", (alumno_id,)); alumno=cur.fetchone()
    if not alumno: cur.close(); conn.close(); return "No encontrado",404
    if request.method=='POST':
        cur.execute("INSERT INTO notas (alumno_id,asignatura,nota,trimestre,curso,anio) VALUES (%s,%s,%s,%s,%s,%s)", (alumno_id,request.form['asignatura'],request.form['nota'],request.form['trimestre'],request.form['curso'],request.form['anio']))
        conn.commit()
    cur.execute("SELECT * FROM notas WHERE alumno_id=%s ORDER BY id DESC", (alumno_id,)); notas=cur.fetchall(); cur.close(); conn.close()
    html = BASE_STYLE + f"<div class='header'><div><b>NOTAS - {alumno['nombre']} {alumno['apellidos']}</b></div><div><a href='/ver/{alumno_id}'>Ver ficha</a></div></div><div style='max-width:900px;margin:15px auto;background:white;padding:18px;border-radius:12px'><h3>TODAS LAS NOTAS DE 1 ESBA A 2 BACH</h3><form method='post' style='display:flex;gap:6px;flex-wrap:wrap;background:#f9f9f9;padding:12px;border-radius:8px'><input name='asignatura' placeholder='Asignatura' required style='flex:2'><input name='nota' placeholder='Nota' required><input name='trimestre' placeholder='Trimestre' required><input name='curso' placeholder='Curso (1 ESBA - 2 BACH)' value='{alumno['curso_actual'] or ''}' required><input name='anio' value='{alumno['anio_escolar'] or '2025-2026'}' required><button style='padding:10px 15px;background:#6f42c1;color:white;border:none;border-radius:6px'>ANADIR NOTA</button></form><table style='width:100%;margin-top:12px'><tr><th>Asignatura</th><th>Nota</th><th>Trimestre</th><th>Curso</th><th>Ano</th><th>X</th></tr>"
    for n in notas:
        html+=f"<tr><td style='text-align:left'>{n['asignatura']}</td><td><b>{n['nota']}</b></td><td>{n['trimestre']}</td><td>{n['curso']}</td><td>{n['anio']}</td><td><a href='/borrar_nota/{n['id']}?alumno={alumno_id}' style='color:red'>X</a></td></tr>"
    html+=f"</table><br><a href='/ver/{alumno_id}' class='btn btn-blue'>Volver a ficha</a></div>"
    return html

@app.route('/centros', methods=['GET','POST'])
def centros():
    if 'user_id' not in session or session['rol']!='central': return redirect('/')
    msg=''; gen_user=''; gen_pass=''
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method=='POST':
        try:
            nombre=request.form.get('nombre','').strip()
            localidad=request.form.get('localidad','').strip()
            tel=request.form.get('telefono_contacto','').strip()
            email=request.form.get('email','').strip()
            usuario=request.form.get('usuario','').strip()
            codigo=request.form.get('codigo_usuario','').strip() or nombre[:4].upper()+secrets.token_hex(2).upper()
            if not usuario:
                usuario=nombre.lower().replace(' ','')[:10]+str(secrets.randbelow(100))
            password=gen_password()
            cur.execute("SELECT id FROM centros WHERE LOWER(nombre)=LOWER(%s)", (nombre,))
            row=cur.fetchone()
            if row:
                cid=row['id']
                cur.execute("UPDATE centros SET localidad=%s,telefono_contacto=%s,email=%s,codigo_usuario=%s WHERE id=%s", (localidad,tel,email,codigo,cid))
            else:
                cur.execute("INSERT INTO centros (nombre,localidad,telefono_contacto,email,codigo_usuario) VALUES (%s,%s,%s,%s,%s) RETURNING id", (nombre,localidad,tel,email,codigo))
                cid=cur.fetchone()['id']
            cur.execute("SELECT id FROM usuarios WHERE username=%s", (usuario,))
            if cur.fetchone():
                cur.execute("UPDATE usuarios SET password_hash=%s, centro_id=%s WHERE username=%s", (generate_password_hash(password),cid,usuario))
            else:
                cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)", (usuario, generate_password_hash(password), 'centro', cid))
            conn.commit()
            msg=f"CENTRO CREADO: {nombre}"; gen_user=usuario; gen_pass=password
        except Exception as e:
            conn.rollback(); msg=f"Error: {e}"
    cur.execute("SELECT c.*, (SELECT COUNT(*) FROM alumnos WHERE centro_id=c.id) as num_alumnos FROM centros c ORDER BY c.id DESC"); centros_list=cur.fetchall()
    cur.execute("SELECT u.username,c.nombre as centro_nombre,c.codigo_usuario FROM usuarios u JOIN centros c ON u.centro_id=c.id ORDER BY u.id DESC"); users=cur.fetchall()
    cur.close(); conn.close()
    html = BASE_STYLE + f"<div class='header'><div><b>AGREGAR CENTRO - CENTRAL</b></div><div><a href='/'>Inicio</a></div></div><div style='max-width:1000px;margin:15px auto;display:flex;gap:15px;flex-wrap:wrap'><div style='flex:1;min-width:320px;background:white;padding:18px;border-radius:12px'><h3>Crear / Generar Centro</h3><form method='post'><label>Nombre de centro *</label><input name='nombre' required><label>Localidad</label><input name='localidad'><label>Telefono contacto</label><input name='telefono_contacto'><label>E-mail</label><input name='email' type='email'><label>Usuario (vacio=auto)</label><input name='usuario'><label>Codigo usuario</label><input name='codigo_usuario'><button style='width:100%;padding:13px;background:#0a1931;color:white;border:none;border-radius:8px;margin-top:10px'>GENERAR CENTRO + USUARIO</button></form>"
    if gen_user:
        html+=f"<div style='margin-top:15px;background:#d4edda;padding:12px;border-radius:8px;border:1px solid #28a745'><b>{msg}</b><br>Usuario: <b>{gen_user}</b><br>Contrasena: <b>{gen_pass}</b></div>"
    elif msg:
        html+=f"<div style='margin-top:10px;background:#fff3cd;padding:10px'>{msg}</div>"
    html+=f"</div><div style='flex:1;min-width:320px;background:white;padding:18px'><h3>Centros ({len(centros_list)})</h3><table style='width:100%'><tr><th>Centro</th><th>Localidad</th><th>Codigo</th><th>Alumnos</th></tr>"
    for c in centros_list:
        html+=f"<tr><td style='text-align:left'>{c['nombre']}</td><td>{c['localidad'] or ''}</td><td>{c['codigo_usuario']}</td><td>{c['num_alumnos']}</td></tr>"
    html+="</table></div></div>"
    return html

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
