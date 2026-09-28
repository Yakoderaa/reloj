from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.87.0"' not in s:
    raise SystemExit("V0.88 requiere la base V0.87 aplicada")
s=s.replace('APP_VERSION="0.87.0"','APP_VERSION="0.88.0"',1)
s=s.replace('V0.87','V0.88')

# Add a live-data raster builder next to the exact approved reference loader.
needle='''            def build_exact_reference_customize():
                # Exact approved reference, cropped to the physical 240x296 display.
                # UtraWatch CUSTOMIZE cBinFile:
                # 10-byte config + 240*296 BGR565 pixels.
'''
idx=s.index(needle)
fn_end=s.index("            def build(dev_type",idx)
existing=s[idx:fn_end]
if "build_live_customize" in existing:
    raise SystemExit("V0.88: helper ya existe")

helper=r'''
            def build_live_customize(base_raw,battery_percent=None):
                # CUSTOMIZE supports three live firmware fields:
                # time_pos plus one field above and one below the time.
                # UtraWatch exposes: date=1, sleep=2, heart=4, steps=8.
                # Use time at the top, steps above it and heart rate below it.
                raw=bytearray(base_raw)
                if len(raw)!=142090 or raw[5]!=2:
                    raise RuntimeError("Base CUSTOMIZE V0.88 inválida")

                # Live metadata. Target orange sampled from the approved design:
                # RGB ~= (239,83,64) -> BGR565 0x429D -> little-endian 9d42.
                raw[0]=0       # time at top
                raw[1]=8       # live steps
                raw[2]=4       # live heart rate
                raw[3]=0x9D
                raw[4]=0x42
                raw[5]=2

                w=240;h=296;pix0=10
                def setpix(x,y,v=0):
                    if 0<=x<w and 0<=y<h:
                        off=pix0+((y*w+x)*2)
                        raw[off]=(v>>8)&255
                        raw[off+1]=v&255

                # Remove the four baked sample-value areas from the approved raster.
                # Keep the central analog artwork untouched for visual continuity.
                for x0,y0,x1,y1 in [
                    (5,15,102,68),      # old 10:09
                    (174,13,238,66),    # old 87%
                    (3,235,120,294),    # old 8,426 pasos
                    (143,235,239,294),  # old 72 lpm
                ]:
                    for yy in range(y0,y1):
                        for xx in range(x0,x1):
                            setpix(xx,yy,0)

                # Battery is not an official live CUSTOMIZE complication.
                # Render the battery value read from DEV_SYNC at install time.
                font={
                    "0":["01110","10001","10011","10101","11001","10001","01110"],
                    "1":["00100","01100","00100","00100","00100","00100","01110"],
                    "2":["01110","10001","00001","00010","00100","01000","11111"],
                    "3":["11110","00001","00001","01110","00001","00001","11110"],
                    "4":["00010","00110","01010","10010","11111","00010","00010"],
                    "5":["11111","10000","10000","11110","00001","00001","11110"],
                    "6":["01110","10000","10000","11110","10001","10001","01110"],
                    "7":["11111","00001","00010","00100","01000","01000","01000"],
                    "8":["01110","10001","10001","01110","10001","10001","01110"],
                    "9":["01110","10001","10001","01111","00001","00001","01110"],
                    "%":["10001","00010","00100","01000","10001","00000","00000"],
                    "-":["00000","00000","11111","00000","00000","00000","00000"],
                }
                def text5(txt,x,y,scale=2,color=0x429D):
                    for ch in txt:
                        pat=font.get(ch,font["-"])
                        for ry,row in enumerate(pat):
                            for rx,on in enumerate(row):
                                if on=="1":
                                    for sy in range(scale):
                                        for sx in range(scale):
                                            setpix(x+rx*scale+sx,y+ry*scale+sy,color)
                        x+=6*scale

                battery_text=(str(int(battery_percent))+"%") if battery_percent is not None else "--%"
                # Right-align in the same upper-right area as the approved design.
                x=max(174,236-len(battery_text)*12)
                text5(battery_text,x,27,2,0x429D)

                return bytes(raw),battery_text
'''
s=s[:fn_end]+helper+s[fn_end:]

old_prep='''                emit("1/9 · Cargando referencia APROBADA exacta 240×296 + paquete OEM…")
                path,raw,target_w,target_h=await asyncio.to_thread(build_exact_reference_customize)
                oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                expected_cmd2=raw[:6].hex()
                rep["single_face_install"]["candidate"]={
                    "path":path,
                    "format":"UtraWatch CUSTOMIZE cBinFile · referencia aprobada",
                    "visual_mode":"exact approved reference raster",
                    "target_source":"approved target image",
                    "width":target_w,"height":target_h,
                    "picture_mode":2,
                    "firmware_time_color":"black / hidden",
                    "dynamic_fields":False,
                    "sample_values_baked_into_reference":{
                        "time":"10:09","battery":"87%","steps":"8,426 pasos","heart_rate":"72 lpm"
                    },
                    "raw_size":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "raw_header_hex":raw[:10].hex(),
                    "expected_cmd2_hex":expected_cmd2,
                    "oem_stream_size":len(oem_stream),"deflate_size":len(deflated),
                    "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                    "oem_crc16":f"0x{crc16_8005(deflated):04X}",
                    "oem_header_hex":oem_stream[:20].hex()
                }

'''
new_prep='''                emit("1/9 · Cargando diseño aprobado 240×296; los datos se vincularán al reloj tras DEV_SYNC…")
                path,raw,target_w,target_h=await asyncio.to_thread(build_exact_reference_customize)
                expected_cmd2=None
                oem_stream=None
                deflated=None
                rep["single_face_install"]["candidate"]={
                    "path":path,
                    "format":"UtraWatch CUSTOMIZE cBinFile · referencia aprobada + datos vivos",
                    "visual_mode":"approved raster + firmware live fields",
                    "target_source":"approved target image",
                    "width":target_w,"height":target_h,
                    "picture_mode":2,
                    "dynamic_fields":{
                        "time":"firmware live",
                        "steps":"firmware live · CUSTOMIZE value 8",
                        "heart_rate":"firmware live · CUSTOMIZE value 4",
                        "battery":"read from watch at install time"
                    },
                    "static_analog_note":"Las agujas/segundero del raster siguen siendo gráficos; V0.88 no los declara dinámicos.",
                    "base_raw_size":len(raw),
                    "base_raw_sha256":hashlib.sha256(raw).hexdigest()
                }

'''
if old_prep not in s:
    raise SystemExit("V0.88: preparación V0.87 no encontrada")
