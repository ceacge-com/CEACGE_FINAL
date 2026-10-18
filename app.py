import os, sqlite3, io, base64, datetime
from flask import Flask, request, redirect, session, send_from_directory, render_template_string, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','CEACGE-FOTO-IZQ-QR-DER-NOMBRE-GRANDE-2026')
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, "fotos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

CENTROS = [
    ("INES P. SIALO","INES-PS"), ("INSTITUTO NACIONAL BATA","INB-BATA"),
    ("COLEGIO CLARET","CLARET"), ("COLEGIO ESPANOL","ESPANOL"),
    ("LICEO FRANCES","LICEO"), ("CARMELITAS","CARMEL"),
    ("SALESIANOS","SALES"), ("SANTA TERESITA","TERESITA"),
    ("BUEN PASTOR","PASTOR"), ("OTRO CENTRO","OTRO")
]

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL and 'postgres' in DATABASE_URL

def get_conn():
    if USE_POSTGRES:
        import psycopg2, psycopg2.extras
        url = DATABASE_URL.replace('postgres://','postgresql://',1) if DATABASE_URL.startswith('postgres://') else DATABASE_URL
        return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn=sqlite3.connect(os.path.join(basedir,"ceacge.db"))
        conn.row_factory=sqlite3.Row
        return conn

def adapt(q): return q.replace('?','%s') if USE_POSTGRES else q

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if USE_POSTGRES:
        cur.execute("""CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, fecha_nacimiento TEXT, centro TEXT, codigo_centro TEXT, nivel TEXT, telefono TEXT, notas TEXT, foto TEXT, fecha_registro TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT)""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, fecha_nacimiento TEXT, centro TEXT, codigo_centro TEXT, nivel TEXT, telefono TEXT, notas TEXT, foto TEXT, fecha_registro TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT)""")
    cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),('admin',))
    if not cur.fetchone():
        cur.execute(adapt("INSERT INTO usuarios (usuario,password) VALUES (?,?)"),('admin',generate_password_hash('ceacge2025')))
    for nom,cod in CENTROS:
        cur.execute(adapt("SELECT * FROM centros WHERE codigo=?"),(cod,))
        if not cur.fetchone():
            cur.execute(adapt("INSERT INTO centros (nombre,codigo) VALUES (?,?)"),(nom,cod))
    conn.commit(); conn.close()

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'usuario' not in session: return redirect(url_for('login'))
        return f(*a,**kw)
    return dec

def gen_qr_base64(text):
    qr=qrcode.QRCode(box_size=6, border=1)
    qr.add_data(text); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white").convert('RGB')
    buf=io.BytesIO(); img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['usuario']; p=request.form['password']
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,)); user=cur.fetchone(); conn.close()
        if user and check_password_hash(user['password'], p):
            session['usuario']=u; return redirect('/')
        return '<h3 style=color:red>Clave incorrecta</h3><a href=/login>Volver</a>'
    return '''<style>body{font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5} .b{background:white;padding:30px;border-radius:10px} input{width:100%;padding:10px;margin:5px 0} button{width:100%;padding:10px;background:#0d6efd;color:white;border:0}</style><div class=b><h2>CEACGE FINAL</h2><form method=post><input name=usuario placeholder=admin value=admin><input name=password type=password placeholder=ceacge2025><button>ENTRAR</button></form></div>'''

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall()
    cur.execute("SELECT * FROM centros ORDER BY nombre"); centros=cur.fetchall()
    conn.close()
    return render_template_string("""
    <style>body{font-family:Arial;margin:20px} .ok{background:#d1e7dd;padding:10px;border-radius:8px} .btn{background:#0d6efd;color:white;padding:12px 20px;text-decoration:none;border-radius:8px;display:inline-block;margin:5px;font-weight:bold} .btn2{background:#198754} table{width:100%;border-collapse:collapse;margin-top:15px} th,td{border:1px solid #ddd;padding:8px} th{background:#0d6efd;color:white}</style>
    <h2>CEACGE - Alumnos ({{n}}) - ceacge-final.onrender.com</h2>
    <div class=ok>✓ Postgres conectado | QR + PDF funcionando</div>
    <a class=btn href='/nuevo'>+ AÑADIR ALUMNO</a> <a class=btn btn2 href='/centros' style='background:#6c757d'>+ GESTIONAR CENTROS</a> <a href='/logout'>Salir</a>
    <table><tr><th>Foto</th><th>Nombre Completo</th><th>Centro</th><th>Telefono</th><th>Acciones</th></tr>
    {% for a in alumnos %}
    <tr><td>{% if a['foto'] %}<img src='/fotos/{{a['foto']}}' width=50>{% endif %}</td>
    <td><b>{{a['nombre']}} {{a['apellidos']}}</b><br><small>{{a['notas']}}</small></td><td>{{a['centro']}}</td><td>{{a['telefono']}}</td>
    <td><a href='/alumno/{{a['id']}}'>Ver Carnet</a> | <a href='/pdf/{{a['id']}}'>PDF</a> | <a href='/borrar/{{a['id']}}'>Borrar</a></td></tr>
    {% endfor %}</table>
    """, alumnos=alumnos, centros=centros, n=len(alumnos))

