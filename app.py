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
app.secret_key='V11-8.5PT-12PX-SEPARADO'
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
        return 'Clave incorrecta <a href=/login>volver</a>'
    return '<body style="font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh"><div style="border:1px solid #ccc;padding:30px;border-radius:8px"><h2>CEACGE V11 - 8.5pt</h2><form method=post><input name=usuario value=admin style="width:100%;padding:8px"><br><br><input type=password name=password placeholder="ceacge2025" style="width:100%;padding:8px"><br><br><button style="width:100%;padding:10px;background:#0a2a7a;color:white">ENTRAR</button></form></div></body>'

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/fotos/<f>')
def fotos(f): return send_from_directory(UPLOAD_FOLDER, f)

@app.route('/')
@login_required
def index():
    conn=get_conn(); cur=conn.cursor(); cur.execute("SELECT * FROM alumnos ORDER BY id DESC"); alumnos=cur.fetchall(); conn.close()
    return render_template_string("""
    <h2>CEACGE V11 - A4 8.5pt 12px - {{alumnos|length}} alumnos</h2>
    <a href='/nuevo' style='background:#0a2a7a;color:white;padding:12px;text-decoration:none;border-radius:5px'>+ NUEVO ALUMNO</a> <a href='/logout' style='margin-left:10px'>Salir</a>
    <table border=1 cellpadding=8 style='width:100%;margin-top:15px;border-collapse:collapse'><tr><th>Foto</th><th>Nombre</th><th>PDF con QR Auto</th></tr>
    {% for a in alumnos %}<tr><td>{% if a['foto'] %}<img src='/fotos/{{a['foto']}}' width=45 style='border-radius:4px'>{% endif %}</td><td><b>{{a['nombre']}} {{a['apellidos']}}</b><br><small>{{a['natural_de']}}/{{a['distrito']}}</small></td><td><a href='/notas/{{a['id']}}'>Notas</a> | <a href='/pdf/{{a['id']}}' style='background:#c00000;color:white;padding:6px 12px;text-decoration:none;border-radius:4px'>PDF A4 QR AUTO</a></td></tr>{% endfor %}</table>
    """, alumnos=alumnos)

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
        conn.commit()
        # Obtener ID para redirigir directo a notas y generar QR
        cur.execute(adapt("SELECT id FROM alumnos ORDER BY id DESC LIMIT 1")); nid=cur.fetchone()['id']; conn.close()
        return redirect(f'/notas/{nid}')
    return """
    <h2>NUEVO ALUMNO - QR se genera automático</h2>
    <form method=post enctype=multipart/form-data style='max-width:500px;display:flex;flex-direction:column;gap:8px'>
    Nombre: <input name=nombre required><br>Apellidos: <input name=apellidos required><br>
    Natural de: <input name=natural_de value='VABE' required><br>Distrito: <input name=distrito value='KOGO' required><br>Provincia: <input name=provincia value='LITORAL' required><br>
    Centro: <input name=centro value='PADRE SANTY'><br>Año: <input name=anio value='2023-2024'><br>
    Foto carnet: <input type=file name=foto accept='image/*'><br>
    <button style='padding:14px;background:#0a2a7a;color:white;border:none;border-radius:5px'>GUARDAR - IR A NOTAS (QR AUTO)</button>
    </form><br><a href='/'>Volver</a>"""

