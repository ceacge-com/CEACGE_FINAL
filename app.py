# CEACGE V19 FUSIONADA - V18 ORIGINAL + BUSCAR CENTRAL
# Mantiene: PDF limpio sin linea, Solo Director, Texto seguridad separado, VER bonito con foto grande y QR
# Nuevo: /buscar - Centros ven todo CEACGE pero SOLO VER, Admin edita todo

import os
import base64
import qrcode
from io import BytesIO
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, make_response, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ceacge-v19-final-key-2026")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///ceacge_v19.db")
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- MODELOS ----------------
class Ipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    director = db.Column(db.String(200))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='centro')
    ipe_id = db.Column(db.Integer, db.ForeignKey('ipe.id'), nullable=True)
    ipe = db.relationship('Ipe')

class Alumno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    fecha_nacimiento = db.Column(db.String(30))
    lugar_nacimiento = db.Column(db.String(100))
    especialidad = db.Column(db.String(100))
    matricula = db.Column(db.String(50), unique=True)
    telefono = db.Column(db.String(50))
    foto = db.Column(db.Text)
    ipe_id = db.Column(db.Integer, db.ForeignKey('ipe.id'))
    ipe = db.relationship('Ipe')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    # Notas y otros campos V18
    notas = db.Column(db.Text)

with app.app_context():
    db.create_all()
    if not Ipe.query.first():
        ipe = Ipe(codigo='CEACGE-CENTRAL', nombre='CEACGE Central - Bata', director='Director General CEACGE')
        db.session.add(ipe)
        db.session.commit()
    if not User.query.filter_by(username='admin').first():
        ipe = Ipe.query.first()
        admin = User(username='admin', password=generate_password_hash('admin123'), role='admin', ipe_id=ipe.id)
        db.session.add(admin)
        db.session.commit()

# ---------------- HELPERS ----------------
def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return dec

def get_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def can_edit(user, alumno):
    if not user: return False
    if user.role == 'admin': return True
    return user.ipe_id == alumno.ipe_id

BASE = """
<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>CEACGE V19</title>
<style>
body{font-family:Arial;background:#f4f6f9;margin:0}
.header{background:#0b2e59;color:#fff;padding:15px;display:flex;justify-content:space-between}
.btn{padding:8px 14px;border-radius:6px;text-decoration:none;color:#fff;border:none;cursor:pointer;margin:2px;display:inline-block}
.btn-blue{background:#0b2e59}.btn-green{background:#198754}.btn-orange{background:#fd7e14}.btn-red{background:#dc3545}
.card{background:#fff;padding:16px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08);margin:12px 0}
table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #e9ecef;text-align:left}
.badge{padding:5px 10px;border-radius:20px;font-size:11px;font-weight:bold}
.badge-warn{background:#fff3cd;color:#664d03;border:1px solid #ffecb5}
input,select{width:100%;padding:11px;margin:6px 0;border:1px solid #ccc;border-radius:8px}
</style></head><body>
<div class=header><b>CEACGE V19 - LIVE ceacge-final.onrender.com</b><div>{% if user %}{{user.username}} ({{user.role}}) {% if user.ipe %}- {{user.ipe.codigo}}{% endif %} | <a href=/logout style=color:#fff>Salir</a>{% endif %}</div></div>
<div style=padding:15px>{% with msgs=get_flashed_messages() %}{% if msgs %}{% for m in msgs %}<div class=card style=background:#fff3cd;border-left:5px solid #ffc107>{{m}}</div>{% endfor %}{% endif %}{% endwith %}{{content|safe}}</div></body></html>
"""

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id']=u.id
            return redirect(url_for('index'))
        flash('Usuario o clave incorrecta')
    html = """<div class=card style=max-width:420px;margin:50px auto><h3>CEACGE - Entrar</h3><form method=post><input name=username placeholder=Usuario required><input name=password type=password placeholder=Contraseña required><button class="btn btn-blue" style=width:100%>Entrar</button></form><p style=font-size:12px;color:#666>Admin: admin / admin123</p></div>"""
    return render_template_string(BASE, content=html, user=None, get_flashed_messages=lambda: [])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- INDEX ----------------