@app.route('/centros', methods=['GET','POST'])
@login_required
def centros():
    conn=get_conn(); cur=conn.cursor()
    if request.method=='POST':
        cur.execute(adapt("INSERT INTO centros (nombre,codigo) VALUES (?,?)"),(request.form['nombre'], request.form['codigo']))
        conn.commit()
    cur.execute("SELECT * FROM centros"); lista=cur.fetchall(); conn.close()
    return render_template_string("""
    <h2>Gestionar Centros</h2><form method=post><input name=nombre placeholder="Nombre centro" required><input name=codigo placeholder="Codigo ej: INES-PS" required><button>Agregar Centro</button></form>
    <ul>{% for c in lista %}<li>{{c['nombre']}} - {{c['codigo']}} <a href='/borrar_centro/{{c['id']}}'>Borrar</a></li>{% endfor %}</ul><a href='/'>Volver</a>
    """, lista=lista)

@app.route('/borrar_centro/<int:id>')
@login_required
def borrar_centro(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("DELETE FROM centros WHERE id=?"),(id,)); conn.commit(); conn.close(); return redirect('/centros')

@app.route('/alumno/<int:id>')
@login_required
def ver_alumno(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone(); conn.close()
    if not a: return "No existe"
    qr_b64 = gen_qr_base64(f"CEACGE-{a['id']:05d} {a['nombre']} {a['apellidos']} {a['centro']} {a['codigo_centro']} https://ceacge-final.onrender.com/alumno/{a['id']}")
    foto = a['foto'] if a['foto'] else ''
    return f"""
    <style>body{{font-family:Arial;background:#eee;display:flex;justify-content:center;padding:20px}} .carnet{{background:white;width:850px;padding:25px;border-radius:15px;display:flex;gap:25px;box-shadow:0 4px 12px rgba(0,0,0,.2)}} .left{{width:32%;text-align:center}} .left img.foto{{width:180px;height:230px;object-fit:cover;border-radius:10px;border:3px solid #0d6efd}} .left img.qr{{width:140px;height:140px;margin-top:12px}} .nombre{{font-size:28px;font-weight:bold;color:#0d213f;text-transform:uppercase}} .datos{{line-height:1.6}} </style>
    <div class=carnet>
      <div class=left>
        <img class=foto src='/fotos/{foto}' onerror="this.src='https://via.placeholder.com/180x230?text=Sin+Foto'">
        <br><img class=qr src='data:image/png;base64,{qr_b64}'><br><small>CEACGE-{a['id']:05d}</small>
      </div>
      <div style='width:68%'>
        <div style='background:#0d213f;color:white;padding:8px;text-align:center;border-radius:8px;margin-bottom:10px'>CEACGE - CARNET OFICIAL 2025/2026</div>
        <div class=nombre>{a['nombre']} {a['apellidos']}</div>
        <div class=datos>
          <p><b>Centro:</b> {a['centro']} ({a['codigo_centro']})<br>
          <b>Nivel:</b> {a['nivel']}<br>
          <b>Fecha Nac:</b> {a['fecha_nacimiento']}<br>
          <b>Telefono:</b> {a['telefono']}<br>
          <b>Notas:</b> {a['notas']}<br>
          <b>ID:</b> CEACGE-{a['id']:05d}</p>
        </div>
        <a href='/' class=btn>Volver</a> <a href='/pdf/{a['id']}' class=btn style='background:#198754;text-decoration:none;color:white;padding:10px'>Descargar PDF</a> <a href='javascript:window.print()'>Imprimir</a>
      </div>
    </div>
    """

@app.route('/pdf/<int:id>')
@login_required
def pdf_alumno(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone(); conn.close()
    if not a: return "No existe"
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    c.setFont("Helvetica-Bold",16); c.drawString(50,h-50,f"CEACGE - CARNET OFICIAL - {a['nombre']} {a['apellidos']}")
    # foto izquierda
    foto_path=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(foto_path):
        try: c.drawImage(ImageReader(foto_path), 50, h-300, width=150, height=190, preserveAspectRatio=True)
        except: pass
    # QR derecha
    qr_text=f"CEACGE-{a['id']:05d} {a['nombre']} {a['apellidos']}"
    qr=qrcode.QRCode(box_size=6, border=1); qr.add_data(qr_text); qr.make(fit=True); img=qr.make_image(fill_color="black", back_color="white").convert('RGB')
    qr_buf=io.BytesIO(); img.save(qr_buf, format='PNG'); qr_buf.seek(0)
    c.drawImage(ImageReader(qr_buf), 400, h-250, width=120, height=120)
    c.setFont("Helvetica-Bold",22); c.drawString(50,h-350,f"{a['nombre']} {a['apellidos']}")
    c.setFont("Helvetica",12)
    c.drawString(50,h-380,f"Centro: {a['centro']} ({a['codigo_centro']})  Nivel: {a['nivel']}")
    c.drawString(50,h-400,f"Telefono: {a['telefono']}  Nac: {a['fecha_nacimiento']}")
    c.drawString(50,h-420,f"Notas: {a['notas']}")
    c.drawString(50,h-450,f"ID: CEACGE-{a['id']:05d}  Fecha: {a['fecha_registro']}")
    c.showPage(); c.save(); buf.seek(0)
    resp=make_response(buf.getvalue()); resp.headers['Content-Type']='application/pdf'; resp.headers['Content-Disposition']=f'inline; filename=Carnet_{a["id"]}.pdf'; return resp

@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM centros ORDER BY nombre"); centros_l=cur.fetchall()
    if request.method=='POST':
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; centro_full=request.form['centro']
        if '|' in centro_full: centro, codigo = centro_full.split('|',1)
        else: centro=centro_full; codigo=request.form.get('codigo_centro','OTRO')
        nivel=request.form['nivel']; fn=request.form['fecha_nacimiento']; tel=request.form['telefono']; notas=request.form['notas']
        foto_file=request.files.get('foto'); foto_name=''
        if foto_file and foto_file.filename:
            foto_name=secure_filename(f"{nombre}_{datetime.datetime.now().strftime('%H%M%S')}.jpg")
            foto_file.save(os.path.join(UPLOAD_FOLDER, foto_name))
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,fecha_nacimiento,centro,codigo_centro,nivel,telefono,notas,foto,fecha_registro) VALUES (?,?,?,?,?,?,?,?,?,?)"),(nombre,apellidos,fn,centro,codigo,nivel,tel,notas,foto_name,datetime.datetime.now().isoformat()))
        conn.commit(); conn.close(); return redirect('/')
    conn.close()
    opts="".join([f"<option value=\"{c['nombre']}|{c['codigo']}\">{c['nombre']} ({c['codigo']})</option>" for c in centros_l])
    return f"""
    <style>body{{font-family:Arial;margin:20px}} input,select,textarea{{padding:10px;margin:5px;width:320px}} button{{padding:12px;background:#0d6efd;color:white;border:0}}</style>
    <h2>Nuevo Alumno - CEACGE COMPLETO</h2>
    <form method=post enctype=multipart/form-data>
    Nombre:<br><input name=nombre required><br>
    Apellidos:<br><input name=apellidos required><br>
    Fecha Nac:<br><input name=fecha_nacimiento type=date><br>
    Centro:<br><select name=centro>{opts}</select><br>
    Codigo (si otro):<br><input name=codigo_centro placeholder="OTRO"><br>
    Nivel:<br><select name=nivel><option>1 PRIMARIA</option><option>2 PRIMARIA</option><option>3 PRIMARIA</option><option>4 PRIMARIA</option><option>5 PRIMARIA</option><option>6 PRIMARIA</option><option>1 ESBA</option><option>2 ESBA</option><option>3 ESBA</option><option>4 ESBA</option><option>1 BACHILLERATO</option><option>2 BACHILLERATO</option></select><br>
    Telefono Contacto:<br><input name=telefono placeholder="+240 ..."><br>
    Notas del Alumno:<br><textarea name=notas placeholder="Notas, direccion, tutor..."></textarea><br>
    Foto:<br><input type=file name=foto accept='image/*'><br><br>
    <button>GUARDAR ALUMNO</button>
    </form><br><a href='/'>Volver</a> | <a href='/centros'>Gestionar Centros</a>
    """

@app.route('/borrar/<int:id>')
@login_required
def borrar(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("DELETE FROM alumnos WHERE id=?"),(id,)); conn.commit(); conn.close(); return redirect('/')

try: init_db()
except Exception as e: print("init error", e)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
