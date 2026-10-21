import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2, psycopg2.extras
import qrcode
from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','ceacge2025-secret-v21')
DATABASE_URL = os.environ.get('DATABASE_URL')
def get_db(): return psycopg2.connect(DATABASE_URL, sslmode='require')
def init_db():
    conn=get_db(); cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre VARCHAR(200) UNIQUE NOT NULL, codigo VARCHAR(50));")
    cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, password_hash VARCHAR(300) NOT NULL, rol VARCHAR(20) DEFAULT 'centro', centro_id INTEGER REFERENCES centros(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY,nombre VARCHAR(200) NOT NULL,apellidos VARCHAR(200),codigo_alumno VARCHAR(100),ipes VARCHAR(100),nivel VARCHAR(20) DEFAULT 'SECUNDARIA',fecha_nacimiento DATE,lugar_nacimiento VARCHAR(150),distrito VARCHAR(150),provincia VARCHAR(150),centro_actual VARCHAR(200),anio_academico VARCHAR(20),centro_id INTEGER REFERENCES centros(id),foto_base64 TEXT);")
    cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY,alumno_id INTEGER REFERENCES alumnos(id) ON DELETE CASCADE,asignatura VARCHAR(150),nota VARCHAR(20),trimestre VARCHAR(50),anio VARCHAR(20));")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='alumnos';")
    cols=[r[0] for r in cur.fetchall()]
    for col, typ in [("codigo_alumno","VARCHAR(100)"),("lugar_nacimiento","VARCHAR(150)"),("distrito","VARCHAR(150)"),("provincia","VARCHAR(150)"),("centro_actual","VARCHAR(200)"),("anio_academico","VARCHAR(20)"),("foto_base64","TEXT")]:
        if col not in cols:
            try: cur.execute(f"ALTER TABLE alumnos ADD COLUMN {col} {typ};")
            except: pass
    cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'")
    if not cur.fetchone():
        cur.execute("INSERT INTO centros (nombre,codigo) VALUES ('CEACGE CENTRAL','CENTRAL') RETURNING id"); cid=cur.fetchone()[0]
    else:
        cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'"); cid=cur.fetchone()[0]
    cur.execute("SELECT id FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)", ('admin', generate_password_hash('ceacge2025'), 'admin', cid))
    conn.commit(); cur.close(); conn.close()
try:
    if DATABASE_URL: init_db()
except: pass

