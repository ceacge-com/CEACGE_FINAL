import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
from datetime import datetime
import qrcode
from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ceacge2025-secret-v20')
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS centros (
        id SERIAL PRIMARY KEY,
        nombre VARCHAR(200) UNIQUE NOT NULL,
        codigo VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(300) NOT NULL,
        rol VARCHAR(20) DEFAULT 'centro',
        centro_id INTEGER REFERENCES centros(id),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id SERIAL PRIMARY KEY,
        nombre VARCHAR(200) NOT NULL,
        apellidos VARCHAR(200),
        ipes VARCHAR(100),
        fecha_nacimiento DATE,
        nivel VARCHAR(100),
        centro_id INTEGER REFERENCES centros(id),
        foto_path VARCHAR(300),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)
    cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'")
    if not cur.fetchone():
        cur.execute("INSERT INTO centros (nombre,codigo) VALUES ('CEACGE CENTRAL','CENTRAL') RETURNING id")
        central_id = cur.fetchone()[0]
    else:
        cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'")
        central_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)",
                    ('admin', generate_password_hash('ceacge2025'), 'admin', central_id))
    conn.commit()
    cur.close()
    conn.close()

try:
    if DATABASE_URL:
        init_db()
except Exception as e:
    print(f"Init DB error: {e}")

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

