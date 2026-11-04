@app.route('/alumno/<int:id>')
def alumno_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13],'foto':r[11],'centro_codigo':r[12],'anio':r[9],'observaciones':r[14] if len(r)>14 else '', 'foto_data':r[15] if len(r)>15 else ''}
    cur.execute(adapt("SELECT * FROM notas_historico WHERE alumno_codigo=? ORDER BY anio_academico"), (d['codigo_alumno'],)); hist_rows=cur.fetchall()
    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=? ORDER BY curso"), (d['codigo_alumno'],)); old_rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    qr=gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    foto_html=get_foto_html(d, 150, 200)
    hist_html=""
    for hr in hist_rows:
        h=dict(hr) if isinstance(hr,dict) else {'anio_academico':hr[2],'curso':hr[3],'datos':hr[4]}
        try:
            datos=json.loads(h.get('datos') or '{}')
            if not datos: continue
            hist_html+=f"<div class='card p-2 mb-2 border-primary'><b>Año: {h.get('anio_academico')} - {h.get('curso')}</b><table class='table table-sm'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
            for mat,vals in datos.items():
                def _col(v):
                    try:
                        if not v: return ""
                        return "color:#d00000;font-weight:bold;background:#ffe0e0" if float(str(v).replace(',','.'))<5 else "color:#0a7d00;font-weight:bold;background:#e7f3ff"
                    except: return ""
                hist_html+=f"<tr><td>{mat}</td><td style='{_col(vals.get('T1',''))}'>{vals.get('T1','')}</td><td style='{_col(vals.get('T2',''))}'>{vals.get('T2','')}</td><td style='{_col(vals.get('T3',''))}'>{vals.get('T3','')}</td><td style='{_col(vals.get('JUN',''))}'><b>{vals.get('JUN','')}</b></td></tr>"
            hist_html+="</table></div>"
        except: pass
    if not hist_html:
        for hr in old_rows:
            h=dict(hr) if isinstance(hr,dict) else {'curso':hr[2] if len(hr)>2 else '', 'datos':hr[3] if len(hr)>3 else ''}
            try:
                datos=json.loads(h.get('datos') or '{}')
                if not datos: continue
                hist_html+=f"<div class='card p-2 mb-2 border-success'><b>Historial registrado: {h.get('curso')} (antiguo)</b><table class='table table-sm'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
                for mat,vals in datos.items():
                    if isinstance(vals, dict):
                        def _col(v):
                            try:
                                if not v: return ""
                                return "color:#d00000;font-weight:bold;background:#ffe0e0" if float(str(v).replace(',','.'))<5 else "color:#0a7d00;font-weight:bold;background:#e7f3ff"
                            except: return ""
                        hist_html+=f"<tr><td>{mat}</td><td style='{_col(vals.get('T1',''))}'>{vals.get('T1','')}</td><td style='{_col(vals.get('T2',''))}'>{vals.get('T2','')}</td><td style='{_col(vals.get('T3',''))}'>{vals.get('T3','')}</td><td style='{_col(vals.get('JUN',''))}'><b>{vals.get('JUN','')}</b></td></tr>"
                    else:
                        hist_html+=f"<tr><td>{mat}</td><td colspan=4><b>{vals}</b></td></tr>"
                hist_html+="</table></div>"
            except: pass
    if not hist_html: hist_html="<div class='alert alert-warning'>Sin historial - Añade notas abajo</div>"
    options_anio = "".join([f"<option value='{a}'>{a}</option>" for a in ANIOS_ACADEMICOS])
    form_html = f"<div class='card p-3 mt-4 border-primary'><h5>Añadir Notas Año</h5><form method='post' action='/alumno/{id}/notas_historico/guardar'><select name='anio_academico' class='form-control mb-2'>{options_anio}</select><input name='curso_detalle' class='form-control mb-2' placeholder='Curso'><div id='materiasContainer'></div><button class='btn btn-success mt-2'>Guardar</button></form></div><script>const PLAN={json.dumps(PLAN)};function cargar(){{let s=document.querySelector('select[name=anio_academico]').value;let m=PLAN[s]||[];let h=\"<table class='table table-sm'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>\";m.forEach(x=>{{h+=`<tr><td>${{x}}</td><td><input name='T1_${{x}}' class='form-control form-control-sm'></td><td><input name='T2_${{x}}' class='form-control form-control-sm'></td><td><input name='T3_${{x}}' class='form-control form-control-sm'></td><td><input name='JUN_${{x}}' class='form-control form-control-sm'></td></tr>`}});h+=\"</table>\";document.getElementById('materiasContainer').innerHTML=h}}document.querySelector('select[name=anio_academico]').addEventListener('change',cargar);cargar();</script>"
    # MOD 1: ocultar Editar/Eliminar si no es suyo ni Central
    _v_editar = f"<a href='/alumno/{id}/editar' class='btn btn-warning btn-sm'>Editar</a>" if _puede_editar_registro(d) else ""
    _v_eliminar = f"<a href='/alumno/{id}/eliminar' class='btn btn-danger btn-sm' onclick=\"return confirm('Eliminar?')\">Eliminar Alumno</a>" if _puede_editar_registro(d) else ""
    return render_template_string(BASE, content=f"<div class='d-flex gap-2 mb-2 flex-wrap'><a href='/alumnos' class='btn btn-secondary btn-sm'>Volver</a>{_v_editar}<a href='/alumno/{id}/selectividad' class='btn btn-dark btn-sm'>Selectividad</a><a href='/alumno/{id}/hoja_academica' target='_blank' class='btn btn-success btn-sm'>📄 Hoja Académica VERTICAL</a>{_v_eliminar}</div><div class='row mt-3'><div class='col-md-8'><h4>{d['nombre']} {d['apellidos']} ({d['codigo_alumno']})</h4>{hist_html}{form_html}</div><div class='col-md-4 text-center'>{foto_html}<br><br><img src='{qr}' style='width:180px'></div></div>")

