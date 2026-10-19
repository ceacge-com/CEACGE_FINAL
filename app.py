import os, sqlite3, io, base64, datetime
from flask import Flask, request, redirect, session, send_from_directory, render_template_string, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','CEACGE-HOJA-ACADEMICA-ID')
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, "fotos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

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
        cur.execute("""CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, codigo_centro TEXT, telefono TEXT, foto TEXT, fecha_registro TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre TEXT, codigo TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, nota TEXT)""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, codigo_centro TEXT, telefono TEXT, foto TEXT, fecha_registro TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, codigo TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, nota TEXT)""")
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

def gen_qr_buf(text):
    qr=qrcode.QRCode(box_size=8, border=1)
    qr.add_data(text); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white").convert('RGB')
    buf=io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return buf

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['usuario']; p=request.form['password']
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,)); user=cur.fetchone(); conn.close()
        if user and check_password_hash(user['password'], p):
            session['usuario']=u; return redirect('/')
        return '<h3>Clave incorrecta</h3><a href=/login>Volver</a>'
    return '<style>body{font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5} .b{background:white;padding:30px;border-radius:10px}</style><div class=b><h2>CEACGE - HOJA ACADEMICA</h2><form method=post><input name=usuario value=admin><input name=password type=password placeholder=ceacge2025><button>ENTRAR</button></form></div>'

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall(); conn.close()
    return render_template_string("""
    <style>body{font-family:Arial;margin:20px} .btn{background:#0d6efd;color:white;padding:12px;text-decoration:none;border-radius:8px}</style>
    <h2>CEACGE - HOJA ACADÉMICA - {{alumnos|length}} alumnos</h2>
    <a class=btn href='/nuevo'>+ NUEVO ALUMNO</a> <a href='/logout'>Salir</a>
    <table border=1 cellpadding=8 style='width:100%;margin-top:15px;border-collapse:collapse'>
    <tr><th>Foto</th><th>Nombre</th><th>Origen</th><th>Acciones</th></tr>
    {% for a in alumnos %}<tr><td>{% if a['foto'] %}<img src='/fotos/{{a['foto']}}' width=50>{% endif %}</td><td>{{a['nombre']}} {{a['apellidos']}}</td><td>{{a['natural_de']}}/{{a['distrito']}}</td><td><a href='/alumno/{{a['id']}}'>Ver</a> | <a href='/notas/{{a['id']}}'>Notas</a> | <a href='/pdf/{{a['id']}}'>PDF Hoja Académica</a></td></tr>{% endfor %}
    </table>""", alumnos=alumnos)

