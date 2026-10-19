# COPIA EL V8 QUE YA TE FUNCIONA Y SOLO CAMBIA ESTA FUNCIÓN pdf_hoja
# Te dejo el archivo completo V10 listo:

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
app.secret_key='V10-SIN-HUECO'
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
    return '<h2>CEACGE V10</h2><form method=post><input name=usuario value=admin><br><input type=password name=password><br><button>ENTRAR</button></form>'
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)
@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); a=cur.fetchall(); conn.close()
    return render_template_string("<h2>V10 SIN HUECO - {{a|length}}</h2><a href='/nuevo'>+ NUEVO</a><table border=1><tr><th>Foto</th><th>Nombre</th><th>PDF</th></tr>{% for x in a %}<tr><td><img src='/fotos/{{x['foto']}}' width=30></td><td>{{x['nombre']}}</td><td><a href='/pdf/{{x['id']}}'>PDF FINAL</a></td></tr>{% endfor %}</table>", a=a)
@app.route('/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    if request.method=='POST':
        n=request.form['nombre']; ap=request.form['apellidos']; nat=request.form['natural_de']; dis=request.form['distrito']; prov=request.form['provincia']; cen=request.form['centro']; an=request.form['anio']
        f=request.files.get('foto'); fn=''
        if f and f.filename:
            fn=secure_filename(f.filename); f.save(os.path.join(UPLOAD_FOLDER, fn))
        conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,natural_de,distrito,provincia,centro,foto,anio) VALUES (?,?,?,?,?,?,?,?)"),(n,ap,nat,dis,prov,cen,fn,an)); conn.commit(); conn.close(); return redirect('/')
    return "<form method=post enctype=multipart/form-data>Nombre<input name=nombre><br>Apellidos<input name=apellidos><br>Natural<input name=natural_de><br>Distrito<input name=distrito><br>Provincia<input name=provincia><br>Centro<input name=centro value='PADRE SANTY'><br>Año<input name=anio><br>Foto<input type=file name=foto><br><button>GUARDAR</button></form>"