@app.route('/alumno/<int:id>/notas_historico/guardar', methods=['POST'])
def guardar_historico(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
    # MOD 1: notas tambien son edicion, solo Central o creador
    if not _puede_editar_registro(d):
        try: cur.close(); conn.close()
        except: pass
        return render_template_string(BASE, content="<div class='alert alert-danger'>No tienes permiso para modificar notas de este alumno.</div><a href='/alumnos' class='btn btn-secondary'>Volver</a>")
    anio_acad = request.form.get('anio_academico') or ''
    curso_det = request.form.get('curso_detalle') or anio_acad
    datos={}
    for k,v in request.form.items():
        if k.startswith(('T1_','T2_','T3_','JUN_')):
            parts=k.split('_',1); trim=parts[0]; mat=parts[1]
            if mat not in datos: datos[mat]={}
            datos[mat][trim]=v.strip()
    datos = {m:vals for m,vals in datos.items() if any(vals.values())}
    json_data=json.dumps(datos, ensure_ascii=False)
    cur.execute(adapt("SELECT * FROM notas_historico WHERE alumno_codigo=? AND anio_academico=?"), (d['codigo_alumno'], anio_acad))
    existe=cur.fetchone()
    if existe: cur.execute(adapt("UPDATE notas_historico SET datos=?, curso=? WHERE alumno_codigo=? AND anio_academico=?"), (json_data, curso_det, d['codigo_alumno'], anio_acad))
    else: cur.execute(adapt("INSERT INTO notas_historico (alumno_codigo, anio_academico, curso, datos, centro_codigo) VALUES (?,?,?,?,?)"), (d['codigo_alumno'], anio_acad, curso_det, json_data, d['centro_codigo']))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect(f'/alumno/{id}')

@app.route('/alumno/<int:id>/selectividad')
def alumno_selectividad(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10]}
    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (d['codigo_alumno'],)); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html_rows=""
    for s in rows:
        sd=dict(s) if isinstance(s,dict) else {}
        if sd: n1=sd.get('nota',''); n2=sd.get('nota2',''); sid=sd.get('id',''); fase=sd.get('fase',''); asig=sd.get('asignatura',''); bloque=sd.get('bloque',''); conv=sd.get('convocatoria','')
        else: sid=s[0]; fase=s[2]; asig=s[3]; n1=s[4]; n2=s[5]; bloque=s[8] if len(s)>8 else ''; conv=s[6] if len(s)>6 else ''
        etiqueta = ""
        if n1 and not n2: etiqueta="<span class='badge bg-primary'>Fase 1</span>"
        elif n2 and not n1: etiqueta="<span class='badge bg-success'>Fase 2</span>"
        elif n1 and n2: etiqueta="<span class='badge bg-dark'>Fase 1 y 2</span>"
        _btn_borrar = f"<a href='/selectividad/{sid}/borrar' class='btn btn-sm btn-danger'>Borrar</a>" if _puede_editar_registro(d) else ""
        html_rows+=f"<tr><td><b>{fase}</b><br><small>{bloque}</small><br>{etiqueta}</td><td>{asig}<br><small>{conv}</small></td><td style='{nota_color(n1)}'><b>{n1}</b></td><td style='{nota_color(n2)}'><b>{n2}</b></td><td>{_btn_borrar}</td></tr>"
    if not html_rows: html_rows="<tr><td colspan=5>Sin datos</td></tr>"
    _form_sel = f"<hr><h5>Anadir Nota</h5><form method='post' action='/alumno/{id}/selectividad/add' class='row g-2'><div class='col-md-2'><select name='fase' id='faseSel' class='form-control' onchange='cambiar()'><option value='GENERAL'>Fase General</option><option value='ESPECIAL'>Fase Especial</option></select></div><div class='col-md-3'><select name='asignatura_bloque' id='asigSel' class='form-control'></select></div><div class='col-md-2'><select name='tipo_fase' class='form-control'><option value='FASE1'>Fase 1</option><option value='FASE2'>Fase 2</option><option value='AMBAS'>Ambas</option></select></div><div class='col-md-1'><input name='nota' class='form-control' placeholder='F1'></div><div class='col-md-1'><input name='nota2' class='form-control' placeholder='F2'></div><div class='col-md-3'><input name='convocatoria' class='form-control' value='Junio 2025'></div><div class='col-12'><button class='btn btn-dark'>Guardar</button></div></form>" if _puede_editar_registro(d) else ""
    page = f"<a href='/alumno/{id}' class='btn btn-secondary btn-sm'>Volver</a><h4 class='mt-3'>Selectividad - {d['nombre']} {d['apellidos']}</h4><div class='card p-3 mt-3'><table class='table table-bordered'><tr><th>Fase</th><th>Asignatura</th><th>Nota F1</th><th>Nota F2</th><th></th></tr>{html_rows}</table>{_form_sel}</div><script>const generalList=[\"Lengua Espanola\",\"Historia\",\"Historia de la Filosofia\",\"Idioma\"];const especialBloques={{\"BLOQUE 1\":[\"Historia de Africa y de G.E\",\"Literatura Universal\",\"Historia de Arte\",\"Geografia\",\"Matematicas Aplicadas a CS\",\"Latin\",\"Griego\"],\"BLOQUE 2\":[\"Matematicas\",\"Fisica\",\"Quimica\",\"Dibujo Tecnico\",\"Informatica\",\"Tecnologia Industrial\",\"Electrotecnia\"],\"BLOQUE 3\":[\"Biologia y Geologia\",\"C.N y Salud\",\"Fisica y Quimica\"]}};function cambiar(){{let fase=document.getElementById('faseSel').value;let sel=document.getElementById('asigSel');if(!sel) return;sel.innerHTML='';if(fase==='GENERAL'){{generalList.forEach(m=>{{let o=document.createElement('option');o.value=m;o.text=m;sel.add(o)}})}}else{{for(const [b,mats] of Object.entries(especialBloques)){{let g=document.createElement('optgroup');g.label=b;mats.forEach(m=>{{let o=document.createElement('option');o.value=m+'|'+b;o.text=m;g.appendChild(o)}});sel.appendChild(g)}}}}cambiar();</script>"
    return render_template_string(BASE, content=page)

@app.route('/alumno/<int:id>/selectividad/add', methods=['POST'])
def selectividad_add(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone(); d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[10],'centro_codigo':r[12]}
    if not _puede_editar_registro(d):
        try: cur.close(); conn.close()
        except: pass
        return render_template_string(BASE, content="<div class='alert alert-danger'>No tienes permiso para modificar este alumno.</div><a href='/alumnos' class='btn btn-secondary'>Volver</a>")
    fase_raw=request.form.get('fase') or 'GENERAL'; asig_bloque=request.form.get('asignatura_bloque') or ''; tipo_fase=request.form.get('tipo_fase') or 'FASE1'
    bloque=""; asignatura=asig_bloque
    if '|' in asig_bloque: asignatura,bloque=asig_bloque.split('|',1)
    fase_nombre="Fase General" if fase_raw=="GENERAL" else "Fase Especial"
    nota1=request.form.get('nota','').strip(); nota2=request.form.get('nota2','').strip()
    if tipo_fase=='FASE1': nf1,nf2=nota1 or nota2,""
    elif tipo_fase=='FASE2': nf1,nf2="",nota2 or nota1
    else: nf1,nf2=nota1,nota2
    cur.execute(adapt("INSERT INTO selectividad (alumno_codigo, fase, asignatura, nota, nota2, convocatoria, centro_codigo, bloque) VALUES (?,?,?,?,?,?,?,?)"), (d['codigo_alumno'], fase_nombre, asignatura, nf1, nf2, request.form.get('convocatoria'), d['centro_codigo'], bloque))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect(f'/alumno/{id}/selectividad')

@app.route('/selectividad/<int:sid>/borrar')
def selectividad_borrar(sid):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM selectividad WHERE id=?"), (sid,)); _sr=cur.fetchone()
    if _sr:
        _sd=dict(_sr) if isinstance(_sr,dict) else {'alumno_codigo':_sr[1]}
        cur.execute(adapt("SELECT * FROM alumnos WHERE codigo_alumno=?"), (_sd.get('alumno_codigo'),)); _ar=cur.fetchone()
        _ad=dict(_ar) if isinstance(_ar,dict) else {}
        if _ar and not _puede_editar_registro(_ad):
            try: cur.close(); conn.close()
            except: pass
            return render_template_string(BASE, content="<div class='alert alert-danger'>No tienes permiso para borrar esta nota.</div><a href='/alumnos' class='btn btn-secondary'>Volver</a>")
    cur.execute(adapt("DELETE FROM selectividad WHERE id=?"), (sid,)); conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect('/alumnos')

