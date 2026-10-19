import os, sqlite3, io
from flask import Flask, request, redirect, session, send_from_directory, render_template_string, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key='CEACGE-V7-MODERNO-2COL'
basedir=os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER=os.path.join(basedir,"fotos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATABASE_URL=os.environ.get('DATABASE_URL')
USE_POSTGRES=DATABASE_URL and 'postgres' in DATABASE_URL
def get_conn():
    if USE_POSTGRES:
        import psycopg2, psycopg2.extras
        url=DATABASE_URL.replace('postgres://','postgresql://',1) if DATABASE_URL.startswith('postgres://') else DATABASE_URL
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
        if 'usuario' not in session: return redirect('/login')
        return f(*a,**kw)
    return dec
def gen_qr(text):
    qr=qrcode.QRCode(box_size=4, border=1); qr.add_data(text); qr.make(fit=True)
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
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh"><div style="border:1px solid #ccc;padding:30px"><h2>CEACGE V7</h2><form method=post><input name=usuario value=admin><br><br><input type=password name=password><br><br><button>ENTRAR</button></form></div></body>'
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)
@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall(); conn.close()
    return render_template_string("<h2>CEACGE V7 MODERNO 2 COL - {{alumnos|length}}</h2><a href='/nuevo' style='background:#0d6efd;color:white;padding:10px;text-decoration:none'>+ NUEVO</a> <a href='/logout'>Salir</a><table border=1 cellpadding=8 style='width:100%;margin-top:10px'><tr><th>Foto</th><th>Nombre</th><th>PDF</th></tr>{% for a in alumnos %}<tr><td>{% if a['foto'] %}<img src='/fotos/{{a['foto']}}' width=40>{% endif %}</td><td>{{a['nombre']}} {{a['apellidos']}}</td><td><a href='/notas/{{a['id']}}'>Notas</a> | <a href='/pdf/{{a['id']}}' style='background:#c00000;color:white;padding:5px'>PDF MODERNO</a></td></tr>{% endfor %}</table>", alumnos=alumnos)
@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        nombre=request.form['nombre']; apellidos=request.form['apellidos']; natural=request.form['natural_de']; distrito=request.form['distrito']; provincia=request.form['provincia']; centro=request.form['centro'] or 'PADRE SANTY'; anio=request.form['anio']
        foto_file=request.files.get('foto'); fname=''
        if foto_file and foto_file.filename:
            fname=secure_filename(foto_file.filename); foto_file.save(os.path.join(UPLOAD_FOLDER, fname))
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio) VALUES (?,?,?,?,?,?,?,?)"),(nombre,apellidos,natural,distrito,provincia,centro,fname,anio)); conn.commit(); conn.close(); return redirect('/')
    return "<h2>NUEVO ALUMNO</h2><form method=post enctype=multipart/form-data>Nombre:<input name=nombre required><br>Apellidos:<input name=apellidos required><br>Natural:<input name=natural_de value='VABE'><br>Distrito:<input name=distrito value='KOGO'><br>Provincia:<input name=provincia value='LITORAL'><br>Centro:<input name=centro value='PADRE SANTY'><br>Año:<input name=anio value='2023-2024'><br>Foto:<input type=file name=foto><br><br><button>GUARDAR</button></form>"

