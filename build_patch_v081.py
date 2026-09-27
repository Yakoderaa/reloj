from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

# V0.81 sits on top of the V0.80 OEM-transfer overlay.
if 'APP_VERSION="0.80.0"' not in s:
    raise SystemExit("V0.81 requiere la base V0.80 aplicada")
s = s.replace('APP_VERSION="0.80.0"', 'APP_VERSION="0.81.0"', 1)
s = s.replace('V0.80', 'V0.81')
s = s.replace('INSTALAR ESFERA ÚNICA V0.81', 'APLICAR ESFERA ÚNICA V0.81')
s = s.replace(
    'V0.81 · INSTALACIÓN OEM DE ESFERA ÚNICA · usa el formato real de UtraWatch: consulta 0x84, compresión OEM, cabecera cmd=2 + tamaño + offset y ACK por bloque.',
    'V0.81 · APLICAR ESFERA ÚNICA · resuelve el slot editable real de UtraWatch, instala la esfera CUSTOMIZE y la selecciona con showOrder-1.'
)

needle = '''                    def dial_info(payload):
                        if payload is None or len(payload)<17:return None
                        return {
                            "index":payload[0],
                            "cmd2_hex":payload[1:7].hex(),
                            "cmd3_raw":payload[7:9].hex(),
                            "all_len":int.from_bytes(payload[9:13],"little"),
                            "current_pos":int.from_bytes(payload[13:17],"little"),
                            "raw_hex":payload.hex()
                        }
'''
insert = needle + '''
                    def parse_dev_sync_pid(payload):
                        # K6 DATA_TYPE_DEV_SYNC (0x09) contains a K6_MixInfoStruct.
                        # Each property is [item_len_le16, data_type, data...]. NEW_PID is data_type 31.
                        if payload is None or len(payload)<3:return None
                        count=payload[2];pos=3
                        for _ in range(count):
                            if pos+3>len(payload):break
                            item_len=int.from_bytes(payload[pos:pos+2],"little")
                            if item_len<3 or pos+item_len>len(payload):break
                            dtype=payload[pos+2]
                            data=payload[pos+3:pos+item_len]
                            if dtype==31 and len(data)>=2:
                                value=int.from_bytes(data[:2],"little")
                                return value if value>0 else None
                            pos+=item_len
                        return None

                    def fetch_face_slots(device_id):
                        # Exact endpoint used by UtraWatch V2ChoiceClockdialVM.faceConfig(pid, 1).
                        last=None
                        for scheme in ("http","https"):
                            url=(scheme+"://watchhealth.com.cn/YueDongService/app/faceConfig.do?deviceId="+
                                 str(int(device_id))+"&pageIndex=1")
                            try:
                                req=urllib.request.Request(url,headers={"User-Agent":"UtraWatch/1.5 RelojLab/0.81","Accept":"application/json"})
                                with urllib.request.urlopen(req,timeout=10) as response:
                                    obj=json.loads(response.read().decode("utf-8","replace"))
                                rows=obj.get("result") if isinstance(obj,dict) else None
                                if obj.get("code")!=0 or not isinstance(rows,list) or not rows:
                                    raise RuntimeError("faceConfig rechazó deviceId="+str(device_id)+": "+str(obj)[:180])
                                usable=[]
                                for row in rows:
                                    if not isinstance(row,dict):continue
                                    try:order=int(row.get("showOrder"))
                                    except Exception:continue
                                    if order>0:usable.append(row)
                                editable=[x for x in usable if int(x.get("editable",0) or 0)==1]
                                if not editable:raise RuntimeError("faceConfig no contiene editable=1")
                                custom=min(editable,key=lambda x:int(x.get("showOrder")))
                                custom_order=int(custom.get("showOrder"))
                                max_order=max(int(x.get("showOrder")) for x in usable)
                                return {
                                    "device_id":int(device_id),"source":"UtraWatch faceConfig.do",
                                    "custom_show_order":custom_order,"custom_index":custom_order-1,
                                    "market_show_order":max_order+1,"market_index":max_order,
                                    "face_count":len(usable),"editable_id":custom.get("id")
                                }
                            except Exception as ex:last=ex
                        raise RuntimeError("No se pudo resolver faceConfig: "+repr(last))

                    async def transfer_slot(command,label,file_bytes,chunks):
                        result={"cmd":command,"label":label,"bytes":0,"acks":0,"blocks":len(chunks),"ok":False}
                        for idx,chunk in enumerate(chunks,1):
                            offset=(idx-1)*300
                            app_payload=bytes([command])+len(file_bytes).to_bytes(4,"little")+offset.to_bytes(4,"little")+chunk
                            this_pid,status,frames=await tx83_wait(app_payload)
                            connected=bool(getattr(c,"is_connected",False))
                            rep["single_face_install"]["blocks"].append({
                                "slot_cmd":command,"slot":label,"index":idx,"pid":this_pid,"offset":offset,
                                "data_length":len(chunk),"wtwd_payload_length":len(app_payload),
                                "frame_count":len(frames),"status":status,"connected":connected
                            })
                            result["bytes"]+=len(chunk)
                            if status==1:result["acks"]+=1
                            rep["single_face_install"]["payload_bytes_written"]+=len(chunk)
                            if status==1:rep["single_face_install"]["ack_count"]+=1
                            if idx==1 or idx%10==0 or idx==len(chunks):
                                emit(label+" · "+str(idx)+"/"+str(len(chunks))+" · "+str(result["bytes"])+"/"+str(len(file_bytes))+" B · ACK="+str(status))
                            if status!=1 or not connected:
                                raise RuntimeError(label+" bloque "+str(idx)+" rechazado o desconectado: "+str(status))
                        result["ok"]=(result["bytes"]==len(file_bytes) and result["acks"]==len(chunks))
                        return result
'''
if needle not in s:
    raise SystemExit("V0.81: no se encontró dial_info V0.80")