@app.route('/primaria')
def primaria_list():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM alumnos_primaria ORDER BY id DESC"); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html="<div class='d-flex justify-content-between'><h4>Primaria <a href='/primaria/nuevo' class='btn btn-sm btn-success'>+ Nuevo</a></h4><a href='/dashboard' class='btn btn-sm btn-secondary'>Menu Principal</a></div><table class='table table-hover'><tr><th>Codigo</th><th>Nombre</th><th>Accion</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[4]}
        _p_editar = f"<a href='/primaria/{d['id']}/editar' class='btn btn-sm btn-warning'>Editar</a>" if _puede_editar_registro(d) else ""
        _p_eliminar = f"<a href='/primaria/{d['id']}/eliminar' class='btn btn-sm btn-danger'>Eliminar</a>" if _puede_editar_registro(d) else ""
        html+=f"<tr><td><b>{d['codigo_alumno']}</b></td><td>{d['nombre']} {d['apellidos']}</td><td><a href='/primaria/{d['id']}' class='btn btn-sm btn-primary'>Ver</a> {_p_editar} {_p_eliminar}</td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)

@app.route('/primaria/nuevo', methods=['GET','POST'])
def primaria_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if request.method=='POST':
        f=request.form; codigo=f.get('codigo_alumno','').strip() or gen_codigo("PRI")
        foto_name, foto_data_b64 = _foto_desde_request(codigo)
        cc=session.get('centro_codigo') if session.get('rol')!='admin' else f.get('centro_codigo') or f.get('centro')
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,foto,codigo_alumno,centro,anio,centro_codigo,foto_data,curso,creado_por) VALUES (?,?,?,?,?,?,?,?,?,?)"), (f.get('nombre'),f.get('apellidos'),foto_name,codigo,f.get('centro'),f.get('anio'),cc,foto_data_b64,f.get('curso'),session.get('usuario')))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect('/primaria')
    return render_template_string(BASE, content="<a href='/primaria' class='btn btn-secondary btn-sm'>Volver</a><h4>Nuevo Primaria</h4><form method='post' enctype='multipart/form-data' class='row g-2'><div class='col-md-6'><input name='nombre' class='form-control' placeholder='Nombre' required></div><div class='col-md-6'><input name='apellidos' class='form-control' placeholder='Apellidos' required></div><div class='col-md-4'><input name='centro' class='form-control' placeholder='Centro'></div><div class='col-md-2'><select name='curso' class='form-control'><option>1 Primaria</option><option>2 Primaria</option><option>3 Primaria</option><option>4 Primaria</option><option>5 Primaria</option><option>6 Primaria</option></select></div><div class='col-md-2'><input name='anio' class='form-control' value='2026-2027'></div><div class='col-md-4'><input name='codigo_alumno' class='form-control' placeholder='Codigo'></div><div class='col-md-6'><input type='file' name='foto' accept='image/*' capture='camera' class='form-control'></div><div class='col-12'><button class='btn btn-success'>Guardar</button></div></form>")

@app.route('/primaria/<int:id>')
def primaria_ver(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[4],'centro':r[5],'curso':r[8] if len(r)>8 else 'Primaria','foto':r[3],'foto_data':r[7] if len(r)>7 else ''}
    cur.execute(adapt("SELECT * FROM notas_primaria WHERE alumno_codigo=? ORDER BY anio"), (d['codigo_alumno'],)); notas=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    foto_html=get_foto_html(d,150,200); qr=gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    notas_html=""
    for n in notas:
        nd=dict(n) if isinstance(n,dict) else {'anio':n[2],'datos':n[3]}
        try:
            datos=json.loads(nd.get('datos') or '{}'); notas_html+=f"<div class='card p-2 mb-2'><b>{nd.get('anio')}</b><table class='table table-sm'><tr><th>Materia</th><th>Nota</th></tr>"
            for m,v in datos.items(): notas_html+=f"<tr><td>{m}</td><td style='{nota_color(v)}'><b>{v}</b></td></tr>"
            notas_html+="</table></div>"
        except: pass
    if not notas_html: notas_html="<div class='alert alert-warning'>Sin notas de primaria</div>"
    options = "".join([f"<option>{a}</option>" for a in ANIOS_PRIMARIA])
    form = f"<div class='card p-3 mt-3'><h5>Añadir Notas Primaria</h5><form method='post' action='/primaria/{id}/notas/guardar'><select name='anio' class='form-control mb-2'>{options}</select><div id='matPrim'></div><button class='btn btn-success'>Guardar</button></form></div><script>const PLAN={json.dumps(PLAN)};function cargarPrim(){{let s=document.querySelector('select[name=anio]').value;let m=PLAN[s]||[];let h=\"<table class='table table-sm'><tr><th>Materia</th><th>Nota</th></tr>\";m.forEach(x=>{{h+=`<tr><td>${{x}}</td><td><input name='${{x}}' class='form-control form-control-sm'></td></tr>`}});h+=\"</table>\";document.getElementById('matPrim').innerHTML=h}}document.querySelector('select[name=anio]').addEventListener('change',cargarPrim);cargarPrim();</script>"
    _pv_editar = f"<a href='/primaria/{id}/editar' class='btn btn-warning btn-sm'>Editar</a>" if _puede_editar_registro(d) else ""
    _pv_eliminar = f"<a href='/primaria/{id}/eliminar' class='btn btn-danger btn-sm'>Eliminar</a>" if _puede_editar_registro(d) else ""
    return render_template_string(BASE, content=f"<a href='/primaria' class='btn btn-secondary btn-sm'>Volver</a>{_pv_editar}{_pv_eliminar}<div class='row mt-3'><div class='col-md-8'><h4>{d['nombre']} {d['apellidos']} ({d['codigo_alumno']})</h4>{notas_html}{form}</div><div class='col-md-4 text-center'>{foto_html}<br><br><img src='{qr}' style='width:180px'></div></div>")

@app.route('/primaria/<int:id>/notas/guardar', methods=['POST'])
def primaria_notas_guardar(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"), (id,)); r=cur.fetchone()
    d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[4],'centro_codigo':r[6] if len(r)>6 else ''}
    if not _puede_editar_registro(d):
        try: cur.close(); conn.close()
        except: pass
        return render_template_string(BASE, content="<div class='alert alert-danger'>No tienes permiso para modificar este alumno.</div><a href='/primaria' class='btn btn-secondary'>Volver</a>")
    anio=request.form.get('anio') or 'Primaria'; datos={}
    for k,v in request.form.items():
        if k!='anio' and v.strip(): datos[k]=v.strip()
    json_data=json.dumps(datos, ensure_ascii=False)
    cur.execute(adapt("SELECT * FROM notas_primaria WHERE alumno_codigo=? AND anio=?"), (d['codigo_alumno'], anio))
    existe=cur.fetchone()
    if existe: cur.execute(adapt("UPDATE notas_primaria SET datos=? WHERE alumno_codigo=? AND anio=?"), (json_data, d['codigo_alumno'], anio))
    else: cur.execute(adapt("INSERT INTO notas_primaria (alumno_codigo, anio, datos, centro_codigo) VALUES (?,?,?,?)"), (d['codigo_alumno'], anio, json_data, d['centro_codigo']))
    conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect(f'/primaria/{id}')

