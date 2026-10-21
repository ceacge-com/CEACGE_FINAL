import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2, psycopg2.extras
import qrcode
from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','ceacge2025-secret')
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn=get_db(); cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY, nombre VARCHAR(200) UNIQUE NOT NULL, codigo VARCHAR(50));")
    cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, password_hash VARCHAR(300) NOT NULL, rol VARCHAR(20) DEFAULT 'centro', centro_id INTEGER REFERENCES centros(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY,nombre VARCHAR(200) NOT NULL,apellidos VARCHAR(200),codigo_alumno VARCHAR(100),ipes VARCHAR(100),nivel VARCHAR(20) DEFAULT 'SECUNDARIA',fecha_nacimiento DATE,lugar_nacimiento VARCHAR(150),distrito VARCHAR(150),provincia VARCHAR(150),centro_actual VARCHAR(200),anio_academico VARCHAR(20),centro_id INTEGER REFERENCES centros(id),foto_base64 TEXT);")
    cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY,alumno_id INTEGER REFERENCES alumnos(id) ON DELETE CASCADE,asignatura VARCHAR(150),nota VARCHAR(20),trimestre VARCHAR(50),anio VARCHAR(20));")
    cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'")
    if not cur.fetchone():
        cur.execute("INSERT INTO centros (nombre,codigo) VALUES ('CEACGE CENTRAL','CENTRAL') RETURNING id")
        cid=cur.fetchone()[0]
    else:
        cur.execute("SELECT id FROM centros WHERE nombre='CEACGE CENTRAL'")
        cid=cur.fetchone()[0]
    cur.execute("SELECT id FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username,password_hash,rol,centro_id) VALUES (%s,%s,%s,%s)", ('admin', generate_password_hash('ceacge2025'), 'admin', cid))
    conn.commit(); cur.close(); conn.close()

try:
    if DATABASE_URL:
        init_db()
except Exception as e:
    print(e)

# ... HTML templates igual que antes ...

@app.route('/nuevo', methods=['GET','POST'])
def nuevo():
    if 'user_id' not in session:
        return redirect('/login')
    conn=get_db()
    cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT nombre FROM centros WHERE id=%s", (session['centro_id'],))
    r=cur.fetchone()
    centro_nombre=r['nombre'] if r else ''
    cur.close()
    conn.close()
    if request.method=='POST':
        foto=request.form.get('foto_b64','')
        if len(foto)>2000000:
            foto=''
        conn=get_db()
        cur=conn.cursor()
        placeholders = ",".join(["%s"]*13)
        sql = f"INSERT INTO alumnos (nombre,apellidos,codigo_alumno,ipes,nivel,fecha_nacimiento,lugar_nacimiento,distrito,provincia,centro_actual,anio_academico,centro_id,foto_base64) VALUES ({placeholders}) RETURNING id"
        cur.execute(sql, (
            request.form['nombre'],
            request.form['apellidos'],
            request.form['codigo_alumno'],
            request.form['ipes'],
            request.form['nivel'],
            request.form.get('fecha_nacimiento') or None,
            request.form.get('lugar_nacimiento'),
            request.form.get('distrito'),
            request.form.get('provincia'),
            request.form.get('centro_actual'),
            request.form.get('anio_academico'),
            session['centro_id'],
            foto
        ))
        nid=cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return redirect(f'/ver/{nid}')
    return render_template_string(NUEVO_HTML, centro_nombre=centro_nombre)