s=s.replace(needle,insert,1)

old_setup='''                    emit("3/9 · Bind OEM + consulta de capacidades…")
                    await tx(0x02,b"",3,1.0)
                    await tx(0x6E,sync_payload(),1,.8)
                    await tx(0x1D,bytes([1]),1,.4)
                    await tx(0x1F,bytes([8]),1,.6)
                    cap_mark=len(messages)
                    await tx(0x16,b"",3,1.2)
                    cap=latest_data(0x16,cap_mark)
                    has_dial_compress=(bool(cap[2]&0x20) if cap is not None and len(cap)>=3 else None)
                    rep["single_face_install"]["function_control"]={
                        "payload_hex":cap.hex() if cap else None,
                        "has_dial_compress":has_dial_compress,
                        "fallback_used":has_dial_compress is None
                    }
'''
new_setup='''                    emit("3/9 · Bind OEM + PID real + navegación de esfera…")
                    dev_mark=len(messages)
                    await tx(0x02,b"",3,1.0)
                    dev_info=latest_data(0x02,dev_mark)
                    customer_id=(dev_info[1] if dev_info is not None and len(dev_info)>=2 else None)
                    hardware_tuple=(tuple(dev_info[2:6]) if dev_info is not None and len(dev_info)>=6 else None)

                    sync_mark=len(messages)
                    await tx(0x09,b"",3,2.0)
                    dev_sync=latest_data(0x09,sync_mark)
                    device_pid=parse_dev_sync_pid(dev_sync)
                    pid_source="DEV_SYNC/NEW_PID"

                    if device_pid is None:
                        pid_mark=len(messages)
                        await tx(0x1F,b"",3,1.2)
                        pid_payload=latest_data(0x1F,pid_mark)
                        if pid_payload is not None and len(pid_payload)>=2:
                            candidate_pid=int.from_bytes(pid_payload[:2],"little")
                            if candidate_pid>0:device_pid=candidate_pid;pid_source="direct NEW_PID"

                    if device_pid is None and customer_id not in (None,0,255):
                        device_pid=int(customer_id);pid_source="legacy customer_id"

                    # This exact watch's validated WF candidate was built from OEM watchId 102.
                    # Use it only as a model-specific fallback when the new-protocol PID is not exposed.
                    if device_pid is None and customer_id==255 and hardware_tuple==(3,1,1,1):
                        device_pid=102;pid_source="validated model-102 fallback"

                    face_slots=None;slot_error=None
                    if device_pid is not None:
                        try:face_slots=await asyncio.to_thread(fetch_face_slots,device_pid)
                        except Exception as ex:slot_error=repr(ex)
                    if face_slots is None and device_pid==102:
                        face_slots={"device_id":102,"source":"verified OEM snapshot 2026-09-27",
                                    "custom_show_order":6,"custom_index":5,"market_show_order":7,
                                    "market_index":6,"face_count":6,"editable_id":406}
                    rep["single_face_install"]["slot_navigation"]={
                        "pid":device_pid,"pid_source":pid_source,"customer_id":customer_id,
                        "hardware_tuple":hardware_tuple,"dev_sync_hex":dev_sync.hex() if dev_sync else None,
                        "face_slots":face_slots,"face_config_error":slot_error
                    }
                    if not face_slots or face_slots.get("custom_index") is None:
                        raise RuntimeError("No se pudo resolver el slot editable de la esfera; no se seleccionará un índice a ciegas.")

                    await tx(0x6E,sync_payload(),1,.8)
                    await tx(0x1D,bytes([1]),1,.4)
                    cap_mark=len(messages)
                    await tx(0x16,b"",3,1.2)
                    cap=latest_data(0x16,cap_mark)
                    has_dial_compress=(bool(cap[2]&0x20) if cap is not None and len(cap)>=3 else None)
                    rep["single_face_install"]["function_control"]={
                        "payload_hex":cap.hex() if cap else None,
                        "has_dial_compress":has_dial_compress,
                        "fallback_used":has_dial_compress is None
                    }
'''
if old_setup not in s:
    raise SystemExit("V0.81: no se encontró setup V0.80")
