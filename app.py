import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2, psycopg2.extras
from datetime import datetime
import qrcode
from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','ceacge2025-secret-v20')
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn=get_db(); cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre VARCHAR(200) UNIQUE NOT NULL, codigo VARCHAR(50));")
    cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, password_hash VARCHAR(300) NOT NULL, rol VARCHAR(20) DEFAULT 'centro', centro_id INTEGER REFERENCES centros(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY, nombre VARCHAR(200) NOT NULL, apellidos VARCHAR(200), ipes VARCHAR(100), fecha_nacimiento DATE, nivel VARCHAR(100), centro_id INTEGER REFERENCES centros(id));")
    cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'")
    if not cur.fetchone():
        cur.execute("INSERT INTO centros (nombre,codigo) VALUES ('CEACGE CENTRAL','CENTRAL') RETURNING id")
        cid=cur.fetchone()[0]
    else:
        cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'"); cid=cur.fetchone()[0]
    cur.execute("SELECT id FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)", ('admin', generate_password_hash('ceacge2025'), 'admin', cid))
    conn.commit(); cur.close(); conn.close()

try:
    if DATABASE_URL: init_db()
except: pass

def ensure_v202():
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='alumnos';")
        cols=[r[0] for r in cur.fetchall()]
        for col, typ in [("codigo_alumno","VARCHAR(100)"),("lugar_nacimiento","VARCHAR(150)"),("distrito","VARCHAR(150)"),("provincia","VARCHAR(150)"),("centro_actual","VARCHAR(200)"),("anio_academico","VARCHAR(20)"),("foto_base64","TEXT"),("nivel","VARCHAR(20)")]:
            if col not in cols:
                try: cur.execute(f"ALTER TABLE alumnos ADD COLUMN {col} {typ};")
                except: pass
        cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER REFERENCES alumnos(id) ON DELETE CASCADE, asignatura VARCHAR(150), nota VARCHAR(20), trimestre VARCHAR(50), anio VARCHAR(20));")
        conn.commit(); cur.close(); conn.close()
    except: pass
try: ensure_v202()
except: pass

# ... TU V20 ORIGINAL SE MANTIENE 100% IGUAL, SOLO TE MUESTRO LAS 3 RUTAS NUEVAS ...