s=s.replace(old_prep,new_prep,1)

# Record host time used by the existing OEM sync payload.
old_sync_call='''                    sync_mark=len(messages)
                    await tx(0x6E,sync_payload(),1,0)
                    dev_sync=await wait_data(0x09,sync_mark,8.0)
'''
new_sync_call='''                    sync_mark=len(messages)
                    host_now=datetime.now().astimezone()
                    rep["single_face_install"]["clock_sync"]={
                        "host_iso":host_now.isoformat(),
                        "utc_offset_seconds":int(host_now.utcoffset().total_seconds()) if host_now.utcoffset() else 0,
                        "method":"OEM DEV_SYNC payload 0x68"
                    }
                    emit("HORA · sincronizando reloj con "+host_now.strftime("%H:%M:%S")+" · zona "+host_now.strftime("%z"))
                    await tx(0x6E,sync_payload(),1,0)
                    dev_sync=await wait_data(0x09,sync_mark,8.0)
'''
if old_sync_call not in s:
    raise SystemExit("V0.88: llamada sync V0.87 no encontrada")
s=s.replace(old_sync_call,new_sync_call,1)

# After DEV_SYNC is parsed, read battery data type 3, construct the live cBin,
# and only then build the compressed stream used for transfer.
old_props='''                    props=parse_dev_sync_properties(dev_sync)
                    device_pid=parse_dev_sync_pid(dev_sync)
                    pid_source="DEV_SYNC/NEW_PID"
                    cap=props.get(22)
'''
new_props='''                    props=parse_dev_sync_properties(dev_sync)
                    device_pid=parse_dev_sync_pid(dev_sync)
                    pid_source="DEV_SYNC/NEW_PID"
                    cap=props.get(22)

                    battery_payload=props.get(3)
                    battery_percent=(int(battery_payload[0]) if battery_payload and len(battery_payload)>=1 else None)
                    if battery_percent is not None and not (0<=battery_percent<=100):
                        battery_percent=None
                    raw,battery_text=build_live_customize(raw,battery_percent)
                    expected_cmd2=raw[:6].hex()
                    oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                    rep["single_face_install"]["candidate"].update({
                        "battery_percent_at_install":battery_percent,
                        "battery_text":battery_text,
                        "raw_size":len(raw),
                        "raw_sha256":hashlib.sha256(raw).hexdigest(),
                        "raw_header_hex":raw[:10].hex(),
                        "expected_cmd2_hex":expected_cmd2,
                        "oem_stream_size":len(oem_stream),
                        "deflate_size":len(deflated),
                        "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                        "oem_crc16":f"0x{crc16_8005(deflated):04X}",
                        "oem_header_hex":oem_stream[:20].hex()
                    })
                    rep["single_face_install"]["live_bindings"]={
                        "time":{"source":"watch firmware clock","time_pos":raw[0]},
                        "steps":{"source":"watch firmware","field_value":raw[1]},
                        "heart_rate":{"source":"watch firmware","field_value":raw[2]},
                        "battery":{"source":"DEV_SYNC DATA_TYPE_BATTERY_INFO=3","value_at_install":battery_percent,
                                   "continuous_live":False}
                    }
                    emit("DATOS · hora firmware LIVE · pasos LIVE · pulso LIVE · batería="+battery_text)
'''
if old_props not in s:
    raise SystemExit("V0.88: bloque props V0.87 no encontrado")
s=s.replace(old_props,new_props,1)

# The returned cmd2 metadata must now match the dynamic header.
# Existing verification uses expected_cmd2, so no behavioral rewrite is needed.
s=s.replace(
    'V0.88 LISTA · 1º INSTALAR ESFERA EXACTA V0.88; 2º REVISAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Auto-identifica el reloj por E91A/3802 y conserva la referencia exacta.',
    'V0.88 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.88; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Hora, pasos y pulso pasan a datos vivos del reloj.'
)
s=s.replace('INSTALAR ESFERA EXACTA V0.88','INSTALAR ESFERA SINCRONIZADA V0.88')
s=s.replace(
    'V0.88 · REFERENCIA EXACTA + AUTO-ID · ignora BLE ajenos, encuentra UtraWatch por firma E91A/3802 y luego instala el raster aprobado 240×296 en CUSTOMIZE.',
    'V0.88 · ESFERA SINCRONIZADA · conserva el diseño aprobado pero quita los valores de muestra: hora, pasos y pulso los dibuja el firmware con datos reales; batería se lee del reloj al instalar.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.88 aplicado")