s=s.replace(old_setup,new_setup,1)

old_transfer='''                    chunks=[file_bytes[i:i+300] for i in range(0,len(file_bytes),300)]
                    emit("5/9 · Instalando esfera CUSTOMIZE cmd=2 · "+str(len(chunks))+" bloques OEM…")
                    for idx,chunk in enumerate(chunks,1):
                        offset=(idx-1)*300
                        app_payload=bytes([2])+len(file_bytes).to_bytes(4,"little")+offset.to_bytes(4,"little")+chunk
                        this_pid,status,frames=await tx83_wait(app_payload)
                        connected=bool(getattr(c,"is_connected",False))
                        rep["single_face_install"]["blocks"].append({
                            "index":idx,"pid":this_pid,"offset":offset,"data_length":len(chunk),
                            "wtwd_payload_length":len(app_payload),"frame_count":len(frames),
                            "status":status,"connected":connected
                        })
                        rep["single_face_install"]["payload_bytes_written"]+=len(chunk)
                        if status==1:rep["single_face_install"]["ack_count"]+=1
                        if idx==1 or idx%10==0 or idx==len(chunks):
                            emit("PROGRESO · "+str(idx)+"/"+str(len(chunks))+" · "+str(rep["single_face_install"]["payload_bytes_written"])+"/"+str(len(file_bytes))+" B · ACK="+str(status))
                        if status!=1 or not connected:
                            raise RuntimeError("Bloque OEM "+str(idx)+" rechazado o desconectado: "+str(status))

                    emit("6/9 · Archivo OEM completo; esperando aplicación…")
                    await asyncio.sleep(5.0)
'''
new_transfer='''                    chunks=[file_bytes[i:i+300] for i in range(0,len(file_bytes),300)]
                    emit("5/9 · Instalando nuestra esfera en CUSTOMIZE cmd=2 · "+str(len(chunks))+" bloques…")
                    custom_transfer=await transfer_slot(2,"CUSTOMIZE",file_bytes,chunks)
                    rep["single_face_install"]["custom_transfer"]=custom_transfer

                    emit("6/9 · CUSTOMIZE completo; esperando aplicación…")
                    await asyncio.sleep(4.0)
'''
if old_transfer not in s:
    raise SystemExit("V0.81: no se encontró transferencia V0.80")
s=s.replace(old_transfer,new_transfer,1)

