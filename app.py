# CEACGE V19.1 FINAL - TODO FUSIONADO
# V18 ORIGINAL + BUSCAR CENTRAL + HTTPS + USUARIOS MANUALES ASIGNADOS POR LA CENTRAL
# Mantiene: PDF limpio sin linea, Solo Director, Seguridad separado, VER elegante

import os, base64, qrcode
from io import BytesIO
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, make_response, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ceacge-v19-1-manual-2026")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///ceacge_v19_1.db")
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# FORZAR HTTPS - quita advertencia "No seguro" en Render
@app.before_request
def force_https():
    if request.headers.get('X-Forwarded-Proto', 'http') == 'http':
        if 'onrender.com' in request.host:
            return redirect(request.url.replace('http://', 'https://', 1), code=301)

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

with app.app_context():
    db.create_all()
    if not Ipe.query.first():
        db.session.add(Ipe(codigo='CEACGE-CENTRAL', nombre='CEACGE Central - Bata', director='Director General'))
        db.session.add(Ipe(codigo='IPES-007', nombre='IPES PADRE SANTY', director='Director'))
        db.session.commit()
    if not User.query.filter_by(username='admin').first():
        ipe = Ipe.query.first()
        db.session.add(User(username='admin', password=generate_password_hash('admin123'), role='admin', ipe_id=ipe.id))
        db.session.commit()

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*a,**kw)
    return dec

def get_user():
    if 'user_id' in session: return User.query.get(session['user_id'])
    return None

def can_edit(user, alumno):
    if not user: return False
    if user.role=='admin': return True
    return user.ipe_id==alumno.ipe_id

BASE = """
<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>CEACGE V19.1</title>
<style>
body{font-family:Arial;background:#f4f6f9;margin:0}
.header{background:#0b2e59;color:#fff;padding:15px;display:flex;justify-content:space-between;flex-wrap:wrap}
.btn{padding:8px 14px;border-radius:6px;text-decoration:none;color:#fff;border:none;cursor:pointer;margin:2px;display:inline-block}
.btn-blue{background:#0b2e59}.btn-green{background:#198754}.btn-orange{background:#fd7e14}.btn-red{background:#dc3545}
.card{background:#fff;padding:16px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08);margin:12px 0}
table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #e9ecef;text-align:left}
.badge{padding:5px 10px;border-radius:20px;font-size:11px;font-weight:bold}
.badge-warn{background:#fff3cd;color:#664d03;border:1px solid #ffecb5}
input,select{width:100%;padding:11px;margin:6px 0;border:1px solid #ccc;border-radius:8px}
</style></head><body>
<div class=header><b>CEACGE V19.1 - LIVE</b><div>{% if user %}{{user.username}} ({{user.role}}) {% if user.ipe %}- {{user.ipe.codigo}}{% endif %} | <a href=/logout style=color:#fff>Salir</a>{% endif %}</div></div>
<div style=padding:15px>{% with msgs=get_flashed_messages() %}{% if msgs %}{% for m in msgs %}<div class=card style=background:#fff3cd;border-left:5px solid #ffc107>{{m}}</div>{% endfor %}{% endif %}{% endwith %}{{content|safe}}</div></body></html>
"""

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user_id']=u.id
            return redirect(url_for('index'))
        flash('Usuario o clave incorrecta')
    html="""<div class=card style=max-width:420px;margin:50px auto><h3>CEACGE - Entrar</h3><form method=post><input name=username placeholder="Usuario / Código Centro" required><input name=password type=password placeholder="Contraseña / Código Acceso" required><button class="btn btn-blue" style=width:100%>Entrar</button></form><p style=font-size:12px;color:#666>Admin: admin / admin123<br>Centros: usan el usuario y clave que tú les asignas manualmente</p></div>"""
    return render_template_string(BASE, content=html, user=None, get_flashed_messages=lambda: [])

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    u=get_user(); total=Alumno.query.count(); mis=total if u.role=='admin' else Alumno.query.filter_by(ipe_id=u.ipe_id).count()
    content=f"""
    <div style=display:grid;grid-template-columns:1fr 1fr;gap:12px>
      <div class=card><h4>Total Central CEACGE</h4><h1>{total}</h1></div>
      <div class=card><h4>Mis Alumnos</h4><h1>{mis}</h1><small>{u.ipe.codigo if u.ipe else 'ADMIN'}</small></div>
    </div>
    <div class=card>
      <a class="btn btn-blue" href=/alumnos>📋 Mis Alumnos</a>
      <a class="btn btn-orange" href=/buscar>🔍 BUSCAR CENTRAL (Solo ver alumnos de todo CEACGE)</a>
      <a class="btn btn-green" href=/alumnos/nuevo>➕ Nuevo Alumno</a>
      {'<a class="btn btn-blue" href=/ipes>🏫 Centros</a> <a class="btn btn-blue" href=/usuarios>👤 Usuarios - Asignar accesos manualmente</a>' if u.role=='admin' else ''}
    </div>
    """
    return render_template_string(BASE, content=content, user=u, get_flashed_messages=lambda: [])

