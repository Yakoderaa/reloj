from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.84.0"' not in s:
    raise SystemExit("V0.85 requiere la base V0.84 aplicada")

s=s.replace('APP_VERSION="0.84.0"','APP_VERSION="0.85.0"',1)
s=s.replace('V0.84','V0.85')

# V0.84 only changed the human-readable label to MARKET. The actual transfer
# call remained CUSTOMIZE/cmd=2, so the watch never received the dynamic WF
# in the server-dial slot. Fix the real call and report field explicitly.
old='''                    custom_transfer=await transfer_slot(2,"CUSTOMIZE",file_bytes,chunks)
                    rep["single_face_install"]["custom_transfer"]=custom_transfer
'''
new='''                    target_transfer=await transfer_slot(3,"TARGET-MARKET",file_bytes,chunks)
                    rep["single_face_install"]["target_market_transfer"]=target_transfer
'''
if old not in s:
    raise SystemExit("V0.85: no se encontró la llamada CUSTOMIZE heredada de V0.84")
s=s.replace(old,new,1)

# The final V0.84 classifier already referenced target_transfer, which caused
# the observed NameError because the replacement above had not happened.
if 'target_transfer.get("ok")' not in s:
    raise SystemExit("V0.85: clasificación target_transfer ausente")

# Ensure all runtime wording describes what is really happening.
s=s.replace('CUSTOMIZE · ', 'TARGET-MARKET · ')
s=s.replace('CUSTOMIZE completo', 'TARGET-MARKET completo')
s=s.replace('slot editable exacto de UtraWatch', 'slot MARKET exacto de UtraWatch')

# V0.84 proved the transfer path but the selection can race the watch after a
# large file. Retry selection and verification rather than declaring failure
# after a single immediate read.
old_verify='''                    target_index=int(target_index)
                    _,sel_status,_=await tx83_wait(bytes([1,target_index&255]),3.0)
                    if sel_status!=1:raise RuntimeError("El reloj rechazó la selección del slot MARKET "+str(target_index))
                    await asyncio.sleep(1.2)
                    verify_mark=len(messages)
                    await tx(0x84,b"",3,0)
                    selected_payload=await wait_data(0x84,verify_mark,5.0)
                    selected_info=dial_info(selected_payload)
                    selection_verified=bool(selected_info and selected_info.get("index")==target_index)
                    selection={"index":target_index,"show_order":face_slots.get("market_show_order"),
                               "status":sel_status,"verified":selection_verified,"dial_info":selected_info}
                    rep["single_face_install"]["selection_lock"]=selection
'''
new_verify='''                    target_index=int(target_index)
                    selection_attempts=[]
                    selection_verified=False
                    selected_info=None
                    sel_status=None
                    for select_try in range(1,4):
                        _,sel_status,_=await tx83_wait(bytes([1,target_index&255]),3.0)
                        await asyncio.sleep(1.4 if select_try==1 else 2.0)
                        verify_mark=len(messages)
                        await tx(0x84,b"",3,0)
                        selected_payload=await wait_data(0x84,verify_mark,5.0)
                        selected_info=dial_info(selected_payload)
                        ok=bool(sel_status==1 and selected_info and selected_info.get("index")==target_index)
                        selection_attempts.append({
                            "attempt":select_try,"status":sel_status,
                            "dial_info":selected_info,"verified":ok
                        })
                        if ok:
                            selection_verified=True
                            break
                    if sel_status!=1:
                        raise RuntimeError("El reloj rechazó la selección del slot MARKET "+str(target_index))
                    selection={"index":target_index,"show_order":face_slots.get("market_show_order"),
                               "status":sel_status,"verified":selection_verified,
                               "dial_info":selected_info,"attempts":selection_attempts}
                    rep["single_face_install"]["selection_lock"]=selection
'''
if old_verify not in s:
    raise SystemExit("V0.85: bloque de selección MARKET V0.84 no encontrado")
s=s.replace(old_verify,new_verify,1)

# Do not abort before producing a useful diagnostic if the firmware ACKs the
# downloaded MARKET face but delays reflecting the selected index. The photo
# is the physical truth; classify transport and selection separately.
old_all='''                    all_ok=bool(target_transfer.get("ok") and sel_status==1 and selection_verified and connected)
'''
new_all='''                    transfer_ok=bool(target_transfer.get("ok") and connected)
                    all_ok=bool(transfer_ok and sel_status==1 and selection_verified)
'''
if old_all not in s:
    raise SystemExit("V0.85: all_ok V0.84 no encontrado")
s=s.replace(old_all,new_all,1)

old_class='''                    rep["single_face_install"]["classification"]=(
                        "target_photo_dynamic_face_installed_and_selected" if all_ok else
                        "custom_face_install_failed"
                    )
'''
new_class='''                    rep["single_face_install"]["classification"]=(
                        "target_photo_dynamic_face_installed_and_selected" if all_ok else
                        "target_photo_market_transferred_selection_pending" if transfer_ok and sel_status==1 else
                        "target_photo_dynamic_face_install_failed"
                    )
'''
if old_class not in s:
    raise SystemExit("V0.85: clasificación V0.84 no encontrada")
s=s.replace(old_class,new_class,1)

s=s.replace(
    'V0.85 LISTA · 1º INSTALAR ESFERA DE LA FOTO V0.85; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Instala un WF MARKET 240×296 con analógico, hora curvada, pasos y pulso dinámicos.',
    'V0.85 LISTA · 1º INSTALAR ESFERA EXACTA V0.85; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Envía de verdad el WF dinámico al slot MARKET y reintenta la activación hasta verificarla.'
)
s=s.replace('INSTALAR ESFERA DE LA FOTO V0.85','INSTALAR ESFERA EXACTA V0.85')
s=s.replace(
    'V0.85 · ESFERA OBJETIVO · reconstruye el diseño de la foto con recursos OEM dinámicos: analógico central, hora curvada arriba izquierda, pasos y pulso abajo.',
    'V0.85 · ESFERA EXACTA · objetivo visual confirmado: fondo negro, analógico central blanco/rojo, hora curvada arriba izquierda, pasos abajo izquierda y pulso abajo derecha.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.85 aplicado")