@app.route('/')
@login_required
def index():
    u = get_user()
    total = Alumno.query.count()
    mis = total if u.role=='admin' else Alumno.query.filter_by(ipe_id=u.ipe_id).count()
    content = f"""
    <div style=display:grid;grid-template-columns:1fr 1fr;gap:12px>
      <div class=card><h4>Total Central CEACGE</h4><h1>{total}</h1><small>Toda la base central</small></div>
      <div class=card><h4>Mis Alumnos</h4><h1>{mis}</h1><small>{u.ipe.codigo if u.ipe else 'ADMIN'}</small></div>
    </div>
    <div class=card>
      <a class="btn btn-blue" href=/alumnos>📋 Mis Alumnos (Editar)</a>
      <a class="btn btn-orange" href=/buscar>🔍 BUSCAR CENTRAL (Solo ver alumnos de todo CEACGE)</a>
      <a class="btn btn-green" href=/alumnos/nuevo>➕ Nuevo Alumno</a>
      {'<a class="btn btn-blue" href=/ipes>🏫 Centros</a>' if u.role=='admin' else ''}
    </div>
    """
    return render_template_string(BASE, content=content, user=u, get_flashed_messages=lambda: [])

# ---------------- MIS ALUMNOS ----------------
@app.route('/alumnos')
@login_required
def alumnos():
    u = get_user()
    q = request.args.get('q','')
    query = Alumno.query if u.role=='admin' else Alumno.query.filter_by(ipe_id=u.ipe_id)
    if q:
        query = query.filter((Alumno.nombre.contains(q)) | (Alumno.apellidos.contains(q)) | (Alumno.matricula.contains(q)))
    lista = query.order_by(Alumno.id.desc()).limit(200).all()
    rows = "".join([f"<tr><td>{a.matricula}</td><td>{a.nombre} {a.apellidos}</td><td>{a.ipe.codigo if a.ipe else ''}</td><td>{a.especialidad or ''}</td><td><a class='btn btn-blue' href=/alumnos/{a.id}>VER</a> <a class='btn btn-green' href=/alumnos/{a.id}/pdf>PDF</a> <a class='btn btn-orange' href=/alumnos/{a.id}/editar>Editar</a></td></tr>" for a in lista])
    content = f"""<div class=card><h3>Mis Alumnos</h3><form><input name=q value="{q}" placeholder=Buscar...><button class="btn btn-blue">Buscar</button></form><table><tr><th>Matricula</th><th>Nombre</th><th>Centro</th><th>Especialidad</th><th>Acciones</th></tr>{rows}</table></div>"""
    return render_template_string(BASE, content=content, user=u, get_flashed_messages=lambda: [])

# ---------------- BUSCAR CENTRAL V19 - SOLO LECTURA PARA CENTROS ----------------
@app.route('/buscar')
@login_required
def buscar():
    u = get_user()
    q = request.args.get('q','').strip()
    query = Alumno.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Alumno.nombre.ilike(like), Alumno.apellidos.ilike(like), Alumno.matricula.ilike(like), Alumno.telefono.ilike(like), Alumno.especialidad.ilike(like)))
    lista = query.order_by(Alumno.id.desc()).limit(200).all()
    rows=""
    for a in lista:
        es_mio = can_edit(u, a)
        if es_mio:
            acciones = f"<a class='btn btn-blue' href=/alumnos/{a.id}>VER</a> <a class='btn btn-green' href=/alumnos/{a.id}/pdf>PDF</a> <a class='btn btn-orange' href=/alumnos/{a.id}/editar>Editar</a>"
            badge=""
        else:
            acciones = f"<a class='btn btn-blue' href=/alumnos/{a.id}>VER</a> <a class='btn btn-green' href=/alumnos/{a.id}/pdf>PDF</a> <span class=badge badge-warn>OTRO CENTRO - SOLO VER</span>"
            badge = f"<br><span class=badge badge-warn>{a.ipe.codigo if a.ipe else 'CENTRAL'}</span>"
        rows+=f"<tr><td>{a.matricula}{badge}</td><td>{a.nombre} {a.apellidos}</td><td>{a.ipe.codigo if a.ipe else ''}<br><small>{a.ipe.nombre if a.ipe else ''}</small></td><td>{a.especialidad or ''}</td><td>{acciones}</td></tr>"
    content=f"""
    <div class=card>
      <h3>🔍 BUSCAR CENTRAL - Base de Datos Central CEACGE</h3>
      <p style=font-size:13px;color:#555>Norma V19: Los centros <b>pueden VER todos los alumnos de CEACGE</b>, pero solo pueden <b>MODIFICAR los de su propio centro</b>. Solo el admin puede modificar todo.</p>
      <form method=get style=display:flex;gap:8px><input name=q value="{q}" placeholder="Buscar nombre, apellidos, matrícula, teléfono, especialidad..." autofocus style=flex:1><button class="btn btn-blue">Buscar en Central</button><a class="btn btn-green" href=/buscar>Limpiar</a></form>
      <div style=margin-top:12px><table><tr><th>Matricula</th><th>Nombre Completo</th><th>Centro Origen</th><th>Especialidad</th><th>Acciones</th></tr>{rows if rows else '<tr><td colspan=5>No hay resultados - escribe para buscar</td></tr>'}</table></div>
    </div>
    """
    return render_template_string(BASE, content=content, user=u, get_flashed_messages=lambda: [])

# ---------------- VER ----------------
@app.route('/alumnos/<int:id>')
@login_required
def ver_alumno(id):
    u = get_user()
    a = Alumno.query.get_or_404(id)
    es_mio = can_edit(u, a)
    url_ver = request.host_url.rstrip('/') + f'/alumnos/{a.id}'
    qr = qrcode.make(url_ver)
    buf = BytesIO(); qr.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    foto_html = f"<img src='{a.foto}' style=width:200px;height:240px;object-fit:cover;border-radius:12px;border:3px solid #0b2e59;box-shadow:0 4px 12px rgba(0,0,0,.2)>" if a.foto else "<div style=width:200px;height:240px;background:#dee2e6;display:flex;align-items:center;justify-content:center;border-radius:12px>Sin Foto</div>"
    aviso = "" if es_mio else f"<div class=card style=background:#fff3cd;border-left:5px solid #ffc107><b>⚠️ SOLO LECTURA:</b> Este alumno pertenece a {a.ipe.codigo if a.ipe else 'otro centro'}. No puedes editarlo. Solo VER y PDF.</div>"
    content=f"""{aviso}<div class=card><div style=display:flex;gap:24px;flex-wrap:wrap><div style=text-align:center>{foto_html}<br><br><img src='data:image/png;base64,{qr_b64}' style=width:160px;border:1px solid #ddd;padding:6px;border-radius:8px><br><small style=color:#666>QR Verificación<br>{url_ver}</small></div><div style=flex:1;min-width:260px><h2 style=margin-top:0>{a.nombre} {a.apellidos}</h2><p><b>Matrícula:</b> {a.matricula}<br><b>Centro:</b> {a.ipe.nombre if a.ipe else ''} ({a.ipe.codigo if a.ipe else ''})<br><b>Especialidad:</b> {a.especialidad or '-'}<br><b>Nacimiento:</b> {a.fecha_nacimiento or ''} - {a.lugar_nacimiento or ''}<br><b>Teléfono:</b> {a.telefono or ''}<br><b>Registro:</b> {a.fecha_registro.strftime('%d/%m/%Y') if a.fecha_registro else ''}</p><div style=margin-top:16px><a class="btn btn-green" href=/alumnos/{a.id}/pdf>📄 PDF Oficial</a>{'<a class="btn btn-orange" href=/alumnos/'+str(a.id)+'/editar>✏️ Editar</a>' if es_mio else ''}<a class="btn btn-blue" href=/buscar>🔙 Buscar Central</a><a class="btn btn-blue" href=/alumnos>📋 Mis Alumnos</a></div></div></div></div>"""
    return render_template_string(BASE, content=content, user=u, get_flashed_messages=lambda: [])