old_select='''                    emit("7/9 · Verificando DIAL_INFO y fijando la esfera activa…")
                    post_mark=len(messages)
                    await tx(0x84,b"",3,3.0)
                    post=dial_info(latest_data(0x84,post_mark))
                    rep["single_face_install"]["post_dial_info"]=post
                    state_changed=bool(pre and post and pre.get("raw_hex")!=post.get("raw_hex"))
                    rep["single_face_install"]["dial_state_changed"]=state_changed

                    selection=None
                    if post is not None:
                        sel_payload=bytes([1,post["index"]&255])
                        _,sel_status,_=await tx83_wait(sel_payload,3.0)
                        selection={"index":post["index"],"status":sel_status}
                    rep["single_face_install"]["selection_lock"]=selection

                    emit("8/9 · Postcheck de conexión…")
                    postcheck=len(messages)
                    await tx(0x02,b"",3,1.5)
                    connected=bool(getattr(c,"is_connected",False))
                    all_ok=(rep["single_face_install"]["payload_bytes_written"]==len(file_bytes) and rep["single_face_install"]["ack_count"]==len(chunks) and connected)
                    rep["single_face_install"]["classification"]=(
                        "custom_face_oem_installed_and_selected" if all_ok and selection and selection.get("status")==1 else
                        "custom_face_oem_transfer_complete" if all_ok else
                        "custom_face_install_failed"
                    )
'''
new_select='''                    emit("7/9 · Seleccionando el slot editable exacto de UtraWatch…")
                    post_mark=len(messages)
                    await tx(0x84,b"",3,2.0)
                    post=dial_info(latest_data(0x84,post_mark))
                    rep["single_face_install"]["post_dial_info"]=post
                    state_changed=bool(pre and post and pre.get("raw_hex")!=post.get("raw_hex"))
                    rep["single_face_install"]["dial_state_changed"]=state_changed

                    custom_index=int(face_slots["custom_index"])
                    _,sel_status,_=await tx83_wait(bytes([1,custom_index&255]),3.0)
                    if sel_status!=1:raise RuntimeError("El reloj rechazó la selección del slot CUSTOMIZE "+str(custom_index))
                    await asyncio.sleep(1.2)
                    verify_mark=len(messages)
                    await tx(0x84,b"",3,2.0)
                    selected_info=dial_info(latest_data(0x84,verify_mark))
                    selection_verified=bool(selected_info and selected_info.get("index")==custom_index)
                    selection={"index":custom_index,"show_order":face_slots.get("custom_show_order"),
                               "status":sel_status,"verified":selection_verified,"dial_info":selected_info}
                    rep["single_face_install"]["selection_lock"]=selection

                    # Mirror the same WF into the second user-replaceable slot (MARKET cmd=3).
                    # This does not touch firmware-baked factory faces.
                    market_mirror={"attempted":False,"ok":False}
                    market_index=face_slots.get("market_index")
                    if market_index is not None and bool(getattr(c,"is_connected",False)):
                        market_mirror["attempted"]=True
                        try:
                            emit("7/9 · Clonando la misma esfera al slot MARKET cmd=3…")
                            await tx(0x84,b"",3,.8)
                            market_result=await transfer_slot(3,"MARKET",file_bytes,chunks)
                            market_mirror.update(market_result)
                            # A file transfer may alter what the watch displays; force CUSTOMIZE again.
                            _,reselect_status,_=await tx83_wait(bytes([1,custom_index&255]),3.0)
                            market_mirror["reselect_status"]=reselect_status
                        except Exception as ex:
                            market_mirror["error"]=repr(ex)
                    rep["single_face_install"]["market_mirror"]=market_mirror
                    rep["single_face_install"]["factory_faces_deleted"]=False
                    rep["single_face_install"]["factory_faces_note"]="UtraWatch no expone comando de borrado para esferas integradas en firmware; sólo se reemplazaron los slots regrabables."

                    emit("8/9 · Postcheck de conexión y selección…")
                    connected=bool(getattr(c,"is_connected",False))
                    all_ok=bool(custom_transfer.get("ok") and sel_status==1 and connected)
                    rep["single_face_install"]["classification"]=(
                        "custom_face_installed_selected_and_editable_slots_unified" if all_ok and market_mirror.get("ok") else
                        "custom_face_installed_and_selected" if all_ok else
                        "custom_face_install_failed"
                    )
'''
if old_select not in s:
    raise SystemExit("V0.81: no se encontró selección V0.80")
s=s.replace(old_select,new_select,1)

s=s.replace(
    'append("V0.81 LISTA · 1º INSTALAR ESFERA ÚNICA V0.81; 2º REVISAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Usa el protocolo OEM real de UtraWatch.")',
    'append("V0.81 LISTA · 1º APLICAR ESFERA ÚNICA V0.81; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Resuelve PID + showOrder y selecciona el slot editable real.")'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.81 aplicado")
