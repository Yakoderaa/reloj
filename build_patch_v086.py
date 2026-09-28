from pathlib import Path
import base64, zlib, hashlib

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.85.0"' not in s:
    raise SystemExit("V0.86 requiere la base V0.85 aplicada")

asset_path=Path("assets/target_face_v086.b64")
if not asset_path.exists():
    raise SystemExit("V0.86: falta assets/target_face_v086.b64")
packed=asset_path.read_text(encoding="utf-8").strip()
raw_check=zlib.decompress(base64.b64decode(packed))
expected_sha="61b86e4f5f998a436c88785e14436b00d797a705dcea6879e96a7828c4cb62a2"
if len(raw_check)!=142090:
    raise SystemExit("V0.86: tamaño cBinFile inesperado: "+str(len(raw_check)))
if hashlib.sha256(raw_check).hexdigest()!=expected_sha:
    raise SystemExit("V0.86: SHA del objetivo visual no coincide")
if raw_check[:10].hex()!="000000000002f0002801":
    raise SystemExit("V0.86: cabecera CUSTOMIZE 240x296 inesperada")

s=s.replace('APP_VERSION="0.85.0"','APP_VERSION="0.86.0"',1)
s=s.replace('V0.85','V0.86')

fn_start=s.index("            def build_target_market_candidate():")
fn_end=s.index("            def build(dev_type",fn_start)
new_fn=f'''            def build_exact_reference_customize():
                # Exact approved reference, cropped to the physical 240x296 display.
                # UtraWatch CUSTOMIZE cBinFile:
                # 10-byte config + 240*296 BGR565 pixels.
                import base64,zlib
                packed={packed!r}
                raw=zlib.decompress(base64.b64decode(packed))
                expected={expected_sha!r}
                if len(raw)!=142090 or hashlib.sha256(raw).hexdigest()!=expected:
                    raise RuntimeError("Referencia visual V0.86 embebida corrupta")
                if raw[:10].hex()!="000000000002f0002801":
                    raise RuntimeError("Cabecera CUSTOMIZE V0.86 inválida")
                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),
                                    "RelojLab","wf-analysis-v086")
                os.makedirs(folder,exist_ok=True)
                path=os.path.join(folder,"exact-approved-reference-v086.bin")
                with open(path,"wb") as fh:fh.write(raw)
                return path,raw,240,296
'''
s=s[:fn_start]+new_fn+s[fn_end:]

# Replace the V0.85 MARKET candidate preparation with the exact approved
# CUSTOMIZE cBinFile. The OLED/LCD image contains the approved layout itself;
# the firmware's standard digital clock is black/invisible in the cBin header.
prep_start=s.index('                emit("1/9 · Cargando esfera objetivo dinámica 240×296 + paquete OEM…")')
prep_end=s.index('                c=None;events=[];messages=[];tx_n=1;wire_dev_type=1',prep_start)
new_prep='''                emit("1/9 · Cargando referencia APROBADA exacta 240×296 + paquete OEM…")
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
s=s[:prep_start]+new_prep+s[prep_end:]

old_transfer='''                    emit("5/9 · Instalando la esfera de la foto como MARKET cmd=3 · "+str(len(chunks))+" bloques…")
                    target_transfer=await transfer_slot(3,"TARGET-MARKET",file_bytes,chunks)
                    rep["single_face_install"]["target_market_transfer"]=target_transfer

                    emit("6/9 · MARKET objetivo completo; esperando aplicación…")
'''
new_transfer='''                    emit("5/9 · Instalando referencia exacta en CUSTOMIZE cmd=2 · "+str(len(chunks))+" bloques…")
                    exact_transfer=await transfer_slot(2,"EXACT-CUSTOMIZE",file_bytes,chunks)
                    rep["single_face_install"]["exact_customize_transfer"]=exact_transfer

                    emit("6/9 · CUSTOMIZE exacto completo; esperando aplicación física…")
'''
if old_transfer not in s:
    raise SystemExit("V0.86: bloque de transferencia V0.85 no encontrado")
s=s.replace(old_transfer,new_transfer,1)

# V0.85 queried DIAL_INFO right before the selection. Keep that post-transfer
# read, but verify the CUSTOMIZE metadata itself as well as the selected index.
sel_start=s.index('                    target_index=face_slots.get("market_index")')
sel_end=s.index('                    rep["single_face_install"]["selection_lock"]=selection',sel_start)
sel_end += len('                    rep["single_face_install"]["selection_lock"]=selection')
new_sel='''                    custom_index=face_slots.get("custom_index")
                    if custom_index is None:
                        raise RuntimeError("UtraWatch no resolvió el índice CUSTOMIZE de este reloj")
                    custom_index=int(custom_index)
                    selection_attempts=[]
                    selection_verified=False
                    selected_info=None
                    sel_status=None
                    for select_try in range(1,4):
                        _,sel_status,_=await tx83_wait(bytes([1,custom_index&255]),3.0)
                        await asyncio.sleep(1.4 if select_try==1 else 2.0)
                        verify_mark=len(messages)
                        await tx(0x84,b"",3,0)
                        selected_payload=await wait_data(0x84,verify_mark,5.0)
                        selected_info=dial_info(selected_payload)
                        index_ok=bool(selected_info and selected_info.get("index")==custom_index)
                        cmd2_ok=bool(selected_info and selected_info.get("cmd2_hex")==expected_cmd2)
                        ok=bool(sel_status==1 and index_ok and cmd2_ok)
                        selection_attempts.append({
                            "attempt":select_try,"status":sel_status,
                            "dial_info":selected_info,
                            "index_ok":index_ok,"cmd2_metadata_ok":cmd2_ok,
                            "verified":ok
                        })
                        if ok:
                            selection_verified=True
                            break
                    if sel_status!=1:
                        raise RuntimeError("El reloj rechazó la selección del slot CUSTOMIZE "+str(custom_index))
                    selection={
                        "index":custom_index,
                        "show_order":face_slots.get("custom_show_order"),
                        "status":sel_status,
                        "verified":selection_verified,
                        "expected_cmd2_hex":expected_cmd2,
                        "dial_info":selected_info,
                        "attempts":selection_attempts
                    }
                    rep["single_face_install"]["selection_lock"]=selection'''
s=s[:sel_start]+new_sel+s[sel_end:]

# The exact raster replaces the failed MARKET experiment; do not send a second
# file in this version.
old_mirror='''                    rep["single_face_install"]["customize_mirror"]={
                        "attempted":False,
                        "reason":"V0.86 mantiene V0.83 en CUSTOMIZE y dedica MARKET a la esfera dinámica de la foto"
                    }
'''
new_mirror='''                    rep["single_face_install"]["market_attempt"]={
                        "attempted":False,
                        "reason":"V0.86 usa exclusivamente CUSTOMIZE, la ruta ya confirmada visualmente en V0.83"
                    }
'''
if old_mirror not in s:
    raise SystemExit("V0.86: bloque de mirror V0.85 no encontrado")
s=s.replace(old_mirror,new_mirror,1)

old_all='''                    transfer_ok=bool(target_transfer.get("ok") and connected)
                    all_ok=bool(transfer_ok and sel_status==1 and selection_verified)
'''
new_all='''                    transfer_ok=bool(exact_transfer.get("ok") and connected)
                    all_ok=bool(transfer_ok and sel_status==1 and selection_verified)
'''
if old_all not in s:
    raise SystemExit("V0.86: all_ok V0.85 no encontrado")
s=s.replace(old_all,new_all,1)

old_class='''                    rep["single_face_install"]["classification"]=(
                        "target_photo_dynamic_face_installed_and_selected" if all_ok else
                        "target_photo_market_transferred_selection_pending" if transfer_ok and sel_status==1 else
                        "target_photo_dynamic_face_install_failed"
                    )
'''
new_class='''                    rep["single_face_install"]["classification"]=(
                        "exact_approved_reference_installed_and_selected" if all_ok else
                        "exact_approved_reference_transferred_selection_pending" if transfer_ok and sel_status==1 else
                        "exact_approved_reference_install_failed"
                    )
'''
if old_class not in s:
    raise SystemExit("V0.86: clasificación V0.85 no encontrada")
s=s.replace(old_class,new_class,1)

# Fix all V0.85 MARKET-specific status wording that would otherwise be
# misleading during the CUSTOMIZE installation.
s=s.replace("TARGET-MARKET · ","EXACT-CUSTOMIZE · ")
s=s.replace("Seleccionando el slot MARKET exacto de UtraWatch",
            "Seleccionando y verificando el slot CUSTOMIZE exacto")

s=s.replace(
    'V0.86 LISTA · 1º INSTALAR ESFERA EXACTA V0.86; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Envía de verdad el WF dinámico al slot MARKET y reintenta la activación hasta verificarla.',
    'V0.86 LISTA · 1º INSTALAR ESFERA EXACTA V0.86; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Copia la referencia aprobada pixel por pixel al CUSTOMIZE real 240×296.'
)
s=s.replace(
    'V0.86 · ESFERA EXACTA · objetivo visual confirmado: fondo negro, analógico central blanco/rojo, hora curvada arriba izquierda, pasos abajo izquierda y pulso abajo derecha.',
    'V0.86 · REFERENCIA EXACTA · usa la imagen aprobada como raster 240×296 en CUSTOMIZE; sin fondo OEM sustituto ni slot MARKET.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.86 aplicado")
print("target raw",len(raw_check),hashlib.sha256(raw_check).hexdigest(),raw_check[:10].hex())