# MATERIAS - ORDEN EXACTO DE TU FOTO
BLOQUES_IZQ = [
 ("1 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
 ("4 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Biología y Geología","Tecnología","E. Plástica y Artística I","Física y Química","Religión","Inglés","Francés","E. Física"]),
 ("2 ESBA", ["Lengua Española y Lit","Matemáticas","Geografía Gral. y de EG","Ciencias Naturales I","E. Plástica y Visual I","Religión","Francés","Inglés","E. Física"]),
]
BLOQUES_DER = [
 ("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD", ["Lengua Española y Lit","Matemáticas","Biología","Física y Química","Dibujo Técnico I","Religión"]),
 ("RAMA DE CIENCIAS SOCIALES Y HUMANIDADES", ["Latín","Literatura","Geografía de la España Actual","Mat. aplicadas a CC.SS."]),
 ("RAMA DE TECNOLOGÍA", ["Tecnología Industrial I","Matemáticas I","Dibujo técnico I","Física"]),
 ("RAMA DE CIENCIAS DE LA NATURALEZA Y SALUD Y TECNOLOGÍA", ["Literatura","Historia del Mundo Actual","Historia de la Filosofía","Ciencias de la Tierra y Medio Ambiente","Tecnología de la Información","Biología","Física","Química"]),
]

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
@login_required
def notas_alumno(alumno_id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(alumno_id,)); alum=cur.fetchone()
    if request.method=='POST':
        cur.execute(adapt("DELETE FROM notas WHERE alumno_id=?"),(alumno_id,))
        for titulo, lista in BLOQUES_IZQ+BLOQUES_DER:
            for mat in lista:
                o=request.form.get(f"{titulo}__{mat}__o",''); e=request.form.get(f"{titulo}__{mat}__e",'')
                if o or e:
                    cur.execute(adapt("INSERT INTO notas (alumno_id,curso,asignatura,ord,extra) VALUES (?,?,?,?,?)"),(alumno_id,titulo,mat,o,e))
        conn.commit(); conn.close(); return redirect(f'/pdf/{alumno_id}')
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(alumno_id,)); notas_db=cur.fetchall(); nm={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in notas_db}; conn.close()
    html=f"<h2>Notas de {alum['nombre']} {alum['apellidos']} - QR se generará en el PDF automáticamente</h2><form method=post>"
    for titulo, lista in BLOQUES_IZQ+BLOQUES_DER:
        html+=f"<h4 style='background:#c00000;color:white;padding:6px;margin-top:15px'>{titulo}</h4><table border=1 cellpadding=4 style='width:100%;border-collapse:collapse'>"
        for mat in lista:
            o,e=nm.get((titulo,mat),('','')); html+=f"<tr><td style='width:70%'>{mat}</td><td><input name='{titulo}__{mat}__o' value='{o}' style='width:60px'></td><td><input name='{titulo}__{mat}__e' value='{e}' style='width:60px'></td></tr>"
        html+="</table>"
    html+="<br><button style='padding:15px;background:#c00000;color:white;width:100%;font-size:16px;border:none;border-radius:5px'>GUARDAR Y GENERAR PDF A4 CON QR AUTOMÁTICO</button></form><br><a href='/'>Volver</a>"
    return html