BLOQUES_IZQ=[("1 ESBA",["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),("4 ESBA",["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"]),("2 ESBA",["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"])]
BLOQUES_DER=[("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD",["Lengua Española y Lit","Matemáticas","Biología","Física y Química","Dibujo Técnico I","Religión"]),("RAMA DE CIENCIAS SOCIALES Y HUMANIDADES",["Latín","Literatura","Geografía de la España Actual","Mat. aplicadas a CC.SS."]),("RAMA DE TECNOLOGÍA",["Tecnología Industrial I","Matemáticas I","Dibujo técnico I","Física"]),("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD Y TECNOLOGÍA",["Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencias de la Tierra y Medio Ambiente","Tecnología de la Información","Biología","Física","Química"])]

@app.route('/notas/<int:id>', methods=['GET','POST'])
@login_required
def notas(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(id,))
        for t,mats in BLOQUES_IZQ+BLOQUES_DER:
            for mat in mats:
                o=request.form.get(f"{t}__{mat}__o",''); e=request.form.get(f"{t}__{mat}__e",'')
                if o or e: cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(id,t,mat,o,e))
        conn.commit(); conn.close(); return redirect(f'/pdf/{id}')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); db=cur.fetchall(); nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in db}; conn.close()
    h=f"<form method=post>"
    for t,mats in BLOQUES_IZQ+BLOQUES_DER:
        h+=f"<h4>{t}</h4><table border=1>"
        for mat in mats:
            o,e=nm.get((t,mat),('','')); h+=f"<tr><td>{mat}</td><td><input name='{t}__{mat}__o' value='{o}'></td><td><input name='{t}__{mat}__e' value='{e}'></td></tr>"
        h+="</table>"
    h+="<button>GUARDAR</button></form>"
    return h

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); nl=cur.fetchall(); conn.close()
    nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in nl}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0,h-28,w,28,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6); c.drawString(8,h-17,"REPÚBLICA DE GUINEA ECUATORIAL - MINISTERIO DE EDUCACIÓN")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",11); c.drawString(8,h-42,f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica",6.5); c.drawString(8,h-52,f"NATURAL DE {a['natural_de']}, DISTRITO {a['distrito']}, PROVINCIA {a['provincia']} - IPES {a['centro']} BATA")
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold",13); c.drawCentredString(w/2,h-68,"HOJA ACADÉMICA")
    xf=w-60; yf=h-68
    c.setFillColor(colors.white); c.rect(xf,yf,48,56,fill=1,stroke=1)
    fp=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(fp):
        try: c.drawImage(ImageReader(fp), xf, yf, 48, 56, preserveAspectRatio=True)
        except: pass
    def draw_block(x,y,bw,titulo,mats,is_rama):
        if is_rama:
            c.setFillColor(colors.HexColor("#fee2e2")); c.rect(x,y, bw, 11, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#b91c1c")); c.setFont("Helvetica-Bold",5.5); c.drawString(x+2,y+3,titulo[:58])
            y-=2
        else:
            th=len(mats)*12.5+12
            c.setFillColor(colors.HexColor("#64748b")); c.rect(x, y-th, 14, th, fill=1, stroke=0)
            c.saveState(); c.translate(x+7, y-th/2); c.rotate(90); c.setFillColor(colors.white); c.setFont("Helvetica-Bold",7); c.drawCentredString(0,0,"CURSO"); c.restoreState()
            c.setFillColor(colors.HexColor("#1e3a8a")); c.rect(x+14, y, bw-14, 11, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",6.5); c.drawString(x+18,y+3,titulo)
        yy=y-11
        for mat in mats:
            c.setFillColor(colors.HexColor("#e0f2fe")); c.rect(x+14 if not is_rama else x, yy, (bw-14 if not is_rama else bw)-42, 12.5, fill=1, stroke=1)
            c.setFillColor(colors.white); c.rect(x+bw-28 if not is_rama else x+bw-42, yy, 20, 12.5, fill=1, stroke=1); c.rect(x+bw-8 if not is_rama else x+bw-22, yy, 20, 12.5, fill=1, stroke=1)
            c.setFillColor(colors.black); c.setFont("Helvetica",6.5); c.drawString(x+16 if not is_rama else x+2, yy+4, mat[:36])
            o,e=nm.get((titulo,mat),('',''))
            c.setFont("Helvetica-Bold",7); c.drawCentredString(x+bw-18 if not is_rama else x+bw-32, yy+4, o); c.drawCentredString(x+bw+2 if not is_rama else x+bw-12, yy+4, e) if not is_rama else c.drawCentredString(x+bw-12, yy+4, e)
            yy-=12.5
        return yy-8
    x1=6; bw1=w/2-8
    y_cur=h-82
    for t,mats in BLOQUES_IZQ:
        y_cur=draw_block(x1, y_cur, bw1, t, mats, False)
    x2=w/2+2; bw2=w/2-8
    y_cur2=h-82
    for t,mats in BLOQUES_DER:
        y_cur2=draw_block(x2, y_cur2, bw2, t, mats, True)
    # PIE QUE TAPA EL BLANCO
    c.setFillColor(colors.HexColor("#1e293b")); c.rect(0,0,w,52,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#cbd5e1")); c.rect(0,0,w,42,fill=1,stroke=0)
    qr=gen_qr(f"CEACGE-{id}")
    c.drawImage(ImageReader(qr), 8, 4, 34, 34)
    c.setFillColor(colors.black); c.setFont("Helvetica",5); c.drawString(48,28,"Documento verificado digitalmente. La falsificación constituye delito según Código Penal de Guinea Ecuatorial.")
    c.drawString(48,20,"Base de Datos Nacional - CEACGE - ceacge-final.onrender.com/pdf/"+str(id))
    c.setFont("Helvetica-Bold",6); c.drawString(w-100,14,f"COD: CEA-{id:04d}-AA | {a['anio']}")
    c.showPage(); c.save(); buf.seek(0)
    r=make_response(buf.getvalue()); r.headers['Content-Type']='application/pdf'; r.headers['Content-Disposition']=f'inline; filename=HOJA_{id}.pdf'; return r
try: init_db()
except: pass
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
