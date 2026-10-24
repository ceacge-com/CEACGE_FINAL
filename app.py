# ... PEGO SOLO LA RUTA NUEVA CORREGIDA - REEMPLAZA LA RUTA ANTERIOR hoja_academica ...

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
            import json
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
    .año-lateral {{ writing-mode: vertical-rl; background:#d9d9d9; font-weight:bold; width:18px; text-align:center; font-size:8px; }}
    .rama-titulo {{ background:#fff; color:#c00000; font-weight:bold; font-size:8px; text-align:center; border:1px solid #000; padding:2px; margin-top:5px; }}
    .foto-box {{ border:1px solid #000; width:100px; height:120px; text-align:center; }}
    .no-print {{ text-align:center; padding:8px; background:#f0f0f0; }}
    @media print {{ .no-print {{ display:none; }} }}
    </style></head><body>
    <div class='no-print'><button onclick='window.print()' style='background:#0d6efd;color:#fff;padding:10px 20px;border:none;border-radius:6px;'>🖨️ IMPRIMIR / GUARDAR PDF VERTICAL</button> <a href='/alumno/{id}' style='background:gray;color:#fff;padding:10px;text-decoration:none;border-radius:6px;'>Volver</a></div>
    <div class='borde'>
        <div class='header'>
            <div style='display:flex; gap:8px; align-items:center;'>
                <div class='escudo'>🌳<br>PAZ<br>JUSTICIA</div>
                <div>
                    <div style='font-weight:bold; font-size:9px;'>REPUBLICA DE GUINEA ECUATORIAL<br>MINISTERIO DE EDUCACION, CIENCIA, ENSEÑANZA UNIVERSITARIA Y PROFESIONAL</div>
                    <div style='font-size:14px; font-weight:bold; margin:2px 0; text-transform:uppercase;'>{d['nombre']} {d['apellidos']}</div>
                    <div style='font-size:8px;'>NATURAL DE {d.get('lugar_nacimiento','')}, DEL DISTRITO DE {d.get('distrito','')}, PROVINCIA DE {d.get('provincia','')}</div>
                    <div style='font-size:9px; font-weight:bold; margin-top:2px;'>HOJA ACADÉMICA &nbsp; IPES "{d.get('centro','PADRE SANTY—BATA.')}" &nbsp; AÑO ESCOLAR {d.get('anio','')}</div>
                </div>
            </div>
            <div class='foto-box'>FOTO<br>{foto_html}</div>
        </div>

        <div style='display:flex; gap:6px; margin-top:6px;'>
            <!-- COLUMNA IZQUIERDA ESBA -->
            <div style='width:50%;'>
                <table><tr><td class='año-lateral' rowspan=10>1 ESBA<br>AÑO ESCOLAR<br>CURSO......</td><td class='curso-titulo' colspan=2>1 ESBA</td></tr>
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
                <table><tr><td class='año-lateral' rowspan=10>1 ESBA<br>CURSO......</td><td class='curso-titulo' colspan=2>1 ESBA - Repetición</td></tr>
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
                <table><tr><td class='año-lateral' rowspan=9>2 ESBA</td><td class='curso-titulo' colspan=2>2 ESBA</td></tr>
                    <tr><td class='mat'>Lengua Española y Lit</td><td><b>{get_n('2 ESBA','Lengua Española')}</b></td></tr>
                    <tr><td class='mat'>Matemáticas</td><td><b>{get_n('2 ESBA','Matemáticas')}</b></td></tr>
                    <tr><td class='mat'>Biología y Geología</td><td><b>{get_n('2 ESBA','Biología')}</b></td></tr>
                    <tr><td class='mat'>Tecnología</td><td><b>{get_n('2 ESBA','Tecnología')}</b></td></tr>
                    <tr><td class='mat'>E. Plástica y Artística I</td><td><b>{get_n('2 ESBA','Plástica')}</b></td></tr>
                    <tr><td class='mat'>Física y Química</td><td><b>{get_n('2 ESBA','Física')}</b></td></tr>
                    <tr><td class='mat'>Religión / Francés</td><td><b>{get_n('2 ESBA','Religión')}</b></td></tr>
                    <tr><td class='mat'>Inglés / E. Física</td><td><b>{get_n('2 ESBA','Inglés')}</b></td></tr>
                </table>
                <table><tr><td class='año-lateral' rowspan=12>4 ESBA<br>CURSO......</td><td class='curso-titulo' colspan=2>4 ESBA</td></tr>
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

            <!-- COLUMNA DERECHA BACH -->
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