LOGIN_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CEACGE</title><style>body{font-family:Arial;background:#0a1931;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}.card{background:white;padding:30px;border-radius:14px;width:92%;max-width:400px}input{width:100%;padding:13px;margin:8px 0;border:1px solid #ccc;border-radius:8px}button{width:100%;padding:13px;background:#0a1931;color:white;border:none;border-radius:8px;font-weight:bold}</style></head><body><div class="card"><h2 style="text-align:center">CEACGE V20.2.2<br>PRIMARIA-SEC-BACH-ESBA</h2><form method="post"><input name="username" placeholder="Usuario" required><input name="password" type="password" placeholder="Contraseña" required><button>Entrar</button></form>{% if error %}<p style="color:red;text-align:center">{{error}}</p>{% endif %}</div></body></html>"""
DASH_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CEACGE V20.2.2</title><style>body{font-family:Arial;background:#f4f6f9;margin:0}.header{background:#0a1931;color:white;padding:15px;text-align:center}.badge{background:#28a745;color:white;padding:4px 10px;border-radius:20px;font-size:12px}.stats{display:flex;gap:12px;padding:15px;flex-wrap:wrap;justify-content:center}.stat{background:white;padding:12px 20px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.1);min-width:120px;text-align:center}.stat h3{margin:0;color:#0a1931;font-size:24px}.btns{display:flex;gap:8px;justify-content:center;padding:10px;flex-wrap:wrap}.btn{padding:12px 16px;border-radius:8px;text-decoration:none;color:white;font-weight:bold;font-size:13px}.btn-blue{background:#0a1931}.btn-green{background:#28a745}.btn-orange{background:#ff7f00}table{width:98%;margin:10px auto;background:white;border-collapse:collapse;border-radius:10px;overflow:hidden;font-size:12px}th{background:#0a1931;color:white;padding:8px}td{padding:7px;border-bottom:1px solid #eee;text-align:center}.action{padding:4px 8px;border-radius:4px;text-decoration:none;color:white;margin:2px;display:inline-block}.ver{background:#17a2b8}.pdf{background:#dc3545}.notas{background:#6f42c1}.foto{width:32px;height:42px;object-fit:cover;border-radius:3px;border:1px solid #ccc}</style></head><body><div class="header"><h2 style="margin:0">CEACGE V20.2.2 - PRIMARIA | SECUNDARIA | BACH | ESBA - LIVE</h2><small>{{session.username}} ({{session.rol}}) - {{centro_nombre}} <span class="badge">V20.2.2 FIX</span></small><br><a href="/logout" style="color:#ffc107">Salir</a></div><div class="stats"><div class="stat"><h3>{{total_central}}</h3><p>Total Central</p></div><div class="stat"><h3>{{total_mis}}</h3><p>Mis Alumnos</p></div></div><div class="btns"><a class="btn btn-blue" href="/">Mis Alumnos</a><a class="btn btn-green" href="/?view=central">BUSCAR CENTRAL</a><a class="btn btn-orange" href="/nuevo">+ NUEVO ALUMNO (Primaria/Sec/Bach/ESBA)</a>{% if session.rol=='admin' %}<a class="btn btn-blue" href="/centros">Centros</a><a class="btn btn-blue" href="/usuarios">Usuarios - Centro+User+Pass>Generar</a>{% endif %}</div><table><tr><th>Foto</th><th>Nivel</th><th>Nombre</th><th>Codigo</th><th>Centro</th><th>Año</th><th>Acciones</th></tr>{% for a in alumnos %}<tr><td>{% if a.foto_base64 %}<img class="foto" src="{{a.foto_base64}}">{% else %}-{% endif %}</td><td>{{a.nivel}}</td><td style="color:#c00000;font-weight:bold">{{a.nombre}} {{a.apellidos}}</td><td>{{a.codigo_alumno or a.ipes}}</td><td>{{a.centro_nombre}}</td><td>{{a.anio_academico}}</td><td><a class="action ver" href="/ver/{{a.id}}">VER/QR</a> <a class="action notas" href="/notas/{{a.id}}">NOTAS</a> <a class="action pdf" href="/pdf/{{a.id}}">PDF</a></td></tr>{% endfor %}</table></body></html>"""
NUEVO_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Nuevo</title><style>body{font-family:Arial;background:#f4f6f9;margin:0;padding:15px}.card{max-width:850px;margin:auto;background:white;border-radius:12px;padding:20px}label{font-weight:bold;font-size:13px;color:#0a1931;display:block;margin-top:10px}input{width:100%;padding:10px;margin:4px 0;border:1px solid #ccc;border-radius:6px;box-sizing:border-box}.row{display:flex;gap:10px}.row>div{flex:1}.nivel{display:flex;gap:8px;justify-content:center;margin:12px 0}.nivel button{padding:10px 12px;border:2px solid #0a1931;border-radius:8px;font-weight:bold;cursor:pointer;background:white;color:#0a1931}.nivel button.active{background:#0a1931;color:white}.submit{width:100%;padding:14px;background:#28a745;color:white;border:none;border-radius:8px;font-weight:bold;margin-top:15px}</style><script>function setNivel(n){document.getElementById('nivel').value=n; document.querySelectorAll('.nivel button').forEach(b=>b.classList.remove('active')); document.getElementById('b-'+n).classList.add('active');}function previewFoto(e){const f=e.target.files[0]; if(f){const r=new FileReader(); r.onload=function(ev){document.getElementById('prev').src=ev.target.result; document.getElementById('prev').style.display='block'; document.getElementById('foto_b64').value=ev.target.result;}; r.readAsDataURL(f);}}</script></head><body><div class="card"><h2 style="text-align:center;color:#0a1931">NUEVO ALUMNO - PRIMARIA / SECUNDARIA / BACHILLERATO / ESBA</h2><form method="post"><div class="nivel"><button type="button" id="b-PRIMARIA" onclick="setNivel('PRIMARIA')">PRIMARIA</button><button type="button" id="b-SECUNDARIA" class="active" onclick="setNivel('SECUNDARIA')">SECUNDARIA</button><button type="button" id="b-BACHILLERATO" onclick="setNivel('BACHILLERATO')">BACHILLERATO</button><button type="button" id="b-ESBA" onclick="setNivel('ESBA')">ESBA</button></div><input type="hidden" name="nivel" id="nivel" value="SECUNDARIA"><div class="row"><div><label>Foto Tamaño Carné</label><input type="file" accept="image/*" onchange="previewFoto(event)"><input type="hidden" name="foto_b64" id="foto_b64"><img id="prev" style="display:none;width:90px;height:110px;object-fit:cover;border:1px solid #ccc;border-radius:6px;margin-top:6px"></div><div><label>Código QR automático</label><div style="background:#f0f0f0;padding:20px;border-radius:8px;text-align:center;font-size:12px">QR se genera solo al guardar</div></div></div><div class="row"><div><label>Nombre *</label><input name="nombre" required></div><div><label>Apellidos *</label><input name="apellidos" required></div></div><div class="row"><div><label>Código de Alumno *</label><input name="codigo_alumno" required placeholder="CEA2025-001"></div><div><label>IPES</label><input name="ipes"></div></div><div class="row"><div><label>Fecha Nacimiento</label><input name="fecha_nacimiento" type="date"></div><div><label>Lugar Nacimiento</label><input name="lugar_nacimiento" placeholder="Bata"></div></div><div class="row"><div><label>Distrito</label><input name="distrito" placeholder="Distrito"></div><div><label>Provincia</label><input name="provincia" placeholder="Provincia"></div></div><div class="row"><div><label>Centro Actual</label><input name="centro_actual" value="{{centro_nombre}}"></div><div><label>Año</label><input name="anio_academico" value="2025-2026"></div></div><button class="submit">Guardar Alumno + Generar QR</button></form><br><a href="/">Volver</a></div></body></html>"""
VER_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>VER</title><style>body{font-family:Arial;background:#f4f6f9;margin:0;padding:15px}.card{max-width:800px;margin:auto;background:white;border-radius:15px;padding:20px}.header{display:flex;gap:15px;align-items:center;border-bottom:2px solid #0a1931;padding-bottom:12px}.foto{width:100px;height:125px;object-fit:cover;border-radius:6px;border:2px solid #0a1931}.row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eee;font-size:13px}.label{font-weight:bold;color:#0a1931}</style></head><body><div class="card"><div class="header"><div>{% if a.foto_base64 %}<img class="foto" src="{{a.foto_base64}}">{% else %}<div style="width:100px;height:125px;background:#eee;display:flex;align-items:center;justify-content:center;border-radius:6px">Sin foto</div>{% endif %}</div><div><h2 style="margin:0;color:#0a1931">{{a.nombre}} {{a.apellidos}}</h2><p><b style="color:#c00000">{{a.codigo_alumno}}</b> - {{a.nivel}} - Año {{a.anio_academico}}</p><p>Centro: {{a.centro_nombre}}</p></div><div style="margin-left:auto;text-align:center"><img src="data:image/png;base64,{{qr_b64}}" width="110"><br><small>QR</small></div></div><div class="row"><span class="label">Codigo / IPES:</span><span style="color:#c00000;font-weight:bold">{{a.codigo_alumno}} / {{a.ipes}}</span></div><div class="row"><span class="label">Fecha/Lugar Nac:</span><span>{{a.fecha_nacimiento}} - {{a.lugar_nacimiento}}</span></div><div class="row"><span class="label">Distrito / Provincia:</span><span>{{a.distrito}} / {{a.provincia}}</span></div><div class="row"><span class="label">Centro Actual:</span><span>{{a.centro_actual or a.centro_nombre}}</span></div><h3>Notas</h3><table border=1 cellpadding=6 style="width:100%;border-collapse:collapse"><tr style="background:#0a1931;color:white"><th>Asignatura</th><th>Nota</th><th>Trim</th><th>Año</th></tr>{% for n in notas %}<tr><td>{{n.asignatura}}</td><td>{{n.nota}}</td><td>{{n.trimestre}}</td><td>{{n.anio}}</td></tr>{% else %}<tr><td colspan=4 style="text-align:center;color:#999">Sin notas - Usa NOTAS >> AÑADIR</td></tr>{% endfor %}</table><br><div style="text-align:center"><a href="/notas/{{a.id}}" style="background:#6f42c1;color:white;padding:10px 15px;border-radius:6px;text-decoration:none">NOTAS >> BOTON PARA AÑADIR NOTAS</a> <a href="/pdf/{{a.id}}" style="background:#dc3545;color:white;padding:10px 15px;border-radius:6px;text-decoration:none;margin-left:6px">PDF</a> <a href="/" style="background:#0a1931;color:white;padding:10px 15px;border-radius:6px;text-decoration:none;margin-left:6px">Volver</a></div></div></body></html>"""

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
            else: error="Usuario o contraseña incorrectos"
        except Exception as e: error=str(e)
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/')
def root_redirect():
    if 'user_id' not in session: return redirect('/login')
    return redirect(url_for('index'))

@app.route('/dashboard')
@app.route('/index')
def index():
    if 'user_id' not in session: return redirect('/login')
    view=request.args.get('view','mis')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT nombre FROM centros WHERE id=%s", (session['centro_id'],)); cr=cur.fetchone(); centro_nombre=cr['nombre'] if cr else 'CENTRO'
    cur.execute("SELECT COUNT(*) as total FROM alumnos"); total_central=cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM alumnos WHERE centro_id=%s", (session['centro_id'],)); total_mis=cur.fetchone()['total']
    if view=='central':
        cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id ORDER BY a.id DESC")
    else:
        cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.centro_id=%s ORDER BY a.id DESC", (session['centro_id'],))
    alumnos=cur.fetchall(); cur.close(); conn.close()
    return render_template_string(DASH_HTML, alumnos=alumnos, total_central=total_central, total_mis=total_mis, centro_nombre=centro_nombre)

@app.route('/ver/<int:id>')
def ver(id):
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.id=%s", (id,)); a=cur.fetchone()
    cur.execute("SELECT * FROM notas WHERE alumno_id=%s ORDER BY id DESC", (id,)); notas=cur.fetchall()
    cur.close(); conn.close()
    if not a: return "No encontrado",404
    qr=qrcode.make(f"https://ceacge-final.onrender.com/ver/{id}"); buf=BytesIO(); qr.save(buf, format='PNG'); qr_b64=base64.b64encode(buf.getvalue()).decode()
    return render_template_string(VER_HTML, a=a, qr_b64=qr_b64, notas=notas)

def generar_pdf(alumno, notas):
    buffer=BytesIO(); c=canvas.Canvas(buffer, pagesize=A4); w,h=A4
    azul=HexColor("#0a1931"); verde=HexColor("#0b6e4f"); rojo=HexColor("#c00000")
    c.setFillColor(azul); c.rect(0, h-90, w, 90, fill=1, stroke=0)
    c.setFillColor(verde); c.rect(0, h-92, w, 8, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF")); c.setFont("Helvetica-Bold", 11); c.drawCentredString(w/2, h-25, "REPUBLICA DE GUINEA ECUATORIAL")
    c.setFont("Helvetica", 9); c.drawCentredString(w/2, h-38, "MINISTERIO DE EDUCACION")
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(w/2, h-58, "CEACGE V20.2.2")
    c.setFont("Helvetica-Bold", 10); c.drawCentredString(w/2, h-75, f"{alumno['nivel']} - {alumno['anio_academico'] or ''}")
    y=h-120
    if alumno['foto_base64']:
        try:
            d=alumno['foto_base64'].split(',')[1] if ',' in alumno['foto_base64'] else alumno['foto_base64']
            img_bytes=base64.b64decode(d); buf=BytesIO(img_bytes); r=ImageReader(buf); c.drawImage(r, 50, y-90, width=60, height=75, preserveAspectRatio=True, mask='auto')
        except: pass
    c.setFillColor(HexColor("#000000")); c.setFont("Helvetica", 10); c.drawString(130, y, f"Nombre: {alumno['nombre']} {alumno['apellidos']}")
    y-=16; c.setFont("Helvetica-Bold", 11); c.setFillColor(rojo); c.drawString(130, y, f"Codigo: {alumno['codigo_alumno']} IPES:{alumno['ipes'] or ''}"); c.setFillColor(HexColor("#000000")); c.setFont("Helvetica", 10)
    y-=16; c.drawString(130, y, f"Fecha: {alumno['fecha_nacimiento'] or '-'} Lugar:{alumno['lugar_nacimiento'] or '-'}")
    y-=16; c.drawString(130, y, f"Distrito:{alumno['distrito'] or '-'} Provincia:{alumno['provincia'] or '-'}")
    y-=16; c.drawString(130, y, f"Centro:{alumno['centro_actual'] or alumno['centro_nombre']} Año:{alumno['anio_academico'] or ''}")
    y-=30; c.setFont("Helvetica-Bold", 10); c.drawString(50, y, "NOTAS:"); y-=14
    c.setFont("Helvetica", 9)
    for n in notas[:15]:
        if y<100: break
        c.drawString(50, y, f"{n['asignatura']} - {n['nota']} - {n['trimestre']} - {n['anio']}"); y-=12
    qr=qrcode.make(f"https://ceacge-final.onrender.com/ver/{alumno['id']}"); qb=BytesIO(); qr.save(qb, format='PNG'); qb.seek(0); qr_r=ImageReader(qb); c.drawImage(qr_r, w-150, 80, width=90, height=90)
    c.setFont("Helvetica-Bold", 10); c.drawCentredString(w/2, 95, "El Director CEACGE")
    c.showPage(); c.save(); buffer.seek(0); return buffer

@app.route('/pdf/<int:id>')
def pdf(id):
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.id=%s", (id,)); a=cur.fetchone()
    cur.execute("SELECT * FROM notas WHERE alumno_id=%s", (id,)); notas=cur.fetchall()
    cur.close(); conn.close()
    if not a: return "No encontrado",404
    b=generar_pdf(a, notas); return send_file(b, as_attachment=False, download_name=f"CEACGE_{a['codigo_alumno']}.pdf", mimetype='application/pdf')

@app.route('/nuevo', methods=['GET','POST'])
def nuevo():
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT nombre FROM centros WHERE id=%s", (session['centro_id'],)); r=cur.fetchone(); centro_nombre=r['nombre'] if r else ''; cur.close(); conn.close()
    if request.method=='POST':
        foto=request.form.get('foto_b64','')
        if len(foto)>2000000: foto=''
        conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO alumnos (nombre,apellidos,codigo_alumno,ipes,nivel,fecha_nacimiento,lugar_nacimiento,distrito,provincia,centro_actual,anio_academico,centro_id,foto_base64) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (request.form['nombre'], request.form['apellidos'], request.form['codigo_alumno'], request.form['ipes'], request.form['nivel'], request.form.get('fecha_nacimiento') or None, request.form.get('lugar_nacimiento'), request.form.get('distrito'), request.form.get('provincia'), request.form.get('centro_actual'), request.form.get('anio_academico'), session['centro_id'], foto))
        nid=cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
        return redirect(f'/ver/{nid}')
    return render_template_string(NUEVO_HTML, centro_nombre=centro_nombre)

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
def notas_route(alumno_id):
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.id=%s", (alumno_id,)); alumno=cur.fetchone()
    if request.method=='POST':
        cur.execute("INSERT INTO notas (alumno_id,asignatura,nota,trimestre,anio) VALUES (%s,%s,%s,%s,%s)", (alumno_id, request.form['asignatura'], request.form['nota'], request.form['trimestre'], request.form['anio'])); conn.commit()
    cur.execute("SELECT * FROM notas WHERE alumno_id=%s ORDER BY id DESC", (alumno_id,)); notas=cur.fetchall(); cur.close(); conn.close()
    html=f"<body style='font-family:Arial;padding:15px;background:#f4f6f9'><div style='max-width:800px;margin:auto;background:white;padding:20px;border-radius:12px'><h2>NOTAS - {alumno['nombre']} {alumno['apellidos']} - {alumno['codigo_alumno']}</h2><form method='post' style='display:flex;gap:6px;flex-wrap:wrap;background:#f9f9f9;padding:12px;border-radius:8px'><input name='asignatura' placeholder='Asignatura' required style='flex:2;padding:10px'><input name='nota' placeholder='Nota' required style='flex:1;padding:10px'><input name='trimestre' placeholder='Trimestre' required style='flex:1;padding:10px'><input name='anio' value='{alumno['anio_academico'] or '2025-2026'}' style='flex:1;padding:10px'><button style='padding:10px 15px;background:#6f42c1;color:white;border:none;border-radius:6px;font-weight:bold'>AÑADIR NOTA</button></form><table border=1 cellpadding=8 style='width:100%;margin-top:15px;border-collapse:collapse'><tr style='background:#0a1931;color:white'><th>Asignatura</th><th>Nota</th><th>Trim</th><th>Año</th><th>X</th></tr>"
    for n in notas: html+=f"<tr><td>{n['asignatura']}</td><td>{n['nota']}</td><td>{n['trimestre']}</td><td>{n['anio']}</td><td><a href='/borrar_nota/{n['id']}?alumno={alumno_id}' style='color:red'>X</a></td></tr>"
    html+=f"</table><br><a href='/ver/{alumno_id}'>VER</a> <a href='/'>Volver</a></div></body>"; return html

@app.route('/borrar_nota/<int:id>')
def borrar_nota(id):
    alumno_id=request.args.get('alumno'); conn=get_db(); cur=conn.cursor(); cur.execute("DELETE FROM notas WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return redirect(f'/notas/{alumno_id}' if alumno_id else '/')

@app.route('/centros', methods=['GET','POST'])
def centros():
    if 'user_id' not in session or session['rol']!='admin': return redirect('/')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method=='POST':
        try: cur.execute("INSERT INTO centros (nombre,codigo) VALUES (%s,%s)", (request.form['nombre'].strip(), request.form['codigo'].strip())); conn.commit()
        except: conn.rollback()
    cur.execute("SELECT * FROM centros ORDER BY id"); lst=cur.fetchall(); cur.close(); conn.close()
    html='<body style="font-family:Arial;padding:15px;background:#f4f6f9"><h2>Centros V20.2.2</h2><form method="post" style="background:white;padding:15px;border-radius:10px;max-width:500px"><input name="nombre" placeholder="Nombre Centro" required style="width:100%;padding:10px;margin:5px 0"><input name="codigo" placeholder="Codigo" required style="width:100%;padding:10px;margin:5px 0"><button style="padding:10px 20px;background:#0a1931;color:white;border:none;border-radius:6px">Crear Centro</button></form><br><table border=1 cellpadding=8 style="background:white"><tr><th>ID</th><th>Nombre</th><th>Codigo</th></tr>'
    for c in lst: html+=f"<tr><td>{c['id']}</td><td>{c['nombre']}</td><td>{c['codigo']}</td></tr>"
    html+="</table><br><a href='/'>Volver</a></body>"; return html

@app.route('/usuarios', methods=['GET','POST'])
def usuarios():
    if 'user_id' not in session or session['rol']!='admin': return redirect('/')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    msg=''
    if request.method=='POST':
        centro_nombre=request.form.get('centro_nombre','').strip()
        username=request.form.get('username','').strip()
        password=request.form.get('password','').strip()
        rol=request.form.get('rol','centro')
        try:
            cur.execute("SELECT id FROM centros WHERE LOWER(nombre)=LOWER(%s)", (centro_nombre,)); row=cur.fetchone()
            if row: centro_id=row['id']
            else:
                cur.execute("INSERT INTO centros (nombre,codigo) VALUES (%s,%s) RETURNING id", (centro_nombre, (centro_nombre[:6].upper().replace(' ','') or 'CENT')+'01')); centro_id=cur.fetchone()['id']
            cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)", (username, generate_password_hash(password), rol, centro_id)); conn.commit()
            msg=f"<p style='color:green;font-weight:bold'>✓ GENERADO: Centro '{centro_nombre}' + Usuario '{username}' / '{password}'</p>"
        except Exception as e: conn.rollback(); msg=f"<p style='color:red'>{e}</p>"
    cur.execute("SELECT * FROM centros ORDER BY nombre"); centros_list=cur.fetchall()
    cur.execute("SELECT u.*, c.nombre as centro_nombre FROM usuarios u LEFT JOIN centros c ON u.centro_id=c.id ORDER BY u.id DESC"); users=cur.fetchall()
    cur.close(); conn.close()
    html=f"<body style='font-family:Arial;padding:15px;background:#f4f6f9'><h2>Usuarios - Nombre del centro + Usuario + Contraseña > Generar - V20.2.2</h2>{msg}<form method='post' style='background:white;padding:15px;border-radius:12px;max-width:550px'><label>Nombre del Centro *</label><input name='centro_nombre' required style='width:100%;padding:10px;margin:5px 0'><label>Usuario *</label><input name='username' required style='width:100%;padding:10px;margin:5px 0'><label>Contraseña *</label><input name='password' required style='width:100%;padding:10px;margin:5px 0'><label>Rol</label><select name='rol' style='width:100%;padding:10px'><option value='centro'>centro</option><option value='admin'>admin</option></select><button style='width:100%;padding:12px;background:#28a745;color:white;border:none;border-radius:8px;font-weight:bold;margin-top:10px'>GENERAR CENTRO + USUARIO</button></form><br><table border=1 cellpadding=8 style='background:white;border-collapse:collapse'><tr style='background:#0a1931;color:white'><th>Usuario</th><th>Centro</th></tr>"
    for u in users: html+=f"<tr><td>{u['username']}</td><td>{u['centro_nombre']}</td></tr>"
    html+="</table><br><a href='/'>Volver</a></body>"; return html

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
