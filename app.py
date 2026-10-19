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
app.secret_key = 'CEACGE-V5-CLON'
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
        conn=sqlite3.connect(os.path.join(basedir,"ceacge.db")); conn.row_factory=sqlite3.Row; return conn
def adapt(q): return q.replace('?','%s') if USE_POSTGRES else q

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if USE_POSTGRES:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, foto TEXT, anio TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellidos TEXT, natural_de TEXT, distrito TEXT, provincia TEXT, centro TEXT, foto TEXT, anio TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
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
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh"><div style="border:1px solid #ccc;padding:30px"><h2>CEACGE - HOJA ACADEMICA</h2><form method=post><input name=usuario value=admin><br><br><input type=password name=password placeholder=ceacge2025><br><br><button>ENTRAR</button></form></div></body>'

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall(); conn.close()
    return render_template_string("""
    <h2>CEACGE - HOJA ACADÉMICA IDÉNTICA - {{alumnos|length}}</h2>
    <a href='/nuevo' style='background:#0d6efd;color:white;padding:12px;text-decoration:none;border-radius:6px'>+ NUEVO ALUMNO</a> <a href='/logout'>Salir</a>
    <table border=1 cellpadding=8 style='width:100%;margin-top:15px;border-collapse:collapse'><tr><th>Foto</th><th>Nombre</th><th>Origen</th><th>PDF</th></tr>
    {% for a in alumnos %}<tr><td>{% if a['foto'] %}<img src='/fotos/{{a['foto']}}' width=50>{% endif %}</td><td>{{a['nombre']}} {{a['apellidos']}}</td><td>{{a['natural_de']}}/{{a['distrito']}}/{{a['provincia']}}</td><td><a href='/notas/{{a['id']}}'>Notas</a> | <a href='/pdf/{{a['id']}}' style='background:green;color:white;padding:5px;text-decoration:none'>HOJA EXACTA</a></td></tr>{% endfor %}</table>""", alumnos=alumnos)

@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; natural=request.form['natural_de']; distrito=request.form['distrito']; provincia=request.form['provincia']; centro=request.form['centro'] or 'PADRE SANTY'; anio=request.form['anio']
        foto_file=request.files.get('foto'); fname=''
        if foto_file and foto_file.filename:
            fname=secure_filename(foto_file.filename); foto_file.save(os.path.join(UPLOAD_FOLDER, fname))
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio) VALUES (?,?,?,?,?,?,?,?)"),(nombre,apellidos,natural,distrito,provincia,centro,fname,anio))
        conn.commit(); conn.close(); return redirect('/')
    return """
    <h2>NUEVO ALUMNO - Formato Hoja Original</h2>
    <form method=post enctype=multipart/form-data style='max-width:500px'>
    Nombre: <input name=nombre required style='width:100%'><br>Apellidos: <input name=apellidos required style='width:100%'><br>
    Natural de: <input name=natural_de value='VABE' required style='width:100%'><br>
    Distrito: <input name=distrito value='KOGO' required style='width:100%'><br>
    Provincia: <input name=provincia value='LITORAL' required style='width:100%'><br>
    Centro: <input name=centro value='PADRE SANTY' style='width:100%'><br>
    Año escolar: <input name=anio placeholder='2023-2024' style='width:100%'><br>
    Foto Carnet (arriba derecha como PDF): <input type=file name=foto accept='image/*'><br><br>
    <button style='padding:15px;background:green;color:white;width:100%'>GUARDAR</button>
    </form><a href='/'>Volver</a>"""