LOGIN_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CEACGE V20 FUSION Login</title>
<style>body{font-family:Arial;background:#0a1931;color:white;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.card{background:white;color:#0a1931;padding:30px;border-radius:12px;width:90%;max-width:380px}
input{width:100%;padding:12px;margin:8px 0;border:1px solid #ccc;border-radius:8px}button{width:100%;padding:12px;background:#0a1931;color:white;border:none;border-radius:8px;font-weight:bold;cursor:pointer}
</style></head><body><div class="card"><h2 style="text-align:center">CEACGE V20 FUSIÓN<br>V18+V19</h2>
<form method="post"><input name="username" placeholder="Usuario" required><input name="password" type="password" placeholder="Contraseña" required><button>Entrar</button></form>
{% if error %}<p style="color:red;text-align:center">{{error}}</p>{% endif %}
</div></body></html>
"""

DASH_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CEACGE V20</title>
<style>body{font-family:Arial;background:#f4f6f9;margin:0;padding:0}
.header{background:#0a1931;color:white;padding:15px;text-align:center}
.badge{background:#28a745;color:white;padding:4px 10px;border-radius:20px;font-size:12px}
.stats{display:flex;gap:15px;padding:15px;flex-wrap:wrap;justify-content:center}
.stat{background:white;padding:15px 25px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.1);min-width:180px;text-align:center}
.stat h3{margin:0;color:#0a1931;font-size:28px}
.btns{display:flex;gap:10px;justify-content:center;padding:10px;flex-wrap:wrap}
.btn{padding:12px 20px;border-radius:8px;text-decoration:none;color:white;font-weight:bold}
.btn-blue{background:#0a1931}.btn-green{background:#28a745}.btn-orange{background:#ff7f00}
table{width:95%;margin:15px auto;background:white;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)}
th{background:#0a1931;color:white;padding:10px}td{padding:10px;border-bottom:1px solid #eee;text-align:center}
.action{padding:5px 10px;border-radius:5px;text-decoration:none;color:white;margin:2px;display:inline-block;font-size:13px}
.ver{background:#17a2b8}.pdf{background:#dc3545}
</style></head><body>
<div class="header"><h2 style="margin:0">CEACGE V20 FUSION - V18+V19 LIVE</h2><small>{{session.username}} ({{session.rol}}) - {{centro_nombre}} <span class="badge">LIVE</span></small><br><a href="/logout" style="color:#ffc107">Salir</a></div>
<div class="stats">
<div class="stat"><h3>{{total_central}}</h3><p>Total Central CEACGE</p></div>
<div class="stat"><h3>{{total_mis}}</h3><p>Mis Alumnos ({{centro_nombre}})</p></div>
</div>
<div class="btns">
<a class="btn btn-blue" href="/">Mis Alumnos</a>
<a class="btn btn-green" href="/?view=central">BUSCAR CENTRAL (Solo ver alumnos de todo CEACGE)</a>
<a class="btn btn-orange" href="/nuevo">+ Nuevo Alumno</a>
{% if session.rol=='admin' %}<a class="btn btn-blue" href="/centros">Centros</a><a class="btn btn-blue" href="/usuarios">Usuarios - Asignar accesos manualmente</a>{% endif %}
</div>
<table>
<tr><th>Foto</th><th>Nombre</th><th>Apellidos</th><th>IPES</th><th>Centro</th><th>Acciones</th></tr>
{% for a in alumnos %}
<tr>
<td>{% if a.foto_path %}Foto{% else %}-{% endif %}</td>
<td style="color:#c00000;font-weight:bold">{{a.nombre}}</td>
<td>{{a.apellidos}}</td>
<td style="color:#c00000;font-weight:bold">{{a.ipes}}</td>
<td>{{a.centro_nombre}}</td>
<td><a class="action ver" href="/ver/{{a.id}}">VER</a> <a class="action pdf" href="/pdf/{{a.id}}">PDF</a></td>
</tr>
{% endfor %}
</table>
</body></html>
"""

VER_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>VER</title>
<style>body{font-family:Arial;background:#f4f6f9;margin:0;padding:20px}.card{max-width:700px;margin:auto;background:white;border-radius:15px;padding:25px;box-shadow:0 4px 15px rgba(0,0,0,.15)}
.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee}.label{font-weight:bold;color:#0a1931}.qr{text-align:center;margin-top:15px}
</style></head><body><div class="card">
<h2 style="text-align:center;color:#0a1931">CEACGE V20 - Ficha Completa V18+V19</h2>
<div class="row"><span class="label">Nombre:</span><span style="color:#c00000;font-weight:bold;font-size:18px">{{a.nombre}} {{a.apellidos}}</span></div>
<div class="row"><span class="label">IPES:</span><span style="color:#c00000;font-weight:bold">{{a.ipes}}</span></div>
<div class="row"><span class="label">Nivel:</span><span>{{a.nivel}}</span></div>
<div class="row"><span class="label">Centro:</span><span>{{a.centro_nombre}}</span></div>
<div class="row"><span class="label">Fecha Nac:</span><span>{{a.fecha_nacimiento}}</span></div>
<div class="qr"><img src="data:image/png;base64,{{qr_b64}}" width="180"><p style="font-size:12px;color:#666">QR Verificación CEACGE<br>ceacge-final.onrender.com/ver/{{a.id}}</p></div>
<br><div style="text-align:center"><a href="/pdf/{{a.id}}" style="background:#dc3545;color:white;padding:12px 25px;border-radius:8px;text-decoration:none;font-weight:bold">Descargar PDF Oficial V18</a> <a href="/" style="background:#0a1931;color:white;padding:12px 25px;border-radius:8px;text-decoration:none;margin-left:10px">Volver</a></div>
</div></body></html>
"""

@app.route('/login', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        u=request.form['username']; p=request.form['password']
        try:
            conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM usuarios WHERE username=%s", (u,))
            user=cur.fetchone()
            cur.close(); conn.close()
            if user and check_password_hash(user['password_hash'], p):
                session['user_id']=user['id']; session['username']=user['username']; session['rol']=user['rol']; session['centro_id']=user['centro_id']
                return redirect('/')
            else:
                error="Usuario o contraseña incorrectos"
        except Exception as e:
            error=str(e)
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
def root_redirect():
    if 'user_id' not in session:
        return redirect('/login')
    return redirect(url_for('index'))

@app.route('/dashboard')
@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    view = request.args.get('view','mis')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT nombre FROM centros WHERE id=%s", (session['centro_id'],))
    centro_row=cur.fetchone()
    centro_nombre=centro_row['nombre'] if centro_row else 'CENTRO'
    cur.execute("SELECT COUNT(*) as total FROM alumnos"); total_central=cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM alumnos WHERE centro_id=%s", (session['centro_id'],)); total_mis=cur.fetchone()['total']
    if view=='central':
        cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id ORDER BY a.id DESC")
    else:
        if session['rol']=='admin':
            cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.centro_id=%s ORDER BY a.id DESC", (session['centro_id'],))
        else:
            cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.centro_id=%s ORDER BY a.id DESC", (session['centro_id'],))
    alumnos=cur.fetchall()
    if view=='central':
        alumnos=cur.fetchall() if 'alumnos' not in locals() else alumnos
    cur.close(); conn.close()
    return render_template_string(DASH_HTML, alumnos=alumnos, total_central=total_central, total_mis=total_mis, centro_nombre=centro_nombre)

@app.route('/ver/<int:id>')
def ver(id):
    if 'user_id' not in session:
        return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.id=%s", (id,))
    a=cur.fetchone(); cur.close(); conn.close()
    if not a: return "No encontrado",404
    qr = qrcode.make(f"https://ceacge-final.onrender.com/ver/{id}")
    buf=BytesIO(); qr.save(buf, format='PNG'); qr_b64=base64.b64encode(buf.getvalue()).decode()
    return render_template_string(VER_HTML, a=a, qr_b64=qr_b64)

def generar_pdf_oficial(alumno):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w,h = A4
    azul_granada = HexColor("#0a1931")
    verde = HexColor("#0b6e4f")
    rojo_ipes = HexColor("#c00000")
    c.setFillColor(azul_granada)
    c.rect(0, h-90, w, 90, fill=1, stroke=0)
    c.setFillColor(verde)
    c.rect(0, h-92, w, 8, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w/2, h-25, "REPÚBLICA DE GUINEA ECUATORIAL")
    c.setFont("Helvetica", 9)
    c.drawCentredString(w/2, h-38, "MINISTERIO DE EDUCACIÓN, CIENCIA, TECNOLOGÍA Y FORMACIÓN PROFESIONAL")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w/2, h-58, "CENTRO DE APOYO Y GESTIÓN DE ESTUDIANTES DE GUINEA ECUATORIAL - CEACGE")
    y = h-130
    c.setFillColor(HexColor("#000000"))
    c.setFont("Helvetica", 11)
    c.drawString(85, y, f"Certifica que el alumno:")
    y -= 50
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(rojo_ipes)
    c.drawCentredString(w/2, y, f"{alumno['nombre']} {alumno['apellidos'] or ''}")
    y -= 28
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w/2, y, f"IPES: {alumno['ipes']}")
    y -= 55
    c.setFillColor(HexColor("#000000"))
    c.setFont("Helvetica", 11)
    c.drawString(85, y, f"Nivel: {alumno['nivel'] or '-'}")
    y -= 22
    c.drawString(85, y, f"Centro: {alumno['centro_nombre']}")
    y -= 22
    c.drawString(85, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    y -= 85
    qr = qrcode.make(f"https://ceacge-final.onrender.com/ver/{alumno['id']}")
    qr_buf = BytesIO(); qr.save(qr_buf, format='PNG'); qr_buf.seek(0)
    qr_reader = ImageReader(qr_buf)
    c.drawImage(qr_reader, w-170, y-30, width=113, height=113)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(HexColor("#000000"))
    c.drawCentredString(w/2, y, "El Director CEACGE")
    y -= 70
    c.setFont("Helvetica", 10)
    c.drawCentredString(w/2, y, "___________________________")
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#555555"))
    texto_seg = "Este documento es oficial y está protegido. La falsificación será sancionada conforme a la ley vigente. Verificación QR válida en ceacge-final.onrender.com"
    c.drawCentredString(w/2, 42, texto_seg)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

@app.route('/pdf/<int:id>')
def pdf(id):
    if 'user_id' not in session:
        return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.id=%s", (id,))
    a=cur.fetchone(); cur.close(); conn.close()
    if not a: return "No encontrado",404
    pdf_buf = generar_pdf_oficial(a)
    return send_file(pdf_buf, as_attachment=False, download_name=f"CEACGE_{a['ipes']}_V20.pdf", mimetype='application/pdf')

@app.route('/nuevo', methods=['GET','POST'])
def nuevo():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method=='POST':
        conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO alumnos (nombre,apellidos,ipes,nivel,centro_id,fecha_nacimiento) VALUES (%s,%s,%s,%s,%s,%s)",
                    (request.form['nombre'], request.form['apellidos'], request.form['ipes'], request.form['nivel'], session['centro_id'], request.form.get('fecha') or None))
        conn.commit(); cur.close(); conn.close()
        return redirect('/')
    return render_template_string("""
    <body style="font-family:Arial;padding:20px"><h2>Nuevo Alumno - CEACGE V20 FUSION</h2>
    <form method="post"><input name="nombre" placeholder="Nombre" required><br><br>
    <input name="apellidos" placeholder="Apellidos"><br><br>
    <input name="ipes" placeholder="IPES" required style="color:#c00000;font-weight:bold"><br><br>
    <input name="nivel" placeholder="Nivel"><br><br>
    <input name="fecha" type="date"><br><br>
    <button style="padding:10px 20px;background:#0a1931;color:white">Guardar</button></form><br><a href="/">Volver</a></body>
    """)

@app.route('/centros')
def centros():
    if 'user_id' not in session or session['rol']!='admin':
        return redirect('/')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM centros ORDER BY id"); centros=cur.fetchall(); cur.close(); conn.close()
    html="<h2>Centros V20</h2><ul>"
    for c in centros: html+=f"<li>{c['id']} - {c['nombre']} ({c['codigo']})</li>"
    html+="</ul><a href='/'>Volver</a>"
    return html

@app.route('/usuarios')
def usuarios():
    if 'user_id' not in session or session['rol']!='admin':
        return redirect('/')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT u.*, c.nombre as centro_nombre FROM usuarios u LEFT JOIN centros c ON u.centro_id=c.id"); users=cur.fetchall(); cur.close(); conn.close()
    html="<h2>Usuarios - Asignar accesos manualmente - V20</h2><table border=1><tr><th>ID</th><th>Usuario</th><th>Rol</th><th>Centro</th></tr>"
    for u in users: html+=f"<tr><td>{u['id']}</td><td>{u['username']}</td><td>{u['rol']}</td><td>{u['centro_nombre']}</td></tr>"
    html+="</table><br><a href='/'>Volver</a>"
    return html

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
