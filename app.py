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

app=Flask(__name__)
app.secret_key='V12-1-2-3-4-1BACH-2BACH-22PTS'
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
        return 'Clave mal'
    return '<h2>CEACGE V12</h2><form method=post><input name=usuario value=admin><br><input type=password name=password><br><button>ENTRAR</button></form>'
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)
@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); a=cur.fetchall(); conn.close()
    return render_template_string("<h2>V12 - 1-2-3-4 + 1BACH 2BACH - {{a|length}}</h2><a href='/nuevo'>+ NUEVO</a> | <a href='/logout'>Salir</a><table border=1><tr><th>Foto</th><th>Nombre</th><th>PDF</th></tr>{% for x in a %}<tr><td><img src='/fotos/{{x['foto']}}' width=30></td><td>{{x['nombre']}} {{x['apellidos']}}</td><td><a href='/notas/{{x['id']}}'>Notas</a> | <a href='/pdf/{{x['id']}}'>PDF V12</a></td></tr>{% endfor %}</table>", a=a)
@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        n=request.form['nombre']; ap=request.form['apellidos']; nat=request.form['natural_de']; dis=request.form['distrito']; prov=request.form['provincia']; cen=request.form['centro']; an=request.form['anio']
        f=request.files.get('foto'); fn=''
        if f and f.filename:
            fn=secure_filename(f.filename); f.save(os.path.join(UPLOAD_FOLDER, fn))
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio) VALUES (?,?,?,?,?,?,?,?)"),(n,ap,nat,dis,prov,cen,fn,an)); conn.commit(); cur.execute(adapt("SELECT id FROM alumnos ORDER BY id DESC LIMIT 1")); nid=cur.fetchone()['id']; conn.close(); return redirect(f'/notas/{nid}')
    return "<form method=post enctype=multipart/form-data>Nombre<input name=nombre><br>Apellidos<input name=apellidos><br>Natural<input name=natural_de value='VABE'><br>Distrito<input name=distrito value='KOGO'><br>Provincia<input name=provincia value='LITORAL'><br>Centro<input name=centro value='PADRE SANTY'><br>Año<input name=anio value='2023-2024'><br>Foto<input type=file name=foto><br><button>GUARDAR</button></form>"

# === ORDEN QUE PEDISTE ===
BLOQUES_IZQ = [
 ("1 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("2 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("3 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Biología y Geología","Física y Química","Tecnología","E. Plástica y Visual I","Religión","Inglés","Francés","E. Física"]),
 ("4 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"]),
]

# DERECHA: rojas + 1 BACH y 2 BACH azules como pediste
# Formato: (titulo, materias, es_roja)
BLOQUES_DER = [
 ("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD", ["Lengua Española y Lit","Matemáticas","Biología","Física y Química","Dibujo Técnico I","Religión"], True),
 ("RAMA DE CIENCIAS SOCIALES Y HUMANIDADES", ["Latín","Literatura","Geografía de la España Actual","Mat. aplicadas a CC.SS."], True),
 ("1 BACH", ["Lengua Española y Lit","Matemáticas I","Física y Química","Filosofía","Historia del Mundo Contemporáneo","Inglés","Francés","E. Física","Religión"], False),
 ("RAMA DE TECNOLOGÍA", ["Tecnología Industrial I","Matemáticas I","Dibujo técnico I","Física"], True),
 ("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD Y TECNOLOGÍA", ["Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencias de la Tierra y Medio Ambiente","Tecnología de la Información","Biología","Física","Química"], True),
 ("2 BACH", ["Lengua Española y Lit","Matemáticas II","Física","Química","Biología","Historia de España","Inglés","Filosofía","E. Física"], False),
]