# ---------------- EDITAR CON PROTECCION ----------------
@app.route('/alumnos/<int:id>/editar', methods=['GET','POST'])
@login_required
def editar_alumno(id):
    u = get_user()
    a = Alumno.query.get_or_404(id)
    if not can_edit(u, a):
        flash(f'⛔ No autorizado: {a.nombre} {a.apellidos} pertenece a {a.ipe.codigo if a.ipe else "otro centro"}. Solo puedes verlo en BUSCAR CENTRAL, no editarlo.')
        return redirect(url_for('buscar'))
    if request.method=='POST':
        a.nombre = request.form['nombre']
        a.apellidos = request.form['apellidos']
        a.especialidad = request.form.get('especialidad','')
        a.telefono = request.form.get('telefono','')
        a.fecha_nacimiento = request.form.get('fecha_nacimiento','')
        a.lugar_nacimiento = request.form.get('lugar_nacimiento','')
        a.matricula = request.form.get('matricula', a.matricula)
        db.session.commit()
        flash('✅ Alumno actualizado')
        return redirect(url_for('alumnos'))
    content=f"""<div class=card><h3>Editar: {a.nombre} {a.apellidos}</h3><form method=post><label>Nombre</label><input name=nombre value="{a.nombre}" required><label>Apellidos</label><input name=apellidos value="{a.apellidos}" required><label>Matricula</label><input name=matricula value="{a.matricula}"><label>Especialidad</label><input name=especialidad value="{a.especialidad or ''}"><label>Telefono</label><input name=telefono value="{a.telefono or ''}"><label>Fecha Nac</label><input name=fecha_nacimiento value="{a.fecha_nacimiento or ''}"><label>Lugar Nac</label><input name=lugar_nacimiento value="{a.lugar_nacimiento or ''}"><button class="btn btn-blue" style=width:100%;margin-top:10px>Guardar Cambios</button></form></div>"""
    return render_template_string(BASE, content=content, user=u, get_flashed_messages=lambda: [])