@app.route('/primaria/<int:id>/editar', methods=['GET','POST'])
def primaria_editar(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    _ddp = dict(r) if isinstance(r,dict) else {}
    if not _puede_editar_registro(_ddp):
        try: cur.close(); conn.close()
        except: pass
        return render_template_string(BASE, content="<div class='alert alert-danger'>No tienes permiso para editar este registro. Solo la Base de Datos Central puede editarlo, o el usuario que lo creo.</div><a href='/primaria' class='btn btn-secondary'>Volver</a>")
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[4],'centro':r[5],'foto':r[3],'foto_data':r[7] if len(r)>7 else ''}
    if request.method=='POST':
        f=request.form; foto_name=d.get('foto'); foto_data_b64=d.get('foto_data')
        _fn2, _fb2 = _foto_desde_request(d.get('codigo_alumno'))
        if _fn2: foto_name, foto_data_b64 = _fn2, _fb2
        cur.execute(adapt("UPDATE alumnos_primaria SET nombre=?, apellidos=?, centro=?, anio=?, foto=?, foto_data=? WHERE id=?"), (f.get('nombre'),f.get('apellidos'),f.get('centro'),f.get('anio'),foto_name,foto_data_b64,id))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect(f'/primaria/{id}')
    try: cur.close(); conn.close()
    except: pass
    return render_template_string(BASE, content=f"<a href='/primaria/{id}' class='btn btn-secondary btn-sm'>Volver</a><h4>Editar {d['codigo_alumno']}</h4><form method='post' enctype='multipart/form-data'><input name='nombre' value='{d.get('nombre','')}' class='form-control mb-2'><input name='apellidos' value='{d.get('apellidos','')}' class='form-control mb-2'><input name='centro' value='{d.get('centro','')}' class='form-control mb-2'><input name='anio' value='{d.get('anio','')}' class='form-control mb-2'><input type='file' name='foto' accept='image/*' capture='camera' class='form-control mb-2'><button class='btn btn-success'>Guardar</button></form>")

@app.route('/primaria/<int:id>/eliminar')
def primaria_eliminar(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE id=?"), (id,)); r=cur.fetchone()
    _ddpd = dict(r) if isinstance(r,dict) else {}
    if r and not _puede_editar_registro(_ddpd):
        try: cur.close(); conn.close()
        except: pass
        return render_template_string(BASE, content="<div class='alert alert-danger'>No tienes permiso para eliminar este registro. Solo la Base de Datos Central puede eliminarlo, o el usuario que lo creo.</div><a href='/primaria' class='btn btn-secondary'>Volver</a>")
    if r:
        d=dict(r) if isinstance(r,dict) else {'codigo_alumno':r[4]}
        cur.execute(adapt("DELETE FROM notas_primaria WHERE alumno_codigo=?"), (d['codigo_alumno'],))
        cur.execute(adapt("DELETE FROM alumnos_primaria WHERE id=?"), (id,))
        conn.commit()
    try: cur.close(); conn.close()
    except: pass
    return redirect('/primaria')

@app.route('/usuarios', methods=['GET','POST'])
def usuarios():
    if 'usuario' not in session: return redirect('/login')
    if session.get('rol') != 'admin':
        return render_template_string(BASE, content=f"<div class='alert alert-danger'>Solo admin - Tu rol: {session.get('rol','')}</div>")
    conn=get_conn(); cur=conn.cursor()
    if request.method=='POST':
        u=request.form.get('usuario'); p=request.form.get('password'); rol=request.form.get('rol'); cc=request.form.get('centro_codigo')
        try:
            cur.execute(adapt("INSERT INTO usuarios (usuario,password,rol,centro_codigo) VALUES (?,?,?,?)"), (u, generate_password_hash(p), rol, cc))
            conn.commit()
        except: pass
    cur.execute("SELECT * FROM usuarios ORDER BY id"); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html="<h4>Usuarios</h4><table class='table'><tr><th>Usuario</th><th>Rol</th><th>Centro</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'usuario':r[1],'rol':r[3],'centro_codigo':r[4]}
        html+=f"<tr><td>{d['usuario']}</td><td>{d['rol']}</td><td>{d['centro_codigo']}</td></tr>"
    html+="</table><hr><h5>Crear Usuario</h5><form method='post' class='row g-2'><div class='col-md-3'><input name='usuario' placeholder='Usuario' class='form-control' required></div><div class='col-md-3'><input name='password' placeholder='Password' class='form-control' required></div><div class='col-md-2'><select name='rol' class='form-control'><option value='admin'>admin</option><option value='centro'>centro</option></select></div><div class='col-md-2'><input name='centro_codigo' placeholder='Codigo centro' class='form-control'></div><div class='col-md-2'><button class='btn btn-dark'>Crear</button></div></form>"
    return render_template_string(BASE, content=html)

@app.route('/centros')
def centros():
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM centros ORDER BY id DESC"); rows=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    html="<h4>Centros</h4><table class='table'><tr><th>Nombre</th><th>Codigo</th></tr>"
    for r in rows:
        d=dict(r) if isinstance(r,dict) else {'nombre':r[1],'codigo':r[2]}
        html+=f"<tr><td>{d['nombre']}</td><td>{d['codigo']}</td></tr>"
    html+="</table>"
    return render_template_string(BASE, content=html)

@app.route('/centros/nuevo', methods=['GET','POST'])
def centro_nuevo():
    if 'usuario' not in session: return redirect('/login')
    if session.get('rol')!='admin': return render_template_string(BASE, content="<div class='alert alert-danger'>Solo admin</div>")
    if request.method=='POST':
        codigo=request.form.get('codigo') or gen_codigo("CEN")
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("INSERT INTO centros (nombre,codigo,localidad,contacto,email) VALUES (?,?,?,?,?)"), (request.form.get('nombre'),codigo,request.form.get('localidad'),request.form.get('contacto'),request.form.get('email')))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return redirect('/centros')
    return render_template_string(BASE, content="<h4>Nuevo Centro</h4><form method='post'><input name='nombre' placeholder='Nombre' class='form-control mb-2' required><input name='codigo' placeholder='Codigo' class='form-control mb-2'><input name='localidad' placeholder='Localidad' class='form-control mb-2'><input name='contacto' placeholder='Contacto' class='form-control mb-2'><input name='email' placeholder='Email' class='form-control mb-2'><button class='btn btn-warning'>Guardar</button></form>")