# ORDEN EXACTO COMO TU FOTO
BLOQUES_IZQ = [
 ("1 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales","E. Plástica y Visual","Religión","Francés","Inglés","E. Física"]),
 ("4 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales","E. Plástica y Visual","Religión","Francés","Inglés","E. Física"]),
 ("2 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales","E. Plástica y Visual","Religión","Francés","Inglés","E. Física"]),
]
BLOQUES_DER = [
 ("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD", ["Lengua Española y Lit","Matemáticas","Biología","Física y Química","Dibujo Técnico I","Religión"]),
 ("RAMA DE CIENCIAS SOCIALES Y HUMANIDADES", ["Latín","Literatura","Geografía de la España Actual","Matemáticas aplicadas a CC.SS."]),
 ("RAMA DE TECNOLOGÍA", ["Tecnología Industrial I","Matemáticas I","Dibujo técnico I","Física"]),
 ("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD Y TECNOLOGÍA", ["Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencias de la Tierra y Medio Ambiente","Tecnología de la Información","Biología","Física","Química"]),
]

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
@login_required
def notas(alumno_id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(alumno_id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(alumno_id,))
        for titulo, lista in BLOQUES_IZQ+BLOQUES_DER:
            for mat in lista:
                o=request.form.get(f"{titulo}__{mat}__o",''); e=request.form.get(f"{titulo}__{mat}__e",'')
                if o or e: cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(alumno_id,titulo,mat,o,e))
        conn.commit(); conn.close(); return redirect(f'/pdf/{alumno_id}')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(alumno_id,)); notas_db=cur.fetchall(); nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in notas_db}; conn.close()
    html=f"<h2>Notas {alum['nombre']}</h2><form method=post>"
    for titulo, lista in BLOQUES_IZQ+BLOQUES_DER:
        html+=f"<h4 style='background:#c00000;color:white;padding:5px'>{titulo}</h4><table border=1 cellpadding=3 style='width:100%'>"
        for mat in lista:
            o,e=nm.get((titulo,mat),('','')); html+=f"<tr><td>{mat}</td><td><input name='{titulo}__{mat}__o' value='{o}' style='width:50px'></td><td><input name='{titulo}__{mat}__e' value='{e}' style='width:50px'></td></tr>"
        html+="</table>"
    html+="<button style='padding:12px;background:#c00000;color:white;width:100%'>GUARDAR Y GENERAR PDF 1 PAGINA</button></form>"
    return html

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); notas_l=cur.fetchall(); conn.close()
    notas_map={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in notas_l}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    # HEADER AZUL
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0,h-28,w,28,fill=1,stroke=0)
    # ESCUDO + TEXTOS
    c.setFillColor(colors.HexColor("#0a2a7a")); c.setFont("Helvetica-Bold",9); c.drawString(65,h-50,f"REPÚBLICA DE GUINEA ECUATORIAL")
    c.setFont("Helvetica-Bold",7.5); c.setFillColor(colors.HexColor("#1e40af")); c.drawString(65,h-60,"MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",11); c.drawString(65,h-75,f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",6.5); c.drawString(65,h-84,f"NATURAL DE {a['natural_de']}, DEL DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']}")
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",14); c.drawCentredString(w/2,h-102,"HOJA ACADÉMICA")
    c.setFillColor(colors.HexColor("#64748b")); c.setFont("Helvetica-Bold",8); c.drawCentredString(w/2,h-113,f"IPES {a['centro']} - BATA")
    # FOTO
    xf=w-70; yf=h-85
    c.setFillColor(colors.HexColor("#e2e8f0")); c.rect(xf,yf,50,60,fill=1,stroke=1); c.setFillColor(colors.black); c.setFont("Helvetica",6); c.drawCentredString(xf+25,yf+28,"FOTO")
    foto_path=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(foto_path):
        try: c.drawImage(ImageReader(foto_path), xf, yf, width=50, height=60, preserveAspectRatio=True)
        except: pass
    # DIBUJAR BLOQUES
    def draw_block(x,y,bw, titulo, materias, is_rama=False):
        # titulo rojo si es RAMA, gris si es ESBA
        if is_rama:
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6); c.setFillColor(colors.HexColor("#b91c1c")); c.drawString(x, y, titulo[:55])
            y-=8
        else:
            # barra lateral gris CURSO
            c.setFillColor(colors.HexColor("#9ca3af")); c.rect(x, y- (len(materias)*9+12), 18, len(materias)*9+22, fill=1, stroke=0)
            c.saveState(); c.translate(x+9, y- (len(materias)*9)/2); c.rotate(90); c.setFillColor(colors.white); c.setFont("Helvetica-Bold",7); c.drawCentredString(0,0,"CURSO"); c.restoreState()
            # cabecera ESBA gris oscuro
            c.setFillColor(colors.HexColor("#9ca3af")); c.rect(x+18, y, bw-18, 10, fill=1, stroke=0)
            c.setFillColor(colors.black); c.setFont("Helvetica-Bold",6.5); c.drawString(x+22, y+2, titulo)
            y-=2
        # cuerpo celeste claro
        bh=len(materias)*9
        c.setFillColor(colors.HexColor("#bfdbfe")); c.rect(x+18 if not is_rama else x, y-bh-2, bw-18 if not is_rama else bw, bh+4, fill=1, stroke=0)
        yy=y-8
        for mat in materias:
            c.setFillColor(colors.white); c.rect(x+18 if not is_rama else x, yy, (bw-18 if not is_rama else bw)-40, 8, fill=1, stroke=1)
            c.rect(x+ (bw-40) if not is_rama else x+bw-40, yy, 20, 8, fill=1, stroke=1)
            c.rect(x+ bw-20 if not is_rama else x+bw-20, yy, 20, 8, fill=1, stroke=1)
            c.setFillColor(colors.HexColor("#1e293b")); c.setFont("Helvetica",5); c.drawString(x+20 if not is_rama else x+2, yy+2, mat[:32])
            o,e=notas_map.get((titulo,mat),('',''))
            c.setFont("Helvetica-Bold",5.5); c.drawCentredString(x+ (bw-30) if not is_rama else x+bw-30, yy+2, o); c.drawCentredString(x+ bw-10 if not is_rama else x+bw-10, yy+2, e)
            yy-=9
        return yy-10

    # COL IZQUIERDA
    x1=10; bw1= w/2 -15
    y_cur=h-125
    for titulo, mats in BLOQUES_IZQ:
        y_cur=draw_block(x1, y_cur, bw1, titulo, mats, is_rama=False)
    # COL DERECHA
    x2= w/2 +5; bw2= w/2 -15
    y_cur2=h-125
    for titulo, mats in BLOQUES_DER:
        y_cur2=draw_block(x2, y_cur2, bw2, titulo, mats, is_rama=True)
        y_cur2-=4

    # FOOTER
    qr_buf=gen_qr(f"CEACGE-{id} {a['nombre']} | ceacge-final.onrender.com/pdf/{id}")
    c.drawImage(ImageReader(qr_buf), 12, 10, width=38, height=38)
    c.setFillColor(colors.HexColor("#b91c1c")); c.setFont("Helvetica",4.5)
    c.drawString(55,28,"La falsificación de este documento constituye delito, penado según el Código Penal de la República de Guinea Ecuatorial. Este documento es válido únicamente con sello y firma oficial del Ministerio de Educación, Ciencia, Enseñanza Universitaria y Profesional.")
    c.drawString(55,22,"Queda estrictamente prohibida su reproducción o alteración sin autorización oficial.")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",6); c.drawString(w-110,12,f"COD: CEA-{id:04d}-AA")
    c.showPage(); c.save(); buf.seek(0)
    resp=make_response(buf.getvalue()); resp.headers['Content-Type']='application/pdf'; resp.headers['Content-Disposition']=f'inline; filename=HOJA_MODERNA_{id}.pdf'; return resp

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
