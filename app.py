import os, sqlite3, io, secrets, string
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
app.secret_key='V18-SIN-LINEA-DIRECTOR-VER-COMPLETO-ELEGANTE'
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
    try:
        if USE_POSTGRES:
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id SERIAL PRIMARY KEY)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id SERIAL PRIMARY KEY)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id SERIAL PRIMARY KEY)")
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id SERIAL PRIMARY KEY, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
            for col in ["nombre TEXT","apellidos TEXT","natural_de TEXT","distrito TEXT","provincia TEXT","centro TEXT","foto TEXT","anio TEXT","contacto TEXT","email TEXT","centro_nombre TEXT","centro_codigo TEXT","centro_localidad TEXT","centro_contacto TEXT"]:
                try: cur.execute(f"ALTER TABLE alumnos ADD COLUMN IF NOT EXISTS {col}")
                except: pass
            for col in ["nombre TEXT","apellidos TEXT","hijo_de TEXT","y_de TEXT","fecha_nacimiento TEXT","centro TEXT","localidad TEXT","codigo TEXT","foto TEXT","anio TEXT","centro_codigo TEXT"]:
                try: cur.execute(f"ALTER TABLE alumnos_primaria ADD COLUMN IF NOT EXISTS {col}")
                except: pass
            for col in ["nombre TEXT","codigo TEXT","localidad TEXT","contacto TEXT","email TEXT","codigo_acceso TEXT"]:
                try: cur.execute(f"ALTER TABLE centros ADD COLUMN IF NOT EXISTS {col}")
                except: pass
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS alumnos_primaria (id INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS centros (id INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT, rol TEXT, centro_codigo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, curso TEXT, asignatura TEXT, ord TEXT, extra TEXT)")
        try:
            cur.execute(adapt("SELECT * FROM usuarios WHERE usuario=?"), ("admin",))
            if not cur.fetchone():
                cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol) VALUES (?,?,?)"), ("admin", generate_password_hash("ceacge2025"), "admin"))
        except Exception as e:
            print(f"admin warning: {e}")
        conn.commit()
    except Exception as e:
        print(f"init_db error: {e}")
        try: conn.rollback()
        except: pass
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass
