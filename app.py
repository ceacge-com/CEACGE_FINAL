import os, sqlite3, io
from flask import Flask, request, redirect, session, send_from_directory, render_template_string, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','CEACGE-FINAL-V41')
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
        conn=sqlite3.connect(os.path.join(basedir,"ceacge.db"))
        conn.row_factory=sqlite3.Row
        return conn
def adapt(q): return q.replace('?','%s') if USE_POSTGRES else q

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if USE_POSTGRES:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, telefono TEXT, foto TEXT, fecha_registro TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, nota TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, telefono TEXT, foto TEXT, fecha_registro TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, nota TEXT)")
    cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),('admin',))
    if not cur.fetchone():
        cur.execute(adapt("INSERT INTO usuarios (usuario,password) VALUES (?,?)"),('admin',generate_password_hash('ceacge2025')))
    conn.commit(); conn.close()

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'usuario' not in session: return redirect(url_for('login'))
        return f(*a,**kw)
    return dec

def gen_qr(text):
    qr=qrcode.QRCode(box_size=6, border=1); qr.add_data(text); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white").convert('RGB')
    buf=io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0); return buf

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['usuario']; p=request.form['password']
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,)); user=cur.fetchone(); conn.close()
        if user and check_password_hash(user['password'], p):
            session['usuario']=u; return redirect('/')
        return 'Clave mal <a href=/login>volver</a>'
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh"><div style="border:1px solid #ccc;padding:30px"><h2>CEACGE - LOGIN</h2><form method=post><input name=usuario placeholder=admin value=admin><br><br><input type=password name=password placeholder=ceacge2025><br><br><button>ENTRAR</button></form></div></body>'

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall(); conn.close()
    return render_template_string("""
    <h2>CEACGE - {{alumnos|length}} alumnos</h2><a href='/nuevo' style='background:#0d6efd;color:white;padding:10px;text-decoration:none'>+ NUEVO ALUMNO</a> <a href='/logout'>Salir</a>
    <table border=1 cellpadding=8 style='width:100%;margin-top:15px'><tr><th>Foto</th><th>Nombre</th><th>Origen</th><th>PDF</th></tr>
    {% for a in alumnos %}<tr><td>{% if a['foto'] %}<img src='/fotos/{{a['foto']}}' width=50>{% endif %}</td><td>{{a['nombre']}} {{a['apellidos']}}</td><td>{{a['natural_de']}} {{a['distrito']}}</td><td><a href='/notas/{{a['id']}}'>Notas</a> | <a href='/pdf/{{a['id']}}'>HOJA ACADEMICA</a></td></tr>{% endfor %}</table>""", alumnos=alumnos)

@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; natural=request.form['natural_de']; distrito=request.form['distrito']; provincia=request.form['provincia']; centro=request.form['centro']; telefono=request.form['telefono']
        foto_file=request.files.get('foto'); fname=''
        if foto_file and foto_file.filename:
            fname=secure_filename(foto_file.filename); foto_file.save(os.path.join(UPLOAD_FOLDER, fname))
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,telefono,foto,fecha_registro) VALUES (?,?,?,?,?,?,?,?,?)"),(nombre,apellidos,natural,distrito,provincia,centro,telefono,fname, "2026"))
        conn.commit(); conn.close(); return redirect('/')
    return """
    <h2>NUEVO ALUMNO - HOJA ACADEMICA</h2>
    <form method=post enctype=multipart/form-data style='max-width:500px'>
    Nombre: <input name=nombre required style='width:100%'><br>Apellidos: <input name=apellidos required style='width:100%'><br>
    Natural de: <input name=natural_de placeholder='Ej: VABE' required style='width:100%'><br>
    Distrito: <input name=distrito placeholder='Ej: KOGO' required style='width:100%'><br>
    Provincia: <input name=provincia placeholder='Ej: LITORAL' required style='width:100%'><br>
    Centro: <input name=centro placeholder='Ej: PADRE SANTY' required style='width:100%'><br>
    Teléfono: <input name=telefono style='width:100%'><br>
    Foto Carnet: <input type=file name=foto accept='image/*'><br><br>
    <button style='padding:15px;background:green;color:white;width:100%'>GUARDAR ALUMNO</button>
    </form><a href='/'>Volver</a>"""