# MATERIAS EXACTAS DEL PDF QUE ENVIASTE
MATERIAS_ORDEN = [
 ("1 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gra. Y de GE","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("3 ESBA", ["Lengua Española y Lit","Matemáticas","H. de África y de G.E.","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"]),
 ("4 ESBA", ["Lengua Española y Lit","Matemáticas","H. Universal","Física y Química","Tecnología","Biología y Geología","E. Plástica y Artística","Religión","Inglés","Francés","E. Física"]),
 ("1 BACH", ["Lengua Española","H. de África y de G.E.","Educación Física","Religión","Francés","Inglés","CC. De la Tierra y M.","Biología","Matemática I","Física y Química","Dibujo Técnico I","Literatura","Historia del Mundo Actual","Historia de la Filosofía","Geografía de G. Espa. Mund.","Matemáticas Aplic. ACC.","Tecnología Industrial"]),
 ("2 BACH", ["Matemáticas II","Electrotecnia","Química","Geografía","Tecnología Industrial","Dibujo Técnico","Matemáticas Apl. A las C.S. II","Historia de Arte","Latín","Griego","Biología","Literatura","Historia del Mundo Actual","Economía de la Empresa","Religión","Francés","Inglés"]),
]

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
@login_required
def notas(alumno_id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(alumno_id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(alumno_id,))
        for curso, lista in MATERIAS_ORDEN:
            for mat in lista:
                ord_n=request.form.get(f"{curso}__{mat}__ord",'')
                extra_n=request.form.get(f"{curso}__{mat}__extra",'')
                if ord_n or extra_n:
                    cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(alumno_id,curso,mat,ord_n,extra_n))
        conn.commit(); conn.close(); return redirect(f'/pdf/{alumno_id}')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(alumno_id,)); notas_db=cur.fetchall(); notas_map={ (n['curso'],n['asignatura']): (n['ord'], n['extra']) for n in notas_db}; conn.close()
    html=f"<h2>Notas Hoja Académica: {alum['nombre']} {alum['apellidos']}</h2><form method=post>"
    for curso, lista in MATERIAS_ORDEN:
        html+=f"<h3 style='background:#000;color:white;padding:6px'>{curso} - CURSO........... AÑO ESCOLAR {alum['anio'] or ''}</h3><table border=1 cellpadding=4 style='border-collapse:collapse;width:100%'><tr><th>ASIGNATURA</th><th>ORDINARIO</th><th>EXTRAORDINARIO</th></tr>"
        for mat in lista:
            o,e=notas_map.get((curso,mat),('',''))
            html+=f"<tr><td>{mat}</td><td><input name='{curso}__{mat}__ord' value='{o}' style='width:70px'></td><td><input name='{curso}__{mat}__extra' value='{e}' style='width:70px'></td></tr>"
        html+="</table><br>"
    html+="<button style='padding:15px;background:#198754;color:white;width:100%;font-size:18px'>GUARDAR Y GENERAR PDF IDENTICO</button></form>"
    return html

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); notas_l=cur.fetchall(); conn.close()
    notas_map={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in notas_l}

    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4

    # === CLON EXACTO DEL PDF QUE ENVIASTE ===
    c.setFont("Helvetica-Bold",8.5); c.drawCentredString(w/2,h-20,"REPÚBLICA DE GUINEA ECUATORIAL")
    c.setFont("Helvetica",7); c.drawCentredString(w/2,h-30,"MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")
    c.setFont("Helvetica-Bold",10); c.drawString(40,h-55,f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",7.5); c.drawString(40,h-66,f"NATURAL DE {a['natural_de']}, DEL DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']}")
    c.setFont("Helvetica-Bold",11); c.drawCentredString(w/2,h-82,"HOJA ACADÉMICA")
    c.setFont("Helvetica",8); c.drawString(40,h-94,f"IPES \"{a['centro']}—BATA.")
    c.setFont("Helvetica-Bold",7); c.drawString(40,h-105,f"AÑO ESCOLAR {a['anio'] or '........'}")

    # FOTO RECUADRO ARRIBA DERECHA - IDENTICO
    foto_path=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    x_foto=w-85; y_foto=h-115
    c.rect(x_foto, y_foto, 55, 70); c.setFont("Helvetica-Bold",8); c.drawCentredString(x_foto+27, y_foto+30,"FOTO")
    if a['foto'] and os.path.exists(foto_path):
        try: c.drawImage(ImageReader(foto_path), x_foto, y_foto, width=55, height=70, preserveAspectRatio=True, mask='auto')
        except: pass

    # TABLA MAESTRA - COMO TU PDF - 2 COLUMNAS GRANDES
    y_start=h-115; left_x=30; col_width=w-60
    c.setFont("Helvetica-Bold",6); c.setLineWidth(0.6)

    # Dibujamos las cabeceras por cada curso
    y=y_start-10
    for idx, (curso, mats) in enumerate(MATERIAS_ORDEN):
        if y < 100: # nueva pagina si no cabe
            c.showPage(); y=h-40
        # CABECERA CURSO
        c.setFillColor(colors.HexColor("#e0e0e0")); c.rect(left_x, y-12, col_width, 12, fill=1, stroke=1)
        c.setFillColor(colors.black); c.setFont("Helvetica-Bold",7); c.drawString(left_x+5, y-9, f"CURSO............  {curso}   AÑO ESCOLAR {a['anio'] or ''}")
        c.setFont("Helvetica-Bold",5.5)
        c.rect(left_x, y-24, 180, 12); c.rect(left_x+180, y-24, 60, 12); c.rect(left_x+240, y-24, 60, 12)
        c.drawString(left_x+2, y-20, "ASIGNATURAS"); c.drawString(left_x+185, y-20, "ORDINARIOS"); c.drawString(left_x+245, y-20, "EXTRAORD.")
        y-=24
        c.setFont("Helvetica",5.8)
        for mat in mats:
            if y < 70:
                c.showPage(); y=h-40
            o,e=notas_map.get((curso,mat),('',''))
            c.rect(left_x, y-10, 180, 10); c.rect(left_x+180, y-10, 60, 10); c.rect(left_x+240, y-10, 60, 10)
            c.drawString(left_x+3, y-7, mat[:38])
            c.drawString(left_x+185, y-7, o); c.drawString(left_x+245, y-7, e)
            y-=10
        y-=6

    # RAMAS BACH - como en tu PDF
    # Footer
    qr_buf=gen_qr(f"CEACGE-{id:04d} {a['nombre']} {a['apellidos']} | VERIFICAR: ceacge-final.onrender.com/pdf/{id}")
    c.drawImage(ImageReader(qr_buf), 30, 30, width=55, height=55)
    c.setFont("Helvetica",5); c.setFillColor(colors.red)
    c.drawString(90, 55,"Cualquiera que intente falsificar o duplicar este documento académico, estará incurriendo en un delito de \"de")
    c.drawString(90, 48,"falsificación\". Los antecedentes de ésta Hoja Académica, están registrados en una base de Datos Nacional de")
    c.drawString(90, 41,"Guinea Ecuatorial. COD: CEA-001-AA")
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold",6.5); c.drawString(w-110, 30, f"COD: CEA-{id:04d}-AA")

    c.showPage(); c.save(); buf.seek(0)
    resp=make_response(buf.getvalue()); resp.headers['Content-Type']='application/pdf'; resp.headers['Content-Disposition']=f'inline; filename=HOJA_ACADEMICA_{a["nombre"]}_{id}.pdf'; return resp

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