@app.route('/consulta', methods=['GET','POST'])
def consulta():
    codigo=(request.args.get('codigo') or request.form.get('codigo') or '').strip()
    nombre_busqueda=(request.args.get('nombre') or request.form.get('nombre') or request.args.get('nombre_completo') or request.form.get('nombre_completo') or '').strip()
    alumno=None; sel_data=[]; hist_rows=[]; old_rows=[]; is_primaria=False; lista_coincidencias=[]
    # MOD 3: busqueda por nombre completo, sin tildes ni mayusculas
    if nombre_busqueda and not codigo:
        _nb = _norm_txt(nombre_busqueda)
        conn=get_conn(); cur=conn.cursor()
        try:
            cur.execute("SELECT * FROM alumnos"); _todos=cur.fetchall()
            for _r in _todos:
                _d=dict(_r) if isinstance(_r,dict) else {}
                _full=_norm_txt(f"{_d.get('nombre','')} {_d.get('apellidos','')}")
                if _nb and (_nb in _full or _full in _nb or all(_w in _full for _w in _nb.split())):
                    lista_coincidencias.append((_d, False))
            if not lista_coincidencias:
                cur.execute("SELECT * FROM alumnos_primaria"); _todos2=cur.fetchall()
                for _r in _todos2:
                    _d=dict(_r) if isinstance(_r,dict) else {}
                    _full=_norm_txt(f"{_d.get('nombre','')} {_d.get('apellidos','')}")
                    if _nb and (_nb in _full or _full in _nb or all(_w in _full for _w in _nb.split())):
                        lista_coincidencias.append((_d, True))
            if len(lista_coincidencias)==1:
                alumno=lista_coincidencias[0][0]; is_primaria=lista_coincidencias[0][1]; lista_coincidencias=[]
                ad=alumno
                if not is_primaria:
                    cur.execute(adapt("SELECT * FROM notas_historico WHERE alumno_codigo=? ORDER BY anio_academico"), (ad['codigo_alumno'],)); hist_rows=cur.fetchall()
                    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=? ORDER BY curso"), (ad['codigo_alumno'],)); old_rows=cur.fetchall()
                    cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (ad['codigo_alumno'],)); sel_data=cur.fetchall()
                else:
                    cur.execute(adapt("SELECT * FROM notas_primaria WHERE alumno_codigo=? ORDER BY anio"), (ad['codigo_alumno'],)); hist_rows=cur.fetchall()
        except: pass
        finally:
            try: cur.close(); conn.close()
            except: pass
    if codigo:
        conn=get_conn(); cur=conn.cursor()
        cur.execute(adapt("SELECT * FROM alumnos WHERE codigo_alumno=?"), (codigo.strip(),)); alumno=cur.fetchone()
        if alumno:
            ad=dict(alumno) if isinstance(alumno,dict) else {'codigo_alumno':alumno[10]}
            cur.execute(adapt("SELECT * FROM notas_historico WHERE alumno_codigo=? ORDER BY anio_academico"), (ad['codigo_alumno'],)); hist_rows=cur.fetchall()
            cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=? ORDER BY curso"), (ad['codigo_alumno'],)); old_rows=cur.fetchall()
            cur.execute(adapt("SELECT * FROM selectividad WHERE alumno_codigo=? ORDER BY fase, bloque"), (ad['codigo_alumno'],)); sel_data=cur.fetchall()
        else:
            cur.execute(adapt("SELECT * FROM alumnos_primaria WHERE codigo_alumno=?"), (codigo.strip(),)); alumno=cur.fetchone()
            if alumno:
                is_primaria=True
                ad=dict(alumno) if isinstance(alumno,dict) else {'codigo_alumno':alumno[4]}
                cur.execute(adapt("SELECT * FROM notas_primaria WHERE alumno_codigo=? ORDER BY anio"), (ad['codigo_alumno'],)); hist_rows=cur.fetchall()
        try: cur.close(); conn.close()
        except: pass
    content=f"<h3 class='text-center'>Consulta Publica V28.14</h3><form method='post' class='d-flex justify-content-center gap-2 mt-3 flex-wrap'><input name='codigo' value='{codigo or ''}' placeholder='Codigo Alumno' class='form-control' style='max-width:300px'><input name='nombre' value='{nombre_busqueda or ''}' placeholder='O buscar por Nombre Completo (ej: Juan Ndong Mba)' class='form-control' style='max-width:350px'><button class='btn btn-primary'>Buscar</button></form><div class='text-center mt-2'><small class='text-muted'>Puedes buscar por codigo O por nombre completo.</small></div>"
    if lista_coincidencias:
        _lst = "".join([f"<tr><td>{_d.get('nombre','')} {_d.get('apellidos','')}</td><td>{_d.get('codigo_alumno','')}</td><td>{_d.get('centro','')}</td><td><a href='/consulta?codigo={_d.get('codigo_alumno','')}' class='btn btn-sm btn-primary'>Ver ficha completa</a></td></tr>" for _d,_ip in lista_coincidencias])
        content+=f"<div class='card p-3 mt-4'><h5>Se encontraron {len(lista_coincidencias)} alumnos con ese nombre:</h5><table class='table'><tr><th>Nombre Completo</th><th>Codigo</th><th>Centro</th><th></th></tr>{_lst}</table></div>"
    if (codigo or nombre_busqueda) and not alumno and not lista_coincidencias: content+=f"<div class='alert alert-danger mt-4 text-center'>No encontrado: {codigo or nombre_busqueda}</div>"
    if alumno:
        d=dict(alumno) if isinstance(alumno,dict) else {'nombre':alumno[1],'apellidos':alumno[2],'codigo_alumno':alumno[4] if is_primaria else alumno[10],'centro':alumno[5] if is_primaria else alumno[8], 'curso':alumno[8] if is_primaria and len(alumno)>8 else alumno[13] if len(alumno)>13 else '', 'foto':alumno[3] if is_primaria else alumno[11], 'foto_data':alumno[7] if is_primaria else alumno[15] if len(alumno)>15 else ''}
        foto_html = get_foto_html(d, 220, 270); qr_img = gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d.get('codigo_alumno')}")
        # MOD 4: mostrar TODA la info registrada
        html_datos = f"<div class='text-center mb-4'><b>Foto carnet</b><div class='mt-2'>{foto_html}</div></div><div class='text-center mb-4'><b>Codigo QR</b><div class='mt-2'><img src='{qr_img}' style='width:200px'></div><small>{d.get('codigo_alumno')}</small></div><div class='card p-3 bg-light'><b>Nombre Completo:</b> {d.get('nombre')} {d.get('apellidos')}<br><b>Codigo:</b> {d.get('codigo_alumno')}<br><b>Lugar de Nacimiento:</b> {d.get('lugar_nacimiento','')}<br><b>Distrito:</b> {d.get('distrito','')} | <b>Provincia:</b> {d.get('provincia','')}<br><b>Telefono / Contacto:</b> {d.get('telefono','')}<br><b>Email:</b> {d.get('email','')}<br><b>Centro:</b> {d.get('centro')} | <b>Curso:</b> {d.get('curso')} | <b>Ano Academico:</b> {d.get('anio','')}<br><b>Codigo Centro:</b> {d.get('centro_codigo','')}<br><b>Observaciones:</b> {d.get('observaciones','')}<br><b>Registrado por:</b> {d.get('creado_por','Base Central')}</div>"
        html_notas=""
        all_hist = hist_rows if hist_rows else old_rows
        for hr in all_hist:
            h=dict(hr) if isinstance(hr,dict) else {'anio_academico':hr[2] if len(hr)>2 else '', 'curso':hr[2] if len(hr)>2 else '', 'datos':hr[3] if len(hr)>3 else hr[2], 'anio':hr[2] if len(hr)>2 else ''}
            try:
                datos=json.loads(h.get('datos') or '{}')
                if not datos: continue
                titulo = h.get('anio_academico') or h.get('curso') or h.get('anio') or 'Notas'
                html_notas+=f"<h5 class='mt-4'>{titulo}</h5><table class='table table-bordered'><tr><th>Materia</th><th>1er</th><th>2do</th><th>3er</th><th>Junio</th></tr>"
                for mat,vals in datos.items():
                    def st(v):
                        try:
                            if not v: return ""
                            return "color:red;font-weight:bold;background:#ffe0e0" if float(str(v).replace(',','.'))<5 else "color:green;font-weight:bold"
                        except: return ""
                    if isinstance(vals, dict):
                        html_notas+=f"<tr><td>{mat}</td><td style='{st(vals.get('T1',''))}'>{vals.get('T1','')}</td><td style='{st(vals.get('T2',''))}'>{vals.get('T2','')}</td><td style='{st(vals.get('T3',''))}'>{vals.get('T3','')}</td><td style='{st(vals.get('JUN',''))}'><b>{vals.get('JUN','')}</b></td></tr>"
                    else:
                        html_notas+=f"<tr><td>{mat}</td><td colspan=4><b>{vals}</b></td></tr>"
                html_notas+="</table>"
            except: pass
        if sel_data:
            html_notas+="<h5 class='mt-4'>SELECTIVIDAD</h5><table class='table table-bordered'><tr><th>Fase</th><th>Bloque</th><th>Asignatura</th><th>F1</th><th>F2</th></tr>"
            for s in sel_data:
                sd=dict(s) if isinstance(s,dict) else {}
                if sd: n1=sd.get('nota',''); n2=sd.get('nota2',''); fase=sd.get('fase',''); asig=sd.get('asignatura',''); bloque=sd.get('bloque','')
                else: n1=s[4] if len(s)>4 else ''; n2=s[5] if len(s)>5 else ''; fase=s[2] if len(s)>2 else ''; asig=s[3] if len(s)>3 else ''; bloque=s[8] if len(s)>8 else ''
                html_notas+=f"<tr><td>{fase}</td><td>{bloque}</td><td>{asig}</td><td style='{nota_color(n1)}'><b>{n1}</b></td><td style='{nota_color(n2)}'><b>{n2}</b></td></tr>"
            html_notas+="</table>"
        # En consulta publica no hay id de sesion, usar codigo para hoja academica
        content+=f"<div class='card p-4 mt-4 shadow'>{html_datos}<hr>{html_notas}<div class='text-center mt-4'><button onclick='window.print()' class='btn btn-primary'>Imprimir</button></div></div>"
    return render_template_string(BASE, content=content)