# ---------------- PDF V18 ORIGINAL FUSIONADO - LIMPIO SIN LINEA ----------------
@app.route('/alumnos/<int:id>/pdf')
@login_required
def pdf_alumno(id):
    u = get_user()
    a = Alumno.query.get_or_404(id)
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import textwrap

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ENCABEZADO - sin linea como pediste en V18
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.04, 0.18, 0.35)
    c.drawCentredString(width/2, height-60, "CENTRO DE ESTUDIOS AVANZADOS CEACGE")
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.2,0.2,0.2)
    c.drawCentredString(width/2, height-78, "Sistema Central de Gestión Académica - Bata, Guinea Ecuatorial")

    # FOTO grande
    y_foto = height-280
    if a.foto and a.foto.startswith('data:image'):
        try:
            # decode base64
            header, data = a.foto.split(',',1)
            img_data = base64.b64decode(data)
            img_buf = BytesIO(img_data)
            img = ImageReader(img_buf)
            c.drawImage(img, 50, y_foto, width=140, height=170, preserveAspectRatio=True, mask='auto')
        except:
            c.rect(50, y_foto, 140, 170)
            c.drawString(60, y_foto+80, "Foto")
    else:
        c.rect(50, y_foto, 140, 170)
        c.drawString(70, y_foto+80, "Sin Foto")

    # DATOS
    c.setFillColorRGB(0,0,0)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(220, height-120, f"EXPEDIENTE ACADÉMICO - {a.matricula}")
    c.setFont("Helvetica", 11)
    line_y = height-145
    datos = [
        f"Nombre Completo: {a.nombre} {a.apellidos}",
        f"Matrícula: {a.matricula}",
        f"Centro: {a.ipe.nombre if a.ipe else ''} ({a.ipe.codigo if a.ipe else ''})",
        f"Especialidad: {a.especialidad or 'No asignada'}",
        f"Fecha Nacimiento: {a.fecha_nacimiento or '-'}",
        f"Lugar Nacimiento: {a.lugar_nacimiento or '-'}",
        f"Teléfono: {a.telefono or '-'}",
        f"Fecha Registro: {a.fecha_registro.strftime('%d/%m/%Y') if a.fecha_registro else ''}",
    ]
    for d in datos:
        c.drawString(220, line_y, d)
        line_y -= 20

    # QR
    url_ver = request.host_url.rstrip('/') + f'/alumnos/{a.id}'
    qr = qrcode.make(url_ver)
    qr_buf = BytesIO(); qr.save(qr_buf, format='PNG'); qr_buf.seek(0)
    qr_img = ImageReader(qr_buf)
    c.drawImage(qr_img, 50, y_foto-110, width=130, height=130)
    c.setFont("Helvetica", 7)
    c.drawString(50, y_foto-120, "Verificación QR")
    c.setFont("Helvetica", 6)
    c.drawString(50, y_foto-128, url_ver[:55])

    # Texto seguridad SEPARADO como pediste V18
    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(0.04,0.18,0.35)
    c.drawString(50, 200, "NOTA DE SEGURIDAD:")
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.3,0.3,0.3)
    texto_seg = "Este documento es oficial y está registrado en la base de datos central de CEACGE. Cualquier alteración invalida su validez. Verifique la autenticidad escaneando el código QR."
    for i, line in enumerate(textwrap.wrap(texto_seg, 110)):
        c.drawString(50, 188 - i*10, line)

    # SOLO EL DIRECTOR - como pediste
    c.setFillColorRGB(0,0,0)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width-150, 110, "El Director CEACGE")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width-150, 95, "Firma y Sello")
    # espacio para firma sin linea extra
    c.drawString(width-200, 70, "___________________________")

    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.5,0.5,0.5)
    c.drawCentredString(width/2, 30, f"CEACGE Central - Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - Sistema V19 - ceacge-final.onrender.com/alumnos/{a.id}")

    c.showPage()
    c.save()
    buffer.seek(0)
    resp = make_response(buffer.getvalue())
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = f'inline; filename=CEACGE_{a.matricula}.pdf'
    return resp

@app.route('/alumnos/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    u = get_user()
    if request.method=='POST':
        ipe_id = u.ipe_id if u.role!='admin' else int(request.form.get('ipe_id', u.ipe_id))
        al = Alumno(nombre=request.form['nombre'], apellidos=request.form['apellidos'], matricula=request.form['matricula'], especialidad=request.form.get('especialidad',''), telefono=request.form.get('telefono',''), ipe_id=ipe_id)
        db.session.add(al); db.session.commit()
        flash('✅ Alumno creado'); return redirect(url_for('alumnos'))
    ipes_sel = "".join([f"<option value={i.id}>{i.codigo} - {i.nombre}</option>" for i in Ipe.query.all()])
    sel_html = f"<label>Centro (solo admin)</label><select name=ipe_id>{ipes_sel}</select>" if u.role=='admin' else ""
    content = f"<div class=card><h3>Nuevo Alumno</h3><form method=post><input name=nombre placeholder=Nombre required><input name=apellidos placeholder=Apellidos required><input name=matricula placeholder=Matricula required><input name=especialidad placeholder=Especialidad><input name=telefono placeholder=Telefono>{sel_html}<button class='btn btn-blue' style=width:100%;margin-top:10px>Crear Alumno</button></form></div>"
    return render_template_string(BASE, content=content, user=u, get_flashed_messages=lambda: [])

@app.route('/ipes')
@login_required
def ipes():
    u = get_user()
    if u.role!='admin': abort(403)
    rows="".join([f"<tr><td>{i.codigo}</td><td>{i.nombre}</td><td>{i.director or ''}</td></tr>" for i in Ipe.query.all()])
    return render_template_string(BASE, content=f"<div class=card><h3>Centros</h3><table><tr><th>Codigo</th><th>Nombre</th><th>Director</th></tr>{rows}</table></div>", user=u, get_flashed_messages=lambda: [])

if __name__=='__main__':
    app.run(debug=True)