@app.route('/notas/<int:id>', methods=['GET','POST'])
@login_required
def notas(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(id,))
        for bloque in BLOQUES_IZQ+BLOQUES_DER:
            titulo=bLoque[0] if False else bloque[0]; lista=bloque[1]
            for mat in lista:
                o=request.form.get(f"{titulo}__{mat}__o",''); e=request.form.get(f"{titulo}__{mat}__e",'')
                if o or e: cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(id,titulo,mat,o,e))
        conn.commit(); conn.close(); return redirect(f'/pdf/{id}')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); db=cur.fetchall(); nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in db}; conn.close()
    h=f"<h2>{alum['nombre']}</h2><form method=post>"
    for bloque in BLOQUES_IZQ+BLOQUES_DER:
        titulo=bloque[0]; lista=bloque[1]
        h+=f"<h4 style='background:#0a2a7a;color:white;padding:6px'>{titulo}</h4><table border=1 style='width:100%'>"
        for mat in lista:
            o,e=nm.get((titulo,mat),('','')); h+=f"<tr><td>{mat}</td><td><input name='{titulo}__{mat}__o' value='{o}' style='width:60px'></td><td><input name='{titulo}__{mat}__e' value='{e}' style='width:60px'></td></tr>"
        h+="</table>"
    h+="<button style='padding:15px;background:#c00000;color:white;width:100%'>GUARDAR Y GENERAR PDF</button></form>"
    return h

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); nl=cur.fetchall(); conn.close()
    nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in nl}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    FONT_SIZE=8.5
    ROW_H=12

    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0,h-28,w,28,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6.5); c.drawString(10,h-18,"REPÚBLICA DE GUINEA ECUATORIAL - MINISTERIO DE EDUCACIÓN")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",11); c.drawString(10,h-44,f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",6.5); c.drawString(10,h-54,f"NATURAL DE {a['natural_de']}, DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']} - IPES {a['centro']} BATA")
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",13); c.drawCentredString(w/2,h-70,"HOJA ACADÉMICA")

    xf=w-62; yf=h-66
    c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor("#cbd5e1")); c.rect(xf,yf,50,58,fill=1,stroke=1)
    fp=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(fp):
        try: c.drawImage(ImageReader(fp), xf+1,yf+1,48,56,preserveAspectRatio=True)
        except: pass

    def draw_block(x, y_top, bw, titulo, materias, is_roja):
        # ESPACIOS: 22 pts para azules, 12 para rojas
        GAP = 22 if not is_roja else 12
        total_h = len(materias)*ROW_H + 14
        if is_roja:
            c.setFillColor(colors.HexColor("#fee2e2")); c.rect(x, y_top-11, bw, 11, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#b91c1c")); c.setFont("Helvetica-Bold",5.5); c.drawString(x+3, y_top-7.5, titulo)
            y = y_top-11
        else:
            c.setFillColor(colors.HexColor("#64748b")); c.rect(x, y_top-total_h-3, 14, total_h+3, fill=1, stroke=0)
            c.saveState(); c.translate(x+7, y_top-total_h/2); c.rotate(90); c.setFillColor(colors.white); c.setFont("Helvetica-Bold",7); c.drawCentredString(0,0,"CURSO"); c.restoreState()
            c.setFillColor(colors.HexColor("#1e3a8a")); c.rect(x+14, y_top-11, bw-14, 11, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6.5); c.drawString(x+18, y_top-7.5, titulo)
            y = y_top-11
        yy=y
        for mat in materias:
            bx = x+14 if not is_roja else x
            bw_materia = (bw-14 if not is_roja else bw)-44
            # celdas separadas para que no se junten
            c.setFillColor(colors.HexColor("#e0f2fe") if not is_roja else colors.HexColor("#ffea"))
            c.rect(bx, yy-ROW_H, bw_materia, ROW_H, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#93c5fd") if not is_roja else colors.HexColor("#fca5a5")); c.setLineWidth(0.35)
            c.rect(bx, yy-ROW_H, bw_materia, ROW_H, fill=0, stroke=1)
            c.setFillColor(colors.white); c.rect(bx+bw_materia, yy-ROW_H, 22, ROW_H, fill=1, stroke=1); c.rect(bx+bw_materia+22, yy-ROW_H, 22, ROW_H, fill=1, stroke=1)
            c.setFillColor(colors.black); c.setFont("Helvetica", FONT_SIZE-1.2); c.drawString(bx+2, yy-ROW_H+3.5, mat[:38])
            o,e = nm.get((titulo,mat),('',''))
            c.setFont("Helvetica-Bold", FONT_SIZE); c.drawCentredString(bx+bw_materia+11, yy-ROW_H+3.5, o); c.drawCentredString(bx+bw_materia+33, yy-ROW_H+3.5, e)
            yy-=ROW_H
        return yy - GAP

    x_left=8; bw_col=(w-24)/2
    y_left=h-85
    for tit,mats in BLOQUES_IZQ:
        y_left=draw_block(x_left, y_left, bw_col, tit, mats, False)

    x_right=w/2+4; y_right=h-85
    for bloque in BLOQUES_DER:
        tit,mats,is_roja=bloque
        y_right=draw_block(x_right, y_right, bw_col, tit, mats, is_roja)

    # QR AUTOMATICO - se genera al alumno
    qr_text=f"CEACGE-{id:04d} | {a['nombre']} {a['apellidos']} | VERIFICAR: ceacge-final.onrender.com/pdf/{id}"
    qr_buf=gen_qr(qr_text)
    c.setFillColor(colors.HexColor("#f1f5f9")); c.rect(0,0,w,36,fill=1,stroke=0)
    c.drawImage(ImageReader(qr_buf), 10, 3, width=30, height=30)
    c.setFillColor(colors.HexColor("#b91c1c")); c.setFont("Helvetica",5); c.drawString(46,18,f"QR generado automáticamente al alumno - ceacge-final.onrender.com/pdf/{id}")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",6); c.drawString(w-110,12,f"COD: CEA-{id:04d}-AA | {a['anio']}")
    c.showPage(); c.save(); buf.seek(0)
    r=make_response(buf.getvalue()); r.headers['Content-Type']='application/pdf'; r.headers['Content-Disposition']=f'inline; filename=HOJA_V12_{id}.pdf'; return r

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