MATERIAS = {
 "1 ESBA": ["Lengua Española y Lit","Matemáticas","Geografía Gra. Y de GE","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"],
 "3 ESBA": ["Lengua Española y Lit","Matemáticas","H. de África y de G.E.","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"],
 "4 ESBA": ["Lengua Española y Lit","Matemáticas","H. Universal","Física y Química","Tecnología","Biología y Geología","E. Plástica y Artística","Religión","Inglés","Francés","E. Física"],
 "1 BACH": ["Matemática I","Física y Química","Dibujo Técnico I","Biología","Lengua Española","H. de África","Inglés"],
 "2 BACH": ["Matemáticas II","Electrotecnia","Química","Geografía","Dibujo Técnico"]
}

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
@login_required
def notas(alumno_id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(alumno_id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(alumno_id,))
        for curso, lista in MATERIAS.items():
            for mat in lista:
                nota=request.form.get(f"{curso}__{mat}",'')
                if nota: cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,nota) VALUES (?,?,?,?)"),(alumno_id,curso,mat,nota))
        conn.commit(); conn.close(); return redirect(f'/pdf/{alumno_id}')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(alumno_id,)); notas_db=cur.fetchall(); notas_map={(n['curso'],n['asignatura']):n['nota'] for n in notas_db}; conn.close()
    html=f"<h2>Notas de {alum['nombre']} {alum['apellidos']}</h2><form method=post>"
    for curso, lista in MATERIAS.items():
        html+=f"<h3 style='background:#eee'>{curso}</h3>"
        for mat in lista:
            val=notas_map.get((curso,mat),'')
            html+=f"{mat}: <input name='{curso}__{mat}' value='{val}' style='width:60px'> &nbsp;"
    html+="<br><br><button style='padding:15px;background:#198754;color:white'>GUARDAR Y GENERAR HOJA</button></form>"
    return html

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); notas_l=cur.fetchall(); conn.close()
    notas_map={(n['curso'],n['asignatura']):n['nota'] for n in notas_l}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    c.setFont("Helvetica-Bold",9); c.drawString(60,h-30,"REPÚBLICA DE GUINEA ECUATORIAL")
    c.setFont("Helvetica",7); c.drawString(60,h-40,"MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")
    c.setFont("Helvetica-Bold",11); c.drawString(60,h-55,f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",7); c.drawString(60,h-65,f"NATURAL DE {a['natural_de']}, DEL DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']}".upper())
    c.setFont("Helvetica-Bold",9); c.drawString(60,h-78,f"HOJA ACADÉMICA - IPES {a['centro']}")
    foto_path=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(foto_path):
        try: c.drawImage(ImageReader(foto_path), w-90, h-110, width=55, height=70, preserveAspectRatio=True)
        except: c.rect(w-90, h-110, 55, 70)
    else: c.rect(w-90, h-110, 55, 70); c.drawString(w-80,h-75,"FOTO")
    y=h-110
    c.setFont("Helvetica",6)
    for curso in ["1 ESBA","3 ESBA","4 ESBA","1 BACH","2 BACH"]:
        y-=14; c.setFont("Helvetica-Bold",6); c.drawString(35,y,curso); y-=2
        for mat in MATERIAS.get(curso,[]):
            y-=10
            if y<60: c.showPage(); y=h-30
            c.rect(90,y,130,10); c.rect(220,y,30,10); c.rect(250,y,30,10); c.rect(280,y,30,10)
            c.setFont("Helvetica",5.5); c.drawString(92,y+2,mat[:30])
            nota=notas_map.get((curso,mat),''); c.drawString(222,y+2,str(nota))
    qr_buf=gen_qr(f"CEACGE-{id:04d} {a['nombre']} - https://ceacge-final.onrender.com/pdf/{id}")
    c.drawImage(ImageReader(qr_buf), 35, 35, width=60, height=60)
    c.setFont("Helvetica",5); c.drawString(35,22,"Cualquiera que intente falsificar o duplicar este documento académico, estará incurriendo en un delito de falsificación. Registrado en Base de Datos Nacional.")
    c.setFont("Helvetica-Bold",7); c.drawString(w-120,30,"COD: CEA-001-AA")
    c.showPage(); c.save(); buf.seek(0)
    resp=make_response(buf.getvalue()); resp.headers['Content-Type']='application/pdf'; resp.headers['Content-Disposition']=f'inline; filename=HOJA_{a["nombre"]}_{id}.pdf'; return resp

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