@app.route('/alumnos')
@login_required
def alumnos():
    u=get_user(); q=request.args.get('q',''); query=Alumno.query if u.role=='admin' else Alumno.query.filter_by(ipe_id=u.ipe_id)
    if q: query=query.filter((Alumno.nombre.contains(q)) | (Alumno.apellidos.contains(q)) | (Alumno.matricula.contains(q)))
    lista=query.order_by(Alumno.id.desc()).limit(200).all()
    rows="".join([f"<tr><td>{a.matricula}</td><td>{a.nombre} {a.apellidos}</td><td>{a.ipe.codigo if a.ipe else ''}</td><td><a class='btn btn-blue' href=/alumnos/{a.id}>VER</a> <a class='btn btn-green' href=/alumnos/{a.id}/pdf>PDF</a> <a class='btn btn-orange' href=/alumnos/{a.id}/editar>Editar</a></td></tr>" for a in lista])
    return render_template_string(BASE, content=f"<div class=card><h3>Mis Alumnos</h3><form><input name=q value='{q}' placeholder=Buscar...><button class=btn-blue>Buscar</button></form><table><tr><th>Matricula</th><th>Nombre</th><th>Centro</th><th>Acciones</th></tr>{rows}</table></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/buscar')
@login_required
def buscar():
    u=get_user(); q=request.args.get('q','').strip(); query=Alumno.query
    if q: query=query.filter(db.or_(Alumno.nombre.ilike(f"%{q}%"), Alumno.apellidos.ilike(f"%{q}%"), Alumno.matricula.ilike(f"%{q}%"), Alumno.telefono.ilike(f"%{q}%")))
    lista=query.order_by(Alumno.id.desc()).limit(200).all()
    rows=""
    for a in lista:
        es_mio=can_edit(u,a)
        if es_mio: acciones=f"<a class='btn btn-blue' href=/alumnos/{a.id}>VER</a> <a class='btn btn-green' href=/alumnos/{a.id}/pdf>PDF</a> <a class='btn btn-orange' href=/alumnos/{a.id}/editar>Editar</a>"
        else: acciones=f"<a class='btn btn-blue' href=/alumnos/{a.id}>VER</a> <a class='btn btn-green' href=/alumnos/{a.id}/pdf>PDF</a> <span class=badge badge-warn>OTRO CENTRO - SOLO VER</span>"
        rows+=f"<tr><td>{a.matricula}</td><td>{a.nombre} {a.apellidos}</td><td>{a.ipe.codigo if a.ipe else ''}</td><td>{acciones}</td></tr>"
    return render_template_string(BASE, content=f"<div class=card><h3>🔍 BUSCAR CENTRAL</h3><p style=font-size:13px>Centros ven todo CEACGE pero SOLO VER. Admin edita todo.</p><form method=get><input name=q value='{q}' placeholder='Buscar...'><button class=btn-blue>Buscar</button></form><table><tr><th>Matricula</th><th>Nombre</th><th>Centro</th><th>Acciones</th></tr>{rows}</table></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/alumnos/<int:id>')
@login_required
def ver_alumno(id):
    u=get_user(); a=Alumno.query.get_or_404(id); es_mio=can_edit(u,a); url=request.host_url.rstrip('/')+f'/alumnos/{a.id}'; qr=qrcode.make(url); buf=BytesIO(); qr.save(buf,format='PNG'); qr_b64=base64.b64encode(buf.getvalue()).decode()
    foto=f"<img src='{a.foto}' style=width:200px;height:240px;object-fit:cover;border-radius:12px;border:3px solid #0b2e59>" if a.foto else "<div style=width:200px;height:240px;background:#ddd;display:flex;align-items:center;justify-content:center;border-radius:12px>Sin Foto</div>"
    aviso="" if es_mio else f"<div class=card style=background:#fff3cd;border-left:5px solid #ffc107><b>SOLO LECTURA:</b> Pertenece a {a.ipe.codigo if a.ipe else 'otro centro'}</div>"
    return render_template_string(BASE, content=f"{aviso}<div class=card><div style=display:flex;gap:20px;flex-wrap:wrap><div>{foto}<br><br><img src='data:image/png;base64,{qr_b64}' style=width:160px><br><small>{url}</small></div><div><h2>{a.nombre} {a.apellidos}</h2><p>{a.matricula} - {a.ipe.codigo if a.ipe else ''}</p><a class='btn btn-green' href=/alumnos/{a.id}/pdf>PDF Oficial</a>{'<a class=btn-orange href=/alumnos/'+str(a.id)+'/editar>Editar</a>' if es_mio else ''} <a class='btn btn-blue' href=/buscar>Buscar Central</a></div></div></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/alumnos/<int:id>/editar', methods=['GET','POST'])
@login_required
def editar_alumno(id):
    u=get_user(); a=Alumno.query.get_or_404(id)
    if not can_edit(u,a): flash(f'⛔ No autorizado: {a.nombre} es de {a.ipe.codigo if a.ipe else "otro centro"}'); return redirect(url_for('buscar'))
    if request.method=='POST':
        a.nombre=request.form['nombre']; a.apellidos=request.form['apellidos']; a.matricula=request.form['matricula']; a.especialidad=request.form.get('especialidad',''); db.session.commit(); flash('Actualizado'); return redirect(url_for('alumnos'))
    return render_template_string(BASE, content=f"<div class=card><h3>Editar {a.nombre}</h3><form method=post><input name=nombre value='{a.nombre}'><input name=apellidos value='{a.apellidos}'><input name=matricula value='{a.matricula}'><input name=especialidad value='{a.especialidad or ''}'><button class=btn-blue>Guardar</button></form></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/alumnos/<int:id>/pdf')
@login_required
def pdf_alumno(id):
    u=get_user(); a=Alumno.query.get_or_404(id)
    from reportlab.lib.pagesizes import A4; from reportlab.pdfgen import canvas; from reportlab.lib.utils import ImageReader; import textwrap
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=A4); w,h=A4
    c.setFont("Helvetica-Bold",18); c.setFillColorRGB(0.04,0.18,0.35); c.drawCentredString(w/2,h-60,"CENTRO DE ESTUDIOS AVANZADOS CEACGE")
    c.setFont("Helvetica",11); c.setFillColorRGB(0.2,0.2,0.2); c.drawCentredString(w/2,h-78,"Sistema Central de Gestión Académica - Bata")
    y=h-280
    if a.foto and a.foto.startswith('data:image'):
        try:
            hdr,dat=a.foto.split(',',1); imgd=base64.b64decode(dat); ibuf=BytesIO(imgd); c.drawImage(ImageReader(ibuf),50,y,width=140,height=170,preserveAspectRatio=True,mask='auto')
        except: c.rect(50,y,140,170)
    else: c.rect(50,y,140,170)
    c.setFillColorRGB(0,0,0); c.setFont("Helvetica-Bold",13); c.drawString(220,h-120,f"EXPEDIENTE - {a.matricula}")
    c.setFont("Helvetica",11); ly=h-145
    for d in [f"Nombre: {a.nombre} {a.apellidos}",f"Matricula: {a.matricula}",f"Centro: {a.ipe.nombre if a.ipe else ''} ({a.ipe.codigo if a.ipe else ''})",f"Especialidad: {a.especialidad or '-'}",f"Tel: {a.telefono or '-'}"]:
        c.drawString(220,ly,d); ly-=20
    url=request.host_url.rstrip('/')+f'/alumnos/{a.id}'; qr=qrcode.make(url); qbuf=BytesIO(); qr.save(qbuf,format='PNG'); qbuf.seek(0); c.drawImage(ImageReader(qbuf),50,y-110,width=130,height=130)
    c.setFont("Helvetica-Bold",9); c.setFillColorRGB(0.04,0.18,0.35); c.drawString(50,200,"NOTA DE SEGURIDAD:"); c.setFont("Helvetica",8); c.setFillColorRGB(0.3,0.3,0.3)
    txt="Este documento es oficial y está registrado en la base de datos central de CEACGE. Cualquier alteración invalida su validez. Verifique autenticidad escaneando QR."
    for i,ln in enumerate(textwrap.wrap(txt,110)): c.drawString(50,188-i*10,ln)
    c.setFillColorRGB(0,0,0); c.setFont("Helvetica-Bold",11); c.drawCentredString(w-150,110,"El Director CEACGE"); c.setFont("Helvetica",10); c.drawCentredString(w-150,95,"Firma y Sello"); c.drawString(w-200,70,"___________________________")
    c.showPage(); c.save(); buf.seek(0); r=make_response(buf.getvalue()); r.headers['Content-Type']='application/pdf'; r.headers['Content-Disposition']=f'inline; filename=CEACGE_{a.matricula}.pdf'; return r

@app.route('/alumnos/nuevo', methods=['GET','POST'])
@login_required
def nuevo():
    u=get_user()
    if request.method=='POST':
        ipe_id=u.ipe_id if u.role!='admin' else int(request.form.get('ipe_id',u.ipe_id))
        al=Alumno(nombre=request.form['nombre'],apellidos=request.form['apellidos'],matricula=request.form['matricula'],especialidad=request.form.get('especialidad',''),ipe_id=ipe_id)
        db.session.add(al); db.session.commit(); flash('Alumno creado'); return redirect(url_for('alumnos'))
    opts="".join([f"<option value={i.id}>{i.codigo} - {i.nombre}</option>" for i in Ipe.query.all()])
    sel=f"<select name=ipe_id>{opts}</select>" if u.role=='admin' else ""
    return render_template_string(BASE, content=f"<div class=card><h3>Nuevo Alumno</h3><form method=post><input name=nombre placeholder=Nombre required><input name=apellidos placeholder=Apellidos required><input name=matricula placeholder=Matricula required><input name=especialidad placeholder=Especialidad>{sel}<button class=btn-blue>Crear</button></form></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/ipes')
@login_required
def ipes():
    u=get_user()
    if u.role!='admin': abort(403)
    rows="".join([f"<tr><td>{i.codigo}</td><td>{i.nombre}</td><td><a class='btn btn-orange' href=/ipes/{i.id}/editar>Editar</a></td></tr>" for i in Ipe.query.all()])
    return render_template_string(BASE, content=f"<div class=card><h3>Centros</h3><a class='btn btn-blue' href=/ipes/nuevo>➕ Nuevo Centro</a><table><tr><th>Codigo</th><th>Nombre</th><th></th></tr>{rows}</table></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/ipes/nuevo', methods=['GET','POST'])
@login_required
def nuevo_ipe():
    u=get_user()
    if u.role!='admin': abort(403)
    if request.method=='POST':
        i=Ipe(codigo=request.form['codigo'].strip().upper(), nombre=request.form['nombre'], director=request.form.get('director',''))
        db.session.add(i); db.session.commit(); flash(f'Centro {i.codigo} creado. Ahora asignale usuario manual en Usuarios'); return redirect(url_for('ipes'))
    return render_template_string(BASE, content="<div class=card><h3>Nuevo Centro</h3><form method=post><input name=codigo placeholder=Codigo Ej: IPES-008 required><input name=nombre placeholder=Nombre Centro required><input name=director placeholder=Director><button class=btn-blue>Crear Centro</button></form></div>", user=u, get_flashed_messages=lambda: [])

# --- USUARIOS MANUALES - SOLO CENTRAL ---
@app.route('/usuarios')
@login_required
def lista_usuarios():
    u=get_user()
    if u.role!='admin': flash('Solo central'); return redirect(url_for('index'))
    usuarios=User.query.order_by(User.id.desc()).all()
    rows="".join([f"<tr><td>{us.username}</td><td>{us.role}</td><td>{us.ipe.codigo if us.ipe else 'CENTRAL'}</td><td><a class='btn btn-orange' href=/usuarios/{us.id}/editar>Editar Clave</a> <a class='btn btn-red' href=/usuarios/{us.id}/eliminar onclick=\"return confirm('¿Borrar?')\">Borrar</a></td></tr>" for us in usuarios])
    return render_template_string(BASE, content=f"<div class=card><h3>👤 Gestión Manual de Accesos - Central</h3><p style=font-size:13px>Tú asignas manualmente usuario y contraseña/código a cada centro.</p><a class='btn btn-blue' href=/usuarios/nuevo>➕ Asignar Nuevo Usuario a Centro</a><table style=margin-top:12px><tr><th>Usuario / Código</th><th>Rol</th><th>Centro</th><th>Acciones</th></tr>{rows}</table></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/usuarios/nuevo', methods=['GET','POST'])
@login_required
def nuevo_usuario_manual():
    u=get_user()
    if u.role!='admin': abort(403)
    if request.method=='POST':
        username=request.form['username'].strip(); pwd=request.form['password'].strip(); ipe_id=request.form['ipe_id']; role=request.form.get('role','centro')
        if User.query.filter_by(username=username).first(): flash('Ya existe'); return redirect(url_for('nuevo_usuario_manual'))
        nuevo=User(username=username, password=generate_password_hash(pwd), role=role, ipe_id=int(ipe_id) if ipe_id else None)
        db.session.add(nuevo); db.session.commit(); flash(f'✅ Asignado: {username} / {pwd}'); return redirect(url_for('lista_usuarios'))
    opts="".join([f"<option value={i.id}>{i.codigo} - {i.nombre}</option>" for i in Ipe.query.all()])
    return render_template_string(BASE, content=f"<div class=card style=max-width:600px;margin:auto><h3>➕ Asignar Usuario Manual</h3><p style=font-size:12px>Ej: Usuario: IPES-007 | Clave: BATA2026</p><form method=post><label>Usuario / Código Centro</label><input name=username required><label>Contraseña / Código Acceso (tú la inventas)</label><input name=password required><label>Centro</label><select name=ipe_id required>{opts}</select><label>Rol</label><select name=role><option value=centro>centro</option><option value=admin>admin</option></select><button class=btn-blue style=width:100%;margin-top:10px>Asignar Manualmente</button></form></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/usuarios/<int:id>/editar', methods=['GET','POST'])
@login_required
def editar_usuario_manual(id):
    u=get_user()
    if u.role!='admin': abort(403)
    us=User.query.get_or_404(id)
    if request.method=='POST':
        us.username=request.form['username'].strip(); npwd=request.form['password'].strip()
        if npwd: us.password=generate_password_hash(npwd); flash(f'Clave cambiada a: {npwd}')
        us.ipe_id=int(request.form['ipe_id']) if request.form['ipe_id'] else None; us.role=request.form.get('role','centro'); db.session.commit(); flash('Actualizado'); return redirect(url_for('lista_usuarios'))
    opts="".join([f"<option value={i.id} {'selected' if i.id==us.ipe_id else ''}>{i.codigo} - {i.nombre}</option>" for i in Ipe.query.all()])
    return render_template_string(BASE, content=f"<div class=card style=max-width:600px;margin:auto><h3>Editar {us.username}</h3><form method=post><input name=username value='{us.username}' required><input name=password placeholder='Nueva clave (vacío = no cambiar)'><select name=ipe_id>{opts}</select><select name=role><option value=centro {'selected' if us.role=='centro' else ''}>centro</option><option value=admin {'selected' if us.role=='admin' else ''}>admin</option></select><button class=btn-blue>Guardar</button></form></div>", user=u, get_flashed_messages=lambda: [])

@app.route('/usuarios/<int:id>/eliminar')
@login_required
def eliminar_usuario_manual(id):
    u=get_user()
    if u.role!='admin': abort(403)
    us=User.query.get_or_404(id)
    if us.username=='admin': flash('No puedes borrar admin'); return redirect(url_for('lista_usuarios'))
    db.session.delete(us); db.session.commit(); flash('Borrado'); return redirect(url_for('lista_usuarios'))

if __name__=='__main__':
    app.run(debug=True)
