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
app.secret_key='V8-LETRA-GRANDE'
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
def gen_qr(t):
    qr=qrcode.QRCode(box_size=4, border=1); qr.add_data(t); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white").convert('RGB')
    b=io.BytesIO(); img.save(b, format='PNG'); b.seek(0); return b

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['usuario']; p=request.form['password']
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"),(u,)); user=cur.fetchone(); conn.close()
        if user and check_password_hash(user['password'], p):
            session['usuario']=u; return redirect('/')
        return 'Clave mal'
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh"><div style="border:1px solid #ccc;padding:30px"><h2>CEACGE V8</h2><form method=post><input name=usuario value=admin><br><br><input type=password name=password><br><br><button>ENTRAR</button></form></div></body>'
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)
@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); a=cur.fetchall(); conn.close()
    return render_template_string("<h2>V8 - {{a|length}} alumnos</h2><a href='/nuevo'>+ NUEVO</a> | <a href='/logout'>Salir</a><table border=1 cellpadding=6 style='width:100%'><tr><th>Foto</th><th>Nombre</th><th>PDF</th></tr>{% for x in a %}<tr><td>{% if x['foto'] %}<img src='/fotos/{{x['foto']}}' width=40>{% endif %}</td><td>{{x['nombre']}} {{x['apellidos']}}</td><td><a href='/notas/{{x['id']}}'>Notas</a> | <a href='/pdf/{{x['id']}}' style='background:#c00000;color:white;padding:5px'>PDF GRANDE</a></td></tr>{% endfor %}</table>", a=a)
@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        n=request.form['nombre']; ap=request.form['apellidos']; nat=request.form['natural_de']; dis=request.form['distrito']; prov=request.form['provincia']; cen=request.form['centro'] or 'PADRE SANTY'; an=request.form['anio']
        f=request.files.get('foto'); fn=''
        if f and f.filename:
            fn=secure_filename(f.filename); f.save(os.path.join(UPLOAD_FOLDER, fn))
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio) VALUES (?,?,?,?,?,?,?,?)"),(n,ap,nat,dis,prov,cen,fn,an)); conn.commit(); conn.close(); return redirect('/')
    return "<form method=post enctype=multipart/form-data>Nombre<input name=nombre required><br>Apellidos<input name=apellidos><br>Natural<input name=natural_de value='VABE'><br>Distrito<input name=distrito value='KOGO'><br>Provincia<input name=provincia value='LITORAL'><br>Centro<input name=centro value='PADRE SANTY'><br>Año<input name=anio value='2023-2024'><br>Foto<input type=file name=foto><br><button>GUARDAR</button></form>"