@app.route('/alumno/<int:id>/hoja_academica')
def hoja_academica(id):
    if 'usuario' not in session: return redirect('/login')
    conn=get_conn(); cur=conn.cursor()
    cur.execute(adapt("SELECT * FROM alumnos WHERE id=?"), (id,)); r=cur.fetchone()
    if not r: return "No encontrado",404
    d=dict(r) if isinstance(r,dict) else {'id':r[0],'nombre':r[1],'apellidos':r[2],'codigo_alumno':r[10],'centro':r[8],'curso':r[13] if len(r)>13 else '','lugar_nacimiento':r[3],'distrito':r[4],'provincia':r[5],'anio':r[9],'foto':r[11],'foto_data':r[15] if len(r)>15 else ''}
    cur.execute(adapt("SELECT * FROM notas_historico WHERE alumno_codigo=?"), (d['codigo_alumno'],)); hist=cur.fetchall()
    cur.execute(adapt("SELECT * FROM notas_trimestres WHERE alumno_codigo=?"), (d['codigo_alumno'],)); old=cur.fetchall()
    try: cur.close(); conn.close()
    except: pass
    notas_map={}
    for hr in list(hist)+list(old):
        h=dict(hr) if isinstance(hr,dict) else {'anio_academico':hr[2],'curso':hr[3],'datos':hr[4],'anio':hr[2]}
        try:
            datos=json.loads(h.get('datos') or '{}')
            key=h.get('anio_academico') or h.get('curso') or h.get('anio') or ''
            if key not in notas_map: notas_map[key]={}
            for mat, vals in datos.items():
                nota_final = vals.get('JUN') or vals.get('T3') or vals.get('T2') or vals.get('T1') or vals if isinstance(vals,dict) else str(vals)
                notas_map[key][mat]=nota_final
                notas_map[key][mat.lower()]=nota_final
        except: pass
    def get_n(curso, mat_busca):
        if curso not in notas_map: return ""
        for k,v in notas_map[curso].items():
            if mat_busca.lower() in k.lower() or k.lower() in mat_busca.lower():
                return v
        return ""
    foto_html = get_foto_html(d, 95, 115)
    qr = gen_qr(f"https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}")
    html = f"""
    <html><head><meta charset='utf-8'><title>HOJA {d['codigo_alumno']}</title>
    <style>
    @page {{ size: A4 portrait; margin: 6mm; }}
    body {{ font-family: Arial; font-size: 8px; margin:0; color:#000; }}
    .borde {{ border:2px solid #000; padding:6px; }}
    .header {{ display:flex; justify-content:space-between; align-items:flex-start; }}
    .escudo {{ width:65px; text-align:center; font-size:7px; border:1px solid #000; padding:2px; }}
    table {{ width:100%; border-collapse:collapse; margin-bottom:4px; }}
    td,th {{ border:1px solid #000; padding:2px; text-align:center; height:13px; }}
    .mat {{ text-align:left; padding-left:3px; font-size:7.5px; }}
    .curso-titulo {{ background:#000; color:#fff; font-weight:bold; text-align:center; font-size:8px; padding:2px; }}
    .ao-lateral {{ writing-mode: vertical-rl; background:#d9d9d9; font-weight:bold; width:18px; text-align:center; font-size:8px; }}
    .rama-titulo {{ background:#fff; color:#c00000; font-weight:bold; font-size:8px; text-align:center; border:1px solid #000; padding:2px; margin-top:5px; }}
    .foto-box {{ border:1px solid #000; width:100px; height:120px; text-align:center; }}
    .no-print {{ text-align:center; padding:8px; background:#f0f0f0; }}
    @media print {{ .no-print {{ display:none; }} }}
    </style></head><body>
    <div class='no-print'><button onclick='window.print()' style='background:#0d6efd;color:#fff;padding:10px 20px;border:none;border-radius:6px;'>IMPRIMIR / GUARDAR PDF VERTICAL</button> <a href='/alumno/{id}' style='background:gray;color:#fff;padding:10px;text-decoration:none;border-radius:6px;'>Volver</a></div>
    <div class='borde'>
        <div class='header'>
            <div style='display:flex; gap:8px; align-items:center;'>
                <div class='escudo'>PAZ<br>JUSTICIA</div>
                <div>
                    <div style='font-weight:bold; font-size:9px;'>REPUBLICA DE GUINEA ECUATORIAL<br>MINISTERIO DE EDUCACION, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL</div>
                    <div style='font-size:14px; font-weight:bold; margin:2px 0; text-transform:uppercase;'>{d['nombre']} {d['apellidos']}</div>
                    <div style='font-size:8px;'>NATURAL DE {d.get('lugar_nacimiento','')}, DEL DISTRITO DE {d.get('distrito','')}, PROVINCIA DE {d.get('provincia','')}</div>
                    <div style='font-size:9px; font-weight:bold; margin-top:2px;'>HOJA ACADEMICA &nbsp; IPES "{d.get('centro','PADRE SANTY-BATA.')}" &nbsp; AÑO ESCOLAR {d.get('anio','')}</div>
                </div>
            </div>
            <div class='foto-box'>FOTO<br>{foto_html}</div>
        </div>
        <div style='display:flex; gap:6px; margin-top:6px;'>
            <div style='width:50%;'>
                <table><tr><td class='ao-lateral' rowspan=10>1 ESBA<br>CURSO......</td><td class='curso-titulo' colspan=2>1 ESBA</td></tr>
                    <tr><td class='mat'>Lengua Española y Lit</td><td><b>{get_n('1 ESBA','Lengua Española')}</b></td></tr>
                    <tr><td class='mat'>Matemáticas</td><td><b>{get_n('1 ESBA','Matemáticas')}</b></td></tr>
                    <tr><td class='mat'>Geografía Gra. Y de GE</td><td><b>{get_n('1 ESBA','Geografía')}</b></td></tr>
                    <tr><td class='mat'>Ciencias Naturales I</td><td><b>{get_n('1 ESBA','Ciencias Naturales')}</b></td></tr>
                    <tr><td class='mat'>E. Plástica y Visual I</td><td><b>{get_n('1 ESBA','Plástica')}</b></td></tr>
                    <tr><td class='mat'>Religión</td><td><b>{get_n('1 ESBA','Religión')}</b></td></tr>
                    <tr><td class='mat'>Francés</td><td><b>{get_n('1 ESBA','Francés')}</b></td></tr>
                    <tr><td class='mat'>Inglés</td><td><b>{get_n('1 ESBA','Inglés')}</b></td></tr>
                    <tr><td class='mat'>E. Física</td><td><b>{get_n('1 ESBA','Física')}</b></td></tr>
                </table>
                <table><tr><td class='ao-lateral' rowspan=9>2 ESBA</td><td class='curso-titulo' colspan=2>2 ESBA</td></tr>
                    <tr><td class='mat'>Lengua Española y Lit</td><td><b>{get_n('2 ESBA','Lengua Española')}</b></td></tr>
                    <tr><td class='mat'>Matemáticas</td><td><b>{get_n('2 ESBA','Matemáticas')}</b></td></tr>
                    <tr><td class='mat'>Biología y Geología</td><td><b>{get_n('2 ESBA','Biología')}</b></td></tr>
                    <tr><td class='mat'>Tecnología</td><td><b>{get_n('2 ESBA','Tecnología')}</b></td></tr>
                    <tr><td class='mat'>E. Plástica y Artística I</td><td><b>{get_n('2 ESBA','Plástica')}</b></td></tr>
                    <tr><td class='mat'>Física y Química</td><td><b>{get_n('2 ESBA','Física')}</b></td></tr>
                    <tr><td class='mat'>Religión / Francés</td><td><b>{get_n('2 ESBA','Religión')}</b></td></tr>
                    <tr><td class='mat'>Inglés / E. Física</td><td><b>{get_n('2 ESBA','Inglés')}</b></td></tr>
                </table>
                <table><tr><td class='ao-lateral' rowspan=12>4 ESBA<br>CURSO......</td><td class='curso-titulo' colspan=2>4 ESBA</td></tr>
                    <tr><td class='mat'>Lengua Española y Lit</td><td><b>{get_n('4 ESBA','Lengua Española')}</b></td></tr>
                    <tr><td class='mat'>Matemáticas</td><td><b>{get_n('4 ESBA','Matemáticas')}</b></td></tr>
                    <tr><td class='mat'>H. Universal</td><td><b>{get_n('4 ESBA','Universal')}</b></td></tr>
                    <tr><td class='mat'>Física y Química</td><td><b>{get_n('4 ESBA','Física')}</b></td></tr>
                    <tr><td class='mat'>Tecnología / Biología</td><td><b>{get_n('4 ESBA','Biología')}</b></td></tr>
                    <tr><td class='mat'>Biología y Geología</td><td><b>{get_n('4 ESBA','Biología')}</b></td></tr>
                    <tr><td class='mat'>E. Plástica y Artística</td><td><b>{get_n('4 ESBA','Plástica')}</b></td></tr>
                    <tr><td class='mat'>Religión</td><td><b>{get_n('4 ESBA','Religión')}</b></td></tr>
                    <tr><td class='mat'>Inglés</td><td><b>{get_n('4 ESBA','Inglés')}</b></td></tr>
                    <tr><td class='mat'>Inglés</td><td><b>{get_n('4 ESBA','Inglés')}</b></td></tr>
                    <tr><td class='mat'>E. Física</td><td><b>{get_n('4 ESBA','Física')}</b></td></tr>
                </table>
            </div>
            <div style='width:50%;'>
                <div style='border:1px dashed #000; padding:2px; text-align:center; font-size:7px; margin-bottom:4px;'>CURSO........ <b>1 BACH</b></div>
                <table>
                    <tr><td class='curso-titulo'>Asignatura</td><td class='curso-titulo' style='width:50px;'>Nota</td></tr>
                    <tr><td class='mat'>Lengua Española</td><td><b>{get_n('1 BACH - Ciencias','Lengua Española') or get_n('1 BACH','Lengua Española')}</b></td></tr>
                    <tr><td class='mat'>H. de África y de G.E.</td><td><b>{get_n('1 BACH','África')}</b></td></tr>
                    <tr><td class='mat'>Educación Física</td><td><b>{get_n('1 BACH','Física')}</b></td></tr>
                    <tr><td class='mat'>Religión / Francés</td><td><b>{get_n('1 BACH','Religión')}</b></td></tr>
                    <tr><td class='mat'>Inglés</td><td><b>{get_n('1 BACH','Inglés')}</b></td></tr>
                    <tr><td class='mat'>CC. De la Tierra y M.</td><td><b>{get_n('1 BACH','Tierra')}</b></td></tr>
                    <tr><td class='mat'>Biología</td><td><b>{get_n('1 BACH - Ciencias','Biología')}</b></td></tr>
                    <tr><td class='mat'>Matemática I</td><td><b>{get_n('1 BACH - Ciencias','Matemáticas I') or get_n('1 BACH','Matemáticas I')}</b></td></tr>
                </table>
                <div class='rama-titulo'>RAMA DE CIENCIA DE LA NATURALEZA Y SALUD</div>
                <table>
                    <tr><td class='mat'>Matemática I</td><td><b>{get_n('1 BACH','Matemática I')}</b></td></tr>
                    <tr><td class='mat'>Física y Química</td><td><b>{get_n('1 BACH','Física')}</b></td></tr>
                    <tr><td class='mat'>Dibujo Técnico I</td><td><b>{get_n('1 BACH','Dibujo')}</b></td></tr>
                    <tr><td class='mat'>Biología</td><td><b>{get_n('1 BACH','Biología')}</b></td></tr>
                </table>
                <div class='rama-titulo'>RAMA DE CIENCIAS SOCIALES Y HUMANIDADES</div>
                <table>
                    <tr><td class='mat'>Latín</td><td><b>{get_n('1 BACH - Letras','Latín') or get_n('1 BACH','Latín')}</b></td></tr>
                    <tr><td class='mat'>Griego</td><td><b>{get_n('1 BACH','Griego')}</b></td></tr>
                    <tr><td class='mat'>Geografía de G. Espa. Mund.</td><td><b>{get_n('1 BACH','Geografía')}</b></td></tr>
                    <tr><td class='mat'>Matemáticas Aplic. ACC.</td><td><b>{get_n('1 BACH','Matemáticas')}</b></td></tr>
                </table>
                <div style='border:1px dashed #000; padding:2px; text-align:center; font-size:7px; margin:6px 0;'>CURSO........ <b>2 BACH</b></div>
                <table>
                    <tr><td class='mat'>Literatura</td><td><b>{get_n('2 BACH','Literatura')}</b></td></tr>
                    <tr><td class='mat'>Historia del Mundo Actual</td><td><b>{get_n('2 BACH','Mundo Actual')}</b></td></tr>
                    <tr><td class='mat'>Historia de la Filosofía</td><td><b>{get_n('2 BACH','Filosofía')}</b></td></tr>
                    <tr><td class='mat'>Ciencia de la Naturaleza y Salud</td><td><b>{get_n('2 BACH','Naturaleza')}</b></td></tr>
                    <tr><td class='mat'>Economía de la Empresa</td><td><b>{get_n('2 BACH','Economía')}</b></td></tr>
                    <tr><td class='mat'>Religión</td><td><b>{get_n('2 BACH','Religión')}</b></td></tr>
                    <tr><td class='mat'>Francés</td><td><b>{get_n('2 BACH','Francés')}</b></td></tr>
                    <tr><td class='mat'>Inglés</td><td><b>{get_n('2 BACH','Inglés')}</b></td></tr>
                </table>
                <div class='rama-titulo'>RAMA DE CIENCIA DE LA NATURALEZA Y SALUD</div>
                <table>
                    <tr><td class='mat'>Matemáticas II</td><td><b>{get_n('2 BACH - Ciencias','Matemáticas II')}</b></td></tr>
                    <tr><td class='mat'>Electrotecnia</td><td><b>{get_n('2 BACH','Electrotecnia')}</b></td></tr>
                    <tr><td class='mat'>Química</td><td><b>{get_n('2 BACH - Ciencias','Química')}</b></td></tr>
                    <tr><td class='mat'>Geografía</td><td><b>{get_n('2 BACH','Geografía')}</b></td></tr>
                </table>
                <div class='rama-titulo'>RAMA DE TECNOLOGÍA</div>
                <table>
                    <tr><td class='mat'>Tecnología Industrial</td><td><b>{get_n('2 BACH','Tecnología')}</b></td></tr>
                    <tr><td class='mat'>Matemáticas II</td><td><b>{get_n('2 BACH','Matemáticas II')}</b></td></tr>
                    <tr><td class='mat'>Electrotecnia</td><td><b>{get_n('2 BACH','Electrotecnia')}</b></td></tr>
                    <tr><td class='mat'>Dibujo Técnico</td><td><b>{get_n('2 BACH','Dibujo')}</b></td></tr>
                </table>
                <div class='rama-titulo'>RAMA DE HUMANIDADES Y CIENCIAS SOCIALES</div>
                <table>
                    <tr><td class='mat'>Matemáticas Apl. A las C.S. II</td><td><b>{get_n('2 BACH - Letras','Matemáticas')}</b></td></tr>
                    <tr><td class='mat'>Historia de Arte</td><td><b>{get_n('2 BACH - Letras','Arte')}</b></td></tr>
                    <tr><td class='mat'>Latín</td><td><b>{get_n('2 BACH - Letras','Latín')}</b></td></tr>
                    <tr><td class='mat'>Griego</td><td><b>{get_n('2 BACH - Letras','Griego')}</b></td></tr>
                </table>
            </div>
        </div>
        <div style='display:flex; justify-content:space-between; align-items:flex-end; margin-top:6px; border-top:1px solid #000; padding-top:4px;'>
            <div style='display:flex; gap:6px; align-items:center;'>
                <img src='{qr}' style='width:75px; height:75px;'>
                <div style='font-size:6.5px; width:320px; text-align:justify; color:#c00000;'>
                Cualquiera que intente falsificar o duplicar este documento académico, estará incurriendo en un delito de "de falsificación". Los antecedentes de ésta Hoja Académica, están registrados en una base de Datos Nacional de Guinea Ecuatorial.<br>
                Verificación: https://ceacge-final.onrender.com/consulta?codigo={d['codigo_alumno']}
                </div>
            </div>
            <div style='font-size:8px; font-weight:bold;'>COD: CEA-001-AA &nbsp; {d['codigo_alumno']}</div>
        </div>
    </div>
    </body></html>
    """
    return html