@app.route('/alumno/<int:id>')
@login_required
def ver_alumno(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone(); conn.close()
    return f"<h2>{a['nombre']} {a['apellidos']}</h2><p>{a['natural_de']} - {a['distrito']} - {a['provincia']}</p><img src='/fotos/{a['foto']}' width=200><br><a href='/notas/{id}'>Gestionar Notas</a> | <a href='/pdf/{id}'>Descargar HOJA ACADÉMICA PDF</a> | <a href='/'>Volver</a>"

# PLANTILLA NOTAS
MATERIAS = {
    "1 ESBA": ["Lengua Española y Lit","Matemáticas","Geografía Gra. Y de GE","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"],
    "3 ESBA": ["Lengua Española y Lit","Matemáticas","H. de África y de G.E.","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"],
    "4 ESBA": ["Lengua Española y Lit","Matemáticas","H. Universal","Física y Química","Tecnología","Biología y Geología","E. Plástica y Artística","Religión","Inglés","Francés","E. Física"],
    "1 BACH": ["Lengua Española","H. de África y de G.E.","Educación Física","Religión","Francés","Inglés","CC. De la Tierra y M.","Biología","Matemática I","Física y Química","Dibujo Técnico I","Biología","Latín","Griego","Geografía de G. Espa. Mund.","Matemáticas Aplic. ACC.","Tecnología Industrial","Matemáticas I","Dibujo Técnico I","Biología","Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencia de la Naturaleza y Salud","Economía de la Empresa","Religión","Francés","Inglés"],
    "2 BACH": ["Matemáticas II","Electrotecnia","Química","Geografía","Tecnología Industrial","Matemáticas II","Electrotecnia","Dibujo Técnico","Matemáticas Apl. A las C.S. II","Historia de Arte","Latín","Griego"]
}

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
@login_required
def notas(alumno_id):
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(alumno_id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(alumno_id,))
        for curso, lista in MATERIAS.items():
            for mat in lista:
                key = f"{curso}__{mat}"
                nota = request.form.get(key,'')
                if nota:
                    cur.execute(adapt("INSERT INTO notas (alumno_id, curso, asignatura, nota) VALUES (?,?,?,?)"),(alumno_id, curso, mat, nota))
        conn.commit()
        conn.close()
        return redirect(f'/pdf/{alumno_id}')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(alumno_id,)); notas_db=cur.fetchall()
    notas_map={(n['curso'],n['asignatura']):n['nota'] for n in notas_db}
    conn.close()
    html=f"<h2>Notas de {alum['nombre']} {alum['apellidos']}</h2><form method=post>"
    for curso, lista in MATERIAS.items():
        html+=f"<h3 style='background:#e9ecef;padding:5px'>{curso}</h3>"
        for mat in lista:
            val=notas_map.get((curso,mat),'')
            html+=f"<div style='display:inline-block;width:320px;margin:3px'>{mat}: <input name='{curso}__{mat}' value='{val}' style='width:50px' placeholder='Nota'></div>"
    html+="<br><br><button style='padding:15px;background:#198754;color:white;border:0'>GUARDAR Y GENERAR PDF</button></form><a href='/'>Volver</a>"
    return html

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); notas_l=cur.fetchall(); conn.close()
    notas_map={(n['curso'],n['asignatura']):n['nota'] for n in notas_l}

    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    
    # ESCUDO y CABECERA
    c.setFont("Helvetica-Bold",9); c.drawString(60,h-30,"REPÚBLICA DE GUINEA ECUATORIAL")
    c.setFont("Helvetica",7); c.drawString(60,h-40,"MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")
    c.setFont("Helvetica-Bold",11); c.drawString(60,h-55,f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",7); c.drawString(60,h-65,f"NATURAL DE {a['natural_de']}, DEL DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']}".upper())
    c.setFont("Helvetica-Bold",9); c.drawString(60,h-80,f"HOJA ACADÉMICA")
    c.setFont("Helvetica",8); c.drawString(60,h-95,f"IPES \"{a['centro']} - BATA\"")
    
    # FOTO
    foto_path=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(foto_path):
        try: c.drawImage(ImageReader(foto_path), w-90, h-110, width=55, height=70, preserveAspectRatio=True)
        except: c.rect(w-90, h-110, 55, 70)
    else:
        c.rect(w-90, h-110, 55, 70); c.drawString(w-80,h-80,"FOTO")
    
    c.setFont("Helvetica",6)
    # DIBUJAR TABLAS COMO EN EL PDF ORIGINAL
    y = h-120
    def draw_curso_block(title, y_pos, materias, curso_key):
        c.setFont("Helvetica-Bold",6); c.drawString(35, y_pos, title)
        x=90; col_w=120; note_w=30
        # header
        # Asignaturas
        c.setFont("Helvetica",5.5)
        for mat in materias:
            y_pos-=10
            if y_pos<60:
                c.showPage(); y_pos=h-30
            c.rect(x, y_pos, col_w, 10); c.rect(x+col_w, y_pos, note_w, 10); c.rect(x+col_w+note_w, y_pos, note_w, 10); c.rect(x+col_w+note_w*2, y_pos, note_w, 10)
            c.drawString(x+2, y_pos+2, mat[:28])
            nota=notas_map.get((curso_key,mat),'')
            if nota: c.drawString(x+col_w+5, y_pos+2, str(nota))
        return y_pos-5

    y = draw_curso_block("1 ESBA", y, MATERIAS["1 ESBA"], "1 ESBA")
    y = draw_curso_block("3 ESBA", y-10, MATERIAS["3 ESBA"], "3 ESBA")
    y = draw_curso_block("4 ESBA", y-10, MATERIAS["4 ESBA"], "4 ESBA")
    
    # Lado derecho - 1 BACH y 2 BACH
    y2 = h-120
    # 1 BACH box right side
    x_right = 300
    c.setFont("Helvetica-Bold",5); c.setFillColor(colors.red); c.drawString(x_right, y2, "RAMA DE CIENCIA DE LA NATURALEZA Y SALUD"); c.setFillColor(colors.black)
    y2-=10
    for mat in ["Matemática I","Física y Química","Dibujo Técnico I","Biología"]:
        y2-=10; c.rect(x_right, y2, 120, 10); c.rect(x_right+120, y2, 25, 10); c.drawString(x_right+2, y2+2, mat)
        nota=notas_map.get(("1 BACH",mat),''); c.drawString(x_right+125, y2+2, nota)
    
    # QR abajo izquierda
    qr_buf=gen_qr_buf(f"CEACGE-{a['id']:04d} {a['nombre']} {a['apellidos']} - VERIFICACION: https://ceacge-final.onrender.com/alumno/{a['id']}")
    c.drawImage(ImageReader(qr_buf), 35, 35, width=60, height=60)
    c.setFont("Helvetica",5); c.setFillColor(colors.red)
    c.drawString(35,25,"Cualquiera que intente falsificar o duplicar este documento académico, estará incurriendo en un delito de \"de falsificación\". Los antecedentes de ésta Hoja Académica, están registrados en una base de Datos Nacional de Guinea Ecuatorial.")
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold",7); c.drawString(w-120,30,"COD: CEA-001-AA")
    
    c.showPage(); c.save(); buf.seek(0)
    resp=make_response(buf.getvalue()); resp.headers['Content-Type']='application/pdf'; resp.headers['Content-Disposition']=f'inline; filename=HOJA_{a["nombre"]}_{a["id"]}.pdf'; return resp

try: init_db()
except Exception as e: print(e)

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
