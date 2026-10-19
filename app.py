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
app.secret_key = 'CEACGE-V6-MODERNO'
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
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh"><div style="border:1px solid #ccc;padding:30px"><h2>CEACGE MODERNO</h2><form method=post><input name=usuario value=admin><br><br><input type=password name=password placeholder=ceacge2025><br><br><button>ENTRAR</button></form></div></body>'

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall(); conn.close()
    return render_template_string("""
    <h2>CEACGE V6 MODERNO - {{alumnos|length}} alumnos</h2>
    <a href='/nuevo' style='background:#0d6efd;color:white;padding:12px;text-decoration:none'>+ NUEVO</a> <a href='/logout'>Salir</a>
    <table border=1 cellpadding=8 style='width:100%;margin-top:15px'><tr><th>Foto</th><th>Nombre</th><th>Origen</th><th>PDF MODERNO</th></tr>
    {% for a in alumnos %}<tr><td>{% if a['foto'] %}<img src='/fotos/{{a['foto']}}' width=50>{% endif %}</td><td>{{a['nombre']}} {{a['apellidos']}}</td><td>{{a['natural_de']}}/{{a['distrito']}}</td><td><a href='/notas/{{a['id']}}'>Notas</a> | <a href='/pdf/{{a['id']}}' style='background:#c00000;color:white;padding:6px;text-decoration:none'>PDF MODERNO 1 PAGINA</a></td></tr>{% endfor %}</table>""", alumnos=alumnos)

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
    <h2>NUEVO ALUMNO</h2>
    <form method=post enctype=multipart/form-data style='max-width:500px'>
    Nombre: <input name=nombre required style='width:100%'><br>Apellidos: <input name=apellidos required style='width:100%'><br>
    Natural de: <input name=natural_de value='VABE' required style='width:100%'><br>Distrito: <input name=distrito value='KOGO' required style='width:100%'><br>Provincia: <input name=provincia value='LITORAL' required style='width:100%'><br>
    Centro: <input name=centro value='PADRE SANTY' style='width:100%'><br>Año: <input name=anio value='2023-2024' style='width:100%'><br>
    Foto: <input type=file name=foto accept='image/*'><br><br>
    <button style='padding:15px;background:green;color:white;width:100%'>GUARDAR</button></form>"""

MATERIAS_ORDEN = [
 ("1 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gra. Y de GE","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("3 ESBA", ["Lengua Española y Lit","Matemáticas","H. de África y de G.E.","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"]),
 ("4 ESBA", ["Lengua Española y Lit","Matemáticas","H. Universal","Física y Química","Tecnología","Biología y Geología","E. Plástica y Artística","Religión","Inglés","Francés","E. Física"]),
 ("1 BACH", ["Lengua Española","H. de África y de G.E.","Religión","Francés","Inglés","CC. De la Tierra y M.","Biología","Matemática I","Física y Química","Dibujo Técnico I","Lit. y Filo","Geografía de GE","Mat. Aplic.","Tecn. Industrial"]),
 ("2 BACH", ["Matemáticas II","Electrotecnia","Química","Geografía","Tecn. Industrial","Dibujo Técnico","Mat. Apl. CCSS II","Hist. Arte","Latín","Griego","Biología","Literatura","Economía","Religión","Inglés"]),
]

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
@login_required
def notas(alumno_id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(alumno_id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(alumno_id,))
        for curso, lista in MATERIAS_ORDEN:
            for mat in lista:
                ord_n=request.form.get(f"{curso}__{mat}__ord",''); extra_n=request.form.get(f"{curso}__{mat}__extra",'')
                if ord_n or extra_n: cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(alumno_id,curso,mat,ord_n,extra_n))
        conn.commit(); conn.close(); return redirect(f'/pdf/{alumno_id}')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(alumno_id,)); notas_db=cur.fetchall(); notas_map={ (n['curso'],n['asignatura']): (n['ord'], n['extra']) for n in notas_db}; conn.close()
    html=f"<h2>Notas: {alum['nombre']} {alum['apellidos']}</h2><form method=post>"
    for curso, lista in MATERIAS_ORDEN:
        html+=f"<h3 style='background:#0f2c5c;color:white;padding:6px'>{curso}</h3><table border=1 cellpadding=4 style='width:100%'><tr><th>ASIGNATURA</th><th>ORD</th><th>EXTRA</th></tr>"
        for mat in lista:
            o,e=notas_map.get((curso,mat),('','')); html+=f"<tr><td>{mat}</td><td><input name='{curso}__{mat}__ord' value='{o}' style='width:60px'></td><td><input name='{curso}__{mat}__extra' value='{e}' style='width:60px'></td></tr>"
        html+="</table>"
    html+="<br><button style='padding:15px;background:#c00000;color:white;width:100%'>GUARDAR Y GENERAR PDF MODERNO 1 PAGINA</button></form>"
    return html

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); notas_l=cur.fetchall(); conn.close()
    notas_map={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in notas_l}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4

    # --- ENCABEZADO MODERNO CON COLORES ---
    c.setFillColor(colors.HexColor("#0f2c5c")); c.rect(0, h-55, w, 55, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",9); c.drawString(20, h-20, "REPÚBLICA DE GUINEA ECUATORIAL")
    c.setFont("Helvetica",7); c.drawString(20, h-32, "MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")
    c.setFont("Helvetica-Bold",7); c.drawString(20, h-45, f"IPES \"{a['centro']} — BATA\"  |  AÑO: {a['anio']}")
    # FOTO con borde rojo
    foto_path=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    xf=w-70; yf=h-60
    c.setFillColor(colors.HexColor("#c00000")); c.rect(xf-2, yf-2, 59, 74, fill=1, stroke=0)
    c.setFillColor(colors.white); c.rect(xf, yf, 55, 70, fill=1, stroke=0)
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",7); c.drawCentredString(xf+27, yf+30,"FOTO")
    if a['foto'] and os.path.exists(foto_path):
        try: c.drawImage(ImageReader(foto_path), xf, yf, width=55, height=70, preserveAspectRatio=True, mask='auto')
        except: pass

    # DATOS ALUMNO
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",11); c.drawString(20, h-75, f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",7.5); c.drawString(20, h-87, f"NATURAL DE {a['natural_de']}, DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']}")
    # TITULO ROJO
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",16); c.drawCentredString(w/2, h-105, "HOJA ACADÉMICA")
    c.setFillColor(colors.HexColor("#0f2c5c")); c.rect(0, h-110, w, 2, fill=1, stroke=0)

    # FUNCION PARA DIBUJAR UN CUADRO DE CURSO
    def draw_curso_box(x, y, bw, bh, curso_nombre, materias):
        # Cabecera azul
        c.setFillColor(colors.HexColor("#1e3a8a")); c.rect(x, y, bw, 14, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6.5); c.drawString(x+4, y+4, f"{curso_nombre}")
        c.setFont("Helvetica-Bold",5); c.drawString(x+bw-55, y+4, "ORD")
        c.drawString(x+bw-28, y+4, "EXTRA")
        # Subcabecera
        y2=y-8
        c.setFillColor(colors.HexColor("#dbeafe")); c.rect(x, y2, bw, 8, fill=1, stroke=1)
        c.setFillColor(colors.black); c.setFont("Helvetica-Bold",5); c.drawString(x+2, y2+2, "ASIGNATURAS")
        yy=y2-8
        c.setFont("Helvetica",5.2)
        for mat in materias:
            if yy < 5: break
            # fila alternada
            if materias.index(mat)%2==0: c.setFillColor(colors.HexColor("#f8fafc")); c.rect(x, yy, bw, 8, fill=1, stroke=0)
            c.setFillColor(colors.black); c.rect(x, yy, bw, 8, stroke=1)
            # lineas verticales ORD EXTRA
            c.line(x+bw-60, yy, x+bw-60, yy+8); c.line(x+bw-30, yy, x+bw-30, yy+8)
            o,e=notas_map.get((curso_nombre,mat),('',''))
            c.drawString(x+2, yy+2, mat[:28])
            c.setFont("Helvetica-Bold",5.5); c.drawCentredString(x+bw-45, yy+2, o); c.drawCentredString(x+bw-15, yy+2, e); c.setFont("Helvetica",5.2)
            yy-=8
        return yy

    # --- ORDEN QUE PEDISTE: 3 ARRIBA, 2 ABAJO PARA QUE SEA 1 PAGINA ---
    top_y = h-125
    bw = (w-40)/3 - 4  # 3 columnas
    # FILA 1
    y1_end = draw_curso_box(15, top_y, bw, 100, "1 ESBA", MATERIAS_ORDEN[0][1])
    y2_end = draw_curso_box(15+bw+6, top_y, bw, 100, "3 ESBA", MATERIAS_ORDEN[1][1])
    y3_end = draw_curso_box(15+(bw+6)*2, top_y, bw, 100, "4 ESBA", MATERIAS_ORDEN[2][1])
    # FILA 2 - MAS GRANDES
    second_y = min(y1_end, y2_end, y3_end) - 16
    bw2 = (w-30)/2 - 6
    draw_curso_box(15, second_y, bw2, 120, "1 BACH - RAMA CIENCIAS/SALUD/TEC/HUM", MATERIAS_ORDEN[3][1])
    draw_curso_box(15+bw2+8, second_y, bw2, 120, "2 BACH - RAMAS", MATERIAS_ORDEN[4][1])

    # FOOTER QR Y SEGURIDAD
    qr_buf=gen_qr(f"CEACGE-{id:04d} {a['nombre']} | ceacge-final.onrender.com/pdf/{id}")
    c.drawImage(ImageReader(qr_buf), 15, 12, width=48, height=48)
    c.setFont("Helvetica",5); c.setFillColor(colors.HexColor("#c00000"))
    c.drawString(70, 38, "Cualquiera que intente falsificar o duplicar este documento académico, estará incurriendo en un delito de falsificación.")
    c.drawString(70, 31, "Los antecedentes de ésta Hoja Académica, están registrados en una base de Datos Nacional de Guinea Ecuatorial.")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",6); c.drawString(w-100, 20, f"COD: CEA-{id:04d}-AA | {a['anio']}")

    c.showPage(); c.save(); buf.seek(0)
    resp=make_response(buf.getvalue()); resp.headers['Content-Type']='application/pdf'; resp.headers['Content-Disposition']=f'inline; filename=HOJA_MODERNA_{a["nombre"]}_{id}.pdf'; return resp

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