BLOQUES_IZQ=[("1 ESBA",["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),("4 ESBA",["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"]),("2 ESBA",["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"])]
BLOQUES_DER=[("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD",["Lengua Española y Lit","Matemáticas","Biología","Física y Química","Dibujo Técnico I","Religión"]),("RAMA DE CIENCIAS SOCIALES Y HUMANIDADES",["Latín","Literatura","Geografía de la España Actual","Mat. aplicadas a CC.SS."]),("RAMA DE TECNOLOGÍA",["Tecnología Industrial I","Matemáticas I","Dibujo técnico I","Física"]),("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD Y TECNOLOGÍA",["Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencias de la Tierra y Medio Ambiente","Tecnología de la Información","Biología","Física","Química"])]

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
    html=f"<h2>{alum['nombre']}</h2><form method=post>"
    for titulo, lista in BLOQUES_IZQ+BLOQUES_DER:
        html+=f"<h4 style='background:#0a2a7a;color:white;padding:6px'>{titulo}</h4><table border=1 style='width:100%'>"
        for mat in lista:
            o,e=nm.get((titulo,mat),('','')); html+=f"<tr><td>{mat}</td><td><input name='{titulo}__{mat}__o' value='{o}' style='width:60px'></td><td><input name='{titulo}__{mat}__e' value='{e}' style='width:60px'></td></tr>"
        html+="</table>"
    html+="<button style='padding:15px;background:#c00000;color:white;width:100%'>GUARDAR Y GENERAR PDF</button></form>"
    return html

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); notas_l=cur.fetchall(); conn.close()
    notas_map={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in notas_l}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4

    # HEADER MODERNO GRANDE
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0,h-30,w,30,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6); c.drawString(10,h-18,"REPÚBLICA DE GUINEA ECUATORIAL - MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",12); c.drawString(10,h-45,f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",7); c.drawString(10,h-55,f"NATURAL DE {a['natural_de']}, DEL DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']} - IPES {a['centro']} - BATA")
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",14); c.drawCentredString(w/2,h-72,"HOJA ACADÉMICA")
    # FOTO GRANDE
    xf=w-65; yf=h-70
    c.setFillColor(colors.white); c.rect(xf,yf,50,60,fill=1,stroke=1); c.setFont("Helvetica",6); c.setFillColor(colors.black); c.drawCentredString(xf+25,yf+28,"FOTO")
    foto_path=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(foto_path):
        try: c.drawImage(ImageReader(foto_path), xf, yf, width=50, height=60, preserveAspectRatio=True)
        except: pass

    def draw_block(x,y,bw,titulo,materias,is_rama):
        # titulo
        if is_rama:
            c.setFillColor(colors.HexColor("#b91c1c")); c.setFont("Helvetica-Bold",6); c.drawString(x, y+2, titulo)
            y-=2
        else:
            # barra CURSO gris
            total_h=len(materias)*13+12
            c.setFillColor(colors.HexColor("#94a3b8")); c.rect(x, y-total_h, 16, total_h, fill=1, stroke=0)
            c.saveState(); c.translate(x+8, y-total_h/2); c.rotate(90); c.setFillColor(colors.white); c.setFont("Helvetica-Bold",8); c.drawCentredString(0,0,"CURSO"); c.restoreState()
            c.setFillColor(colors.HexColor("#1e3a8a")); c.rect(x+16, y, bw-16, 12, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",7); c.drawString(x+20, y+3, titulo)
        yy=y-12 if not is_rama else y-6
        row_h=11
        for mat in materias:
            # fondo
            c.setFillColor(colors.HexColor("#e0f2fe")); c.rect(x+16 if not is_rama else x, yy, (bw-16 if not is_rama else bw)-46, row_h, fill=1, stroke=1)
            c.setFillColor(colors.white); c.rect(x+ (bw-30) if not is_rama else x+bw-46, yy, 23, row_h, fill=1, stroke=1)
            c.rect(x+ bw-7 if not is_rama else x+bw-23, yy, 23, row_h, fill=1, stroke=1) if not is_rama else c.rect(x+bw-23, yy, 23, row_h, fill=1, stroke=1)
            # texto materia grande
            c.setFillColor(colors.black); c.setFont("Helvetica",7); c.drawString(x+18 if not is_rama else x+2, yy+3, mat)
            o,e=notas_map.get((titulo,mat),('',''))
            c.setFont("Helvetica-Bold",7.5); c.drawCentredString(x+ bw-18 if not is_rama else x+bw-34, yy+3, o); c.drawCentredString(x+ bw+5 if not is_rama else x+bw-11, yy+3, e) if not is_rama else c.drawCentredString(x+bw-11, yy+3, e)
            yy-=row_h
        return yy-12

    x1=10; bw1=w/2-12
    y_cur=h-85
    for tit,mats in BLOQUES_IZQ:
        y_cur=draw_block(x1, y_cur, bw1, tit, mats, False)

    x2=w/2+2; bw2=w/2-12
    y_cur2=h-85
    for tit,mats in BLOQUES_DER:
        y_cur2=draw_block(x2, y_cur2, bw2, tit, mats, True)
        y_cur2-=2

    # QR GRANDE
    qr_buf=gen_qr(f"CEACGE-{id} {a['nombre']}")
    c.drawImage(ImageReader(qr_buf), 12, 12, width=45, height=45)
    c.setFillColor(colors.HexColor("#b91c1c")); c.setFont("Helvetica",5)
    c.drawString(62,32,"La falsificación de este documento constituye delito. Registrado en Base de Datos Nacional de Guinea Ecuatorial.")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",6); c.drawString(w-110,12,f"COD: CEA-{id:04d}-AA")
    c.showPage(); c.save(); buf.seek(0)
    resp=make_response(buf.getvalue()); resp.headers['Content-Type']='application/pdf'; resp.headers['Content-Disposition']=f'inline; filename=HOJA_{id}.pdf'; return resp

try: init_db()
except: pass
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