@app.route('/pdf/<int:id>')
@login_required
def pdf_hoja(id):
    conn=get_conn(); cur=conn.cursor(); cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"),(id,)); a=cur.fetchone()
    cur.execute(adapt("SELECT * FROM notas WHERE alumno_id=?"),(id,)); notas_l=cur.fetchall(); conn.close()
    notas_map={(n['curso'],n['asignatura']):(n['ord'],n['extra']) for n in notas_l}
    buf=io.BytesIO(); c=canvas.Canvas(buf, pagesize=A4); w,h=A4

    # PARAMETROS QUE PEDISTE
    FONT_SIZE = 8.5
    ROW_H = 12  # 12px como pediste

    # ENCABEZADO
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0, h-28, w, 28, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 6.5); c.drawString(10, h-18, "REPÚBLICA DE GUINEA ECUATORIAL - MINISTERIO DE EDUCACIÓN, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 11.5); c.drawString(10, h-44, f"{a['nombre']} {a['apellidos']}".upper())
    c.setFont("Helvetica", 7); c.drawString(10, h-54, f"NATURAL DE {a['natural_de']}, DISTRITO DE {a['distrito']}, PROVINCIA DE {a['provincia']} - IPES {a['centro']} - BATA")
    c.setFillColor(colors.HexColor("#c00000")); c.setFont("Helvetica-Bold", 13); c.drawCentredString(w/2, h-70, "HOJA ACADÉMICA")
    c.setFillColor(colors.HexColor("#0a2a7a")); c.rect(0, h-73, w, 1.2, fill=1, stroke=0)

    # FOTO
    xf = w-62; yf = h-66
    c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor("#cbd5e1")); c.rect(xf, yf, 50, 58, fill=1, stroke=1)
    foto_path=os.path.join(UPLOAD_FOLDER, a['foto'] or '')
    if a['foto'] and os.path.exists(foto_path):
        try: c.drawImage(ImageReader(foto_path), xf+1, yf+1, width=48, height=56, preserveAspectRatio=True, mask='auto')
        except: 
            c.setFillColor(colors.black); c.setFont("Helvetica",6); c.drawCentredString(xf+25, yf+26, "FOTO")
    else:
        c.setFillColor(colors.black); c.setFont("Helvetica",6); c.drawCentredString(xf+25, yf+26, "FOTO")

    def draw_curso_block(x, y_top, bw, titulo, materias, is_rama):
        # SEPARACION ENTRE CUADROS - NO SE JUNTAN
        GAP = 10
        # Altura total
        total_h = len(materias)*ROW_H + 14
        # Fondo del bloque con separacion
        # Titulo
        if is_rama:
            # RAMA - fondo rosado claro + texto rojo
            c.setFillColor(colors.HexColor("#fee2e2")); c.rect(x, y_top-11, bw, 11, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#b91c1c")); c.setFont("Helvetica-Bold", 6); c.drawString(x+3, y_top-7.5, titulo)
            y = y_top - 11
        else:
            # ESBA - barra lateral CURSO + cabecera azul
            c.setFillColor(colors.HexColor("#64748b")); c.rect(x, y_top-total_h-3, 14, total_h+3, fill=1, stroke=0)
            c.saveState(); c.translate(x+7, y_top-total_h/2); c.rotate(90); c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 7); c.drawCentredString(0,0,"CURSO"); c.restoreState()
            c.setFillColor(colors.HexColor("#1e3a8a")); c.rect(x+14, y_top-11, bw-14, 11, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 6.5); c.drawString(x+18, y_top-7.5, titulo)
            y = y_top - 11

        yy = y
        for mat in materias:
            # celdas con separacion blanca de 1px para que no se junten
            bx = x+14 if not is_rama else x
            c.setFillColor(colors.HexColor("#e0f2fe")); c.rect(bx, yy-ROW_H, (bw-14 if not is_rama else bw)-44, ROW_H, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#93c5fd")); c.setLineWidth(0.4)
            c.rect(bx, yy-ROW_H, (bw-14 if not is_rama else bw)-44, ROW_H, fill=0, stroke=1)
            c.setFillColor(colors.white)
            c.rect(bx+(bw-14 if not is_rama else bw)-44, yy-ROW_H, 22, ROW_H, fill=1, stroke=1)
            c.rect(bx+(bw-14 if not is_rama else bw)-22, yy-ROW_H, 22, ROW_H, fill=1, stroke=1)
            # Texto materia 8.5pt
            c.setFillColor(colors.black); c.setFont("Helvetica", FONT_SIZE-1.5); c.drawString(bx+2, yy-ROW_H+3.5, mat[:38])
            o,e = notas_map.get((titulo,mat),('',''))
            c.setFont("Helvetica-Bold", FONT_SIZE); c.drawCentredString(bx+(bw-14 if not is_rama else bw)-33, yy-ROW_H+3.5, o)
            c.drawCentredString(bx+(bw-14 if not is_rama else bw)-11, yy-ROW_H+3.5, e)
            yy -= ROW_H
        return yy - GAP

    # DIBUJAR - 2 COLUMNAS CON GAP PARA NO JUNTARSE
    x_left = 8; bw_col = (w-24)/2
    y_left = h - 85
    for tit, mats in BLOQUES_IZQ:
        y_left = draw_curso_block(x_left, y_left, bw_col, tit, mats, False)

    x_right = w/2 + 4; y_right = h - 85
    for tit, mats in BLOQUES_DER:
        y_right = draw_curso_block(x_right, y_right, bw_col, tit, mats, True)

    # PIE SIN ESPACIO GRANDE - QR AUTOMATICO
    # QR se genera con datos del alumno automaticamente
    qr_text = f"CEACGE-{id:04d} | {a['nombre']} {a['apellidos']} | {a['centro']} | VERIFICAR: ceacge-final.onrender.com/pdf/{id}"
    qr_buf = gen_qr(qr_text)
    # Fondo pie pequeño para no dejar hueco grande
    c.setFillColor(colors.HexColor("#f1f5f9")); c.rect(0, 0, w, 38, fill=1, stroke=0)
    c.drawImage(ImageReader(qr_buf), 10, 4, width=30, height=30)
    c.setFillColor(colors.HexColor("#b91c1c")); c.setFont("Helvetica", 5)
    c.drawString(46, 22, "QR generado automáticamente al crear el alumno. Verificación digital: ceacge-final.onrender.com/pdf/"+str(id))
    c.drawString(46, 15, "La falsificación de este documento constituye delito. Registrado en Base de Datos Nacional de Guinea Ecuatorial.")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 6); c.drawString(w-110, 14, f"COD: CEA-{id:04d}-AA | {a['anio']}")

    c.showPage(); c.save(); buf.seek(0)
    resp=make_response(buf.getvalue()); resp.headers['Content-Type']='application/pdf'; resp.headers['Content-Disposition']=f'inline; filename=HOJA_ACADEMICA_{a["nombre"]}_{id}_QR_AUTO.pdf'; return resp

try: init_db()
except Exception as e: print(e)
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