# MOD 2: Endpoint para APK - registro con foto (archivo 'foto' o base64 'foto_base64')
@app.route('/api/apk/registro', methods=['POST'])
def api_apk_registro():
    try:
        data = request.form if request.form else {}
        if request.is_json:
            try: data = request.get_json() or {}
            except: data = {}
        def _g(k): return (data.get(k) or request.form.get(k) or '') if hasattr(data,'get') else ''
        tipo = (_g('tipo') or 'sec').lower()
        codigo = (_g('codigo_alumno') or '').strip() or gen_codigo("PRI" if tipo.startswith('pri') else "SEC")
        foto_name, foto_b64 = _foto_desde_request(codigo)
        if not foto_name and isinstance(data, dict) and data.get('foto_base64'):
            try:
                _b64 = str(data.get('foto_base64'))
                if ',' in _b64: _b64 = _b64.split(',',1)[1]
                _b = base64.b64decode(_b64); foto_name, foto_b64 = _guardar_foto_bytes(_b, codigo, 'foto_apk.jpg')
            except: pass
        conn=get_conn(); cur=conn.cursor()
        creador = session.get('usuario') or _g('usuario') or _g('creado_por') or 'apk'
        cc = session.get('centro_codigo') or _g('centro_codigo') or _g('centro')
        if tipo.startswith('pri'):
            cur.execute(adapt("INSERT INTO alumnos_primaria (nombre,apellidos,foto,codigo_alumno,centro,anio,centro_codigo,foto_data,curso,creado_por) VALUES (?,?,?,?,?,?,?,?,?,?)"), (_g('nombre'),_g('apellidos'),foto_name,codigo,_g('centro'),_g('anio') or '2026-2027',cc,foto_b64,_g('curso'),creador))
        else:
            cur.execute(adapt("INSERT INTO alumnos (nombre,apellidos,lugar_nacimiento,distrito,provincia,telefono,email,centro,anio,codigo_alumno,foto,centro_codigo,curso,observaciones,foto_data,creado_por) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"), (_g('nombre'),_g('apellidos'),_g('lugar_nacimiento'),_g('distrito'),_g('provincia'),_g('telefono'),_g('email'),_g('centro'),_g('anio') or '2026-2027',codigo,foto_name,cc,_g('curso'),_g('observaciones'),foto_b64,creador))
        conn.commit()
        try: cur.close(); conn.close()
        except: pass
        return {"ok": True, "codigo_alumno": codigo, "foto": bool(foto_name)}, 200
    except Exception as e:
        return {"ok": False, "error": str(e)}, 400

@app.route('/fotos/<path:filename>')
def fotos(filename):
    try: return send_from_directory(UPLOAD_FOLDER, filename)
    except: return "Foto no encontrada", 404

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