@app.route('/nuevo', methods=['GET','POST'])
def nuevo():
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT nombre FROM centros WHERE id=%s", (session['centro_id'],)); r=cur.fetchone(); centro_nombre=r['nombre'] if r else ''; cur.close(); conn.close()
    if request.method=='POST':
        foto=request.form.get('foto_b64','')
        if len(foto)>2000000: foto=''
        nivel=request.form.get('nivel','SECUNDARIA')
        conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO alumnos (nombre,apellidos,codigo_alumno,ipes,nivel,fecha_nacimiento,lugar_nacimiento,distrito,provincia,centro_actual,anio_academico,centro_id,foto_base64) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (request.form['nombre'], request.form['apellidos'], request.form['codigo_alumno'] or request.form['ipes'], request.form['ipes'], nivel, request.form.get('fecha_nacimiento') or None, request.form.get('lugar_nacimiento'), request.form.get('distrito'), request.form.get('provincia'), request.form.get('centro_actual') or centro_nombre, request.form.get('anio_academico') or '2025-2026', session['centro_id'], foto))
        nid=cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
        return redirect(f'/ver/{nid}')
    return render_template_string("""
<body style="font-family:Arial;padding:15px;background:#f4f6f9"><div style="max-width:850px;margin:auto;background:white;padding:20px;border-radius:12px">
<h2 style="text-align:center;color:#0a1931">NUEVO ALUMNO - PRIMARIA / SECUNDARIA / BACHILLERATO / ESBA - V20.2</h2>
<script>
function setNivel(n){document.getElementById('nivel').value=n; document.querySelectorAll('.nivel button').forEach(b=>b.classList.remove('active')); document.getElementById('b-'+n).classList.add('active');}
function previewFoto(e){const f=e.target.files[0]; if(f){const r=new FileReader(); r.onload=function(ev){document.getElementById('prev').src=ev.target.result; document.getElementById('prev').style.display='block'; document.getElementById('foto_b64').value=ev.target.result;}; r.readAsDataURL(f);}}
</script>
<style>label{font-weight:bold;font-size:13px;color:#0a1931;display:block;margin-top:10px}input{width:100%;padding:10px;margin:4px 0;border:1px solid #ccc;border-radius:6px;box-sizing:border-box}.row{display:flex;gap:10px}.row>div{flex:1}.nivel{display:flex;gap:8px;justify-content:center;margin:12px 0}.nivel button{padding:10px 14px;border:2px solid #0a1931;border-radius:8px;font-weight:bold;cursor:pointer;background:white;color:#0a1931}.nivel button.active{background:#0a1931;color:white}.submit{width:100%;padding:14px;background:#28a745;color:white;border:none;border-radius:8px;font-weight:bold;margin-top:15px}</style>
<form method="post">
<div class="nivel"><button type="button" id="b-PRIMARIA" onclick="setNivel('PRIMARIA')">PRIMARIA</button><button type="button" id="b-SECUNDARIA" class="active" onclick="setNivel('SECUNDARIA')">SECUNDARIA</button><button type="button" id="b-BACHILLERATO" onclick="setNivel('BACHILLERATO')">BACHILLERATO</button><button type="button" id="b-ESBA" onclick="setNivel('ESBA')">ESBA</button></div>
<input type="hidden" name="nivel" id="nivel" value="SECUNDARIA">
<div class="row"><div><label>Foto Tamaño Carné</label><input type="file" accept="image/*" onchange="previewFoto(event)"><input type="hidden" name="foto_b64" id="foto_b64"><img id="prev" style="display:none;width:90px;height:110px;object-fit:cover;border:1px solid #ccc;border-radius:6px;margin-top:6px"></div><div><label>Código QR automático</label><div style="background:#f0f0f0;padding:20px;border-radius:8px;text-align:center;font-size:12px">QR se genera solo con código alumno</div></div></div>
<div class="row"><div><label>Nombre *</label><input name="nombre" required></div><div><label>Apellidos *</label><input name="apellidos" required></div></div>
<div class="row"><div><label>Código de Alumno *</label><input name="codigo_alumno" required placeholder="CEA2025-001"></div><div><label>IPES</label><input name="ipes"></div></div>
<div class="row"><div><label>Fecha Nacimiento</label><input name="fecha_nacimiento" type="date"></div><div><label>Lugar Nacimiento</label><input name="lugar_nacimiento"></div></div>
<div class="row"><div><label>Distrito</label><input name="distrito"></div><div><label>Provincia</label><input name="provincia"></div></div>
<div class="row"><div><label>Centro Actual</label><input name="centro_actual" value="{{centro_nombre}}"></div><div><label>Año</label><input name="anio_academico" value="2025-2026"></div></div>
<button class="submit">Guardar Alumno</button></form><br><a href="/">Volver</a></div></body>
    """, centro_nombre=centro_nombre)

@app.route('/notas/<int:alumno_id>', methods=['GET','POST'])
def notas_route(alumno_id):
    if 'user_id' not in session: return redirect('/login')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT a.*, c.nombre as centro_nombre FROM alumnos a JOIN centros c ON a.centro_id=c.id WHERE a.id=%s", (alumno_id,)); alumno=cur.fetchone()
    if request.method=='POST':
        cur.execute("INSERT INTO notas (alumno_id,asignatura,nota,trimestre,anio) VALUES (%s,%s,%s,%s,%s)", (alumno_id, request.form['asignatura'], request.form['nota'], request.form['trimestre'], request.form['anio']))
        conn.commit()
    cur.execute("SELECT * FROM notas WHERE alumno_id=%s ORDER BY id DESC", (alumno_id,)); notas=cur.fetchall(); cur.close(); conn.close()
    html=f"<body style='font-family:Arial;padding:15px;background:#f4f6f9'><div style='max-width:800px;margin:auto;background:white;padding:20px;border-radius:12px'><h2>NOTAS - {alumno['nombre']} {alumno['apellidos']} - {alumno['codigo_alumno']} - BOTON PARA AÑADIR NOTAS</h2><form method='post' style='display:flex;gap:6px;flex-wrap:wrap;background:#f9f9f9;padding:12px;border-radius:8px'><input name='asignatura' placeholder='Asignatura' required style='flex:2;padding:10px;border:1px solid #ccc;border-radius:6px'><input name='nota' placeholder='Nota' required style='flex:1;padding:10px;border:1px solid #ccc;border-radius:6px'><input name='trimestre' placeholder='Trimestre' required style='flex:1;padding:10px;border:1px solid #ccc;border-radius:6px'><input name='anio' value='{alumno['anio_academico'] or '2025-2026'}' style='flex:1;padding:10px;border:1px solid #ccc;border-radius:6px'><button style='padding:10px 15px;background:#6f42c1;color:white;border:none;border-radius:6px;font-weight:bold'>AÑADIR NOTA</button></form><table border=1 cellpadding=8 style='width:100%;margin-top:15px;border-collapse:collapse'><tr style='background:#0a1931;color:white'><th>Asignatura</th><th>Nota</th><th>Trim</th><th>Año</th><th>X</th></tr>"
    for n in notas: html+=f"<tr><td>{n['asignatura']}</td><td>{n['nota']}</td><td>{n['trimestre']}</td><td>{n['anio']}</td><td><a href='/borrar_nota/{n['id']}?alumno={alumno_id}' style='color:red'>X</a></td></tr>"
    html+=f"</table><br><a href='/ver/{alumno_id}'>VER</a> <a href='/'>Volver</a></div></body>"
    return html

@app.route('/borrar_nota/<int:id>')
def borrar_nota(id):
    if 'user_id' not in session: return redirect('/login')
    alumno_id=request.args.get('alumno'); conn=get_db(); cur=conn.cursor(); cur.execute("DELETE FROM notas WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return redirect(f'/notas/{alumno_id}' if alumno_id else '/')

@app.route('/usuarios', methods=['GET','POST'])
def usuarios():
    if 'user_id' not in session or session['rol']!='admin': return redirect('/')
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    msg=''
    if request.method=='POST':
        centro_nombre=request.form.get('centro_nombre','').strip()
        username=request.form.get('username','').strip()
        password=request.form.get('password','').strip()
        rol=request.form.get('rol','centro')
        try:
            cur.execute("SELECT id FROM centros WHERE LOWER(nombre)=LOWER(%s)", (centro_nombre,))
            row=cur.fetchone()
            if row: centro_id=row['id']
            else:
                cur.execute("INSERT INTO centros (nombre,codigo) VALUES (%s,%s) RETURNING id", (centro_nombre, (centro_nombre[:6].upper().replace(' ','') or 'CENT')+'01'))
                centro_id=cur.fetchone()['id']
            cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)", (username, generate_password_hash(password), rol, centro_id))
            conn.commit()
            msg=f"<p style='color:green;font-weight:bold'>✓ GENERADO: Centro '{centro_nombre}' + Usuario '{username}' / '{password}'</p>"
        except Exception as e:
            conn.rollback(); msg=f"<p style='color:red'>{e}</p>"
    cur.execute("SELECT * FROM centros ORDER BY nombre"); centros_list=cur.fetchall()
    cur.execute("SELECT u.*, c.nombre as centro_nombre FROM usuarios u LEFT JOIN centros c ON u.centro_id=c.id ORDER BY u.id DESC"); users=cur.fetchall()
    cur.close(); conn.close()
    html=f"<body style='font-family:Arial;padding:20px;background:#f4f6f9'><h2>Usuarios - Nombre del centro + Usuario + Contraseña > Generar - V20.2</h2>{msg}<form method='post' style='background:white;padding:20px;border-radius:12px;max-width:550px'><label>Nombre del Centro *</label><input name='centro_nombre' required style='width:100%;padding:12px;margin:6px 0;border:1px solid #ccc;border-radius:8px'><label>Usuario *</label><input name='username' required style='width:100%;padding:12px;margin:6px 0'><label>Contraseña *</label><input name='password' required style='width:100%;padding:12px;margin:6px 0'><label>Rol</label><select name='rol' style='width:100%;padding:12px'><option value='centro'>centro</option><option value='admin'>admin</option></select><button style='width:100%;padding:14px;background:#28a745;color:white;border:none;border-radius:8px;font-weight:bold;margin-top:10px'>GENERAR</button></form><br><table border=1 cellpadding=8 style='background:white;border-collapse:collapse'><tr style='background:#0a1931;color:white'><th>Usuario</th><th>Centro</th></tr>"
    for u in users: html+=f"<tr><td>{u['username']}</td><td>{u['centro_nombre']}</td></tr>"
    html+="</table><br><a href='/'>Volver</a></body>"
    return html
