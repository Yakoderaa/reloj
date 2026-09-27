from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.81.0"' not in s:
    raise SystemExit("V0.82 requiere la base V0.81 aplicada")
s=s.replace('APP_VERSION="0.81.0"','APP_VERSION="0.82.0"',1)
s=s.replace('V0.81','V0.82')

old_sync='''            def sync_payload():
                now=int(time.time());off=-time.timezone
                if time.daylight and time.localtime().tm_isdst:off=-time.altzone
                tm=now.to_bytes(4,"little")+int(off).to_bytes(4,"little",signed=True)+bytes([0])
                subs=[
                    bytes([0x0C,0x00,0x66,0xE8,0x03,0x00,0x00,0x01,0x19,0xAF,0x46,0x00]),
                    bytes([0x04,0x00,0x67,0x00]),bytes([12,0,0x68])+tm,
                    bytes([0x04,0x00,0x6D,0x01]),bytes([0x04,0x00,0x7A,0x01]),
                    bytes([0x08,0x00,0x7C,0x01,0xFF,0xFF,0xFF,0xFF]),
                    bytes([0x05,0x00,0x78,0x01,0x00])
                ]
                body=b"".join(subs);total=len(body)+1
                return bytes([total&255,(total>>8)&255,len(subs)])+body
'''
new_sync='''            def sync_payload():
                # Mirrors SendDataManager.sendAsynInfoDetail() for an ALREADY paired watch.
                # The previous implementation always sent pair=1, which is only used on first pairing.
                now=int(time.time());off=-time.timezone
                if time.daylight and time.localtime().tm_isdst:off=-time.altzone
                tm=now.to_bytes(4,"little")+int(off).to_bytes(4,"little",signed=True)+bytes([0])
                subs=[
                    bytes([0x0C,0x00,0x66,0xE8,0x03,0x00,0x00,0x01,0x19,0xAF,0x46,0x00]),
                    bytes([12,0,0x68])+tm,
                    bytes([0x08,0x00,0x7C,0x01,0xFF,0xFF,0xFF,0xFF]),
                    bytes([0x04,0x00,0x7A,0x01]),
                    bytes([0x04,0x00,0x7B,0x01]),
                    bytes([0x04,0x00,0x67,0x00]),
                    bytes([0x04,0x00,0x6D,0x01]),
                    bytes([0x05,0x00,0x78,0x00,0x00])
                ]
                body=b"".join(subs);total=len(body)+1
                return bytes([total&255,(total>>8)&255,len(subs)])+body
'''
if old_sync not in s: raise SystemExit("V0.82: sync_payload V0.81 no encontrado")
s=s.replace(old_sync,new_sync,1)

old_init='''                c=None;events=[];messages=[];pid=0
                current=None
                ack83_event=asyncio.Event()
                ack83_statuses=[]
'''
new_init='''                c=None;events=[];messages=[];pid=0
                current=None
                ack83_event=asyncio.Event()
                ack83_statuses=[]
                protocol_acks_sent=[]
'''
if old_init not in s: raise SystemExit("V0.82: init no encontrado")
s=s.replace(old_init,new_init,1)

old_complete='''                    def complete_message(msg):
                        messages.append(msg)
                        if msg["opcode"]==0x83 and msg["send_type"]==4 and msg["payload"]:
                            ack83_statuses.append(msg["payload"][0])
                            ack83_event.set()
'''
new_complete='''                    async def ack_device_message(msg):
                        # CEProtocolB automatically ACKs every complete device->app message.
                        # V0.81 parsed those messages but never returned this protocol ACK.
                        a=bytearray(20)
                        a[1]=msg.get("pid",0)&255
                        a[3]=msg.get("n",0)&255
                        a[4]=4
                        a[5]=msg.get("opcode",0)&255
                        a[8]=1
                        a[10]=1
                        try:
                            await asyncio.wait_for(c.write_gatt_char(b002,bytes(a),response=False),timeout=5)
                            protocol_acks_sent.append({"opcode":msg.get("opcode"),"pid":msg.get("pid"),"n":msg.get("n")})
                        except Exception as ex:
                            rep["errors"].append("protocol_ack "+hex(msg.get("opcode",0))+": "+repr(ex))

                    def complete_message(msg):
                        messages.append(msg)
                        if msg["send_type"]==4:
                            if msg["opcode"]==0x83 and msg["payload"]:
                                ack83_statuses.append(msg["payload"][0])
                                ack83_event.set()
                        else:
                            asyncio.create_task(ack_device_message(msg))
'''
if old_complete not in s: raise SystemExit("V0.82: complete_message no encontrado")
s=s.replace(old_complete,new_complete,1)

old_current='''                            current={
                                "opcode":b[5],"send_type":b[4],"pid":b[1],"expected_frags":b[2],
                                "next_frag":1,"plen":plen,"payload":bytearray(b[10:10+take])
                            }
'''
new_current='''                            current={
                                "opcode":b[5],"send_type":b[4],"pid":b[1],"n":b[3],"expected_frags":b[2],
                                "next_frag":1,"plen":plen,"payload":bytearray(b[10:10+take])
                            }
'''
if old_current not in s: raise SystemExit("V0.82: parser current no encontrado")
s=s.replace(old_current,new_current,1)

old_latest='''                    def latest_data(opcode,since=0):
                        for m in reversed(messages[since:]):
                            if m["opcode"]==opcode and m["send_type"]==1:
                                return m["payload"]
                        return None
'''
new_latest='''                    def latest_data(opcode,since=0):
                        for m in reversed(messages[since:]):
                            if m["opcode"]==opcode and m["send_type"]==1:
                                return m["payload"]
                        return None

                    async def wait_data(opcode,since,timeout=6.0):
                        end=time.monotonic()+timeout
                        while time.monotonic()<end:
                            value=latest_data(opcode,since)
                            if value is not None:return value
                            await asyncio.sleep(.08)
                        return None
'''
if old_latest not in s: raise SystemExit("V0.82: latest_data no encontrado")
s=s.replace(old_latest,new_latest,1)

old_parse='''                    def parse_dev_sync_pid(payload):
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
'''
new_parse='''                    def parse_dev_sync_properties(payload):
                        out={}
                        if payload is None or len(payload)<3:return out
                        count=payload[2];pos=3
                        for _ in range(count):
                            if pos+3>len(payload):break
                            item_len=int.from_bytes(payload[pos:pos+2],"little")
                            if item_len<3 or pos+item_len>len(payload):break
                            dtype=payload[pos+2]
                            out[dtype]=bytes(payload[pos+3:pos+item_len])
                            pos+=item_len
                        return out

                    def parse_dev_sync_pid(payload):
                        data=parse_dev_sync_properties(payload).get(31)
                        if data is None or len(data)<2:return None
                        value=int.from_bytes(data[:2],"little")
                        return value if value>0 else None
'''
if old_parse not in s: raise SystemExit("V0.82: parse_dev_sync_pid no encontrado")
s=s.replace(old_parse,new_parse,1)

old_setup='''                    emit("3/9 · Bind OEM + PID real + navegación de esfera…")
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
new_setup='''                    emit("3/9 · Inicialización OEM real · DEVINFO → PAIR SYNC → DEV_SYNC…")
                    dev_mark=len(messages)
                    await tx(0x02,b"",3,0)
                    dev_info=await wait_data(0x02,dev_mark,4.5)
                    customer_id=(dev_info[1] if dev_info is not None and len(dev_info)>=2 else None)
                    hardware_tuple=(tuple(dev_info[2:6]) if dev_info is not None and len(dev_info)>=6 else None)

                    # Official UtraWatch sends sendAsynInfoDetail() first. On an already paired
                    # device pair=0; DEV_SYNC (0x09) is then emitted by the watch.
                    sync_mark=len(messages)
                    await tx(0x6E,sync_payload(),1,0)
                    dev_sync=await wait_data(0x09,sync_mark,8.0)
                    if dev_sync is None:
                        emit("DEV_SYNC espontáneo no llegó; solicitando 0x09 una vez…")
                        sync_mark=len(messages)
                        await tx(0x09,b"",3,0)
                        dev_sync=await wait_data(0x09,sync_mark,5.0)

                    props=parse_dev_sync_properties(dev_sync)
                    device_pid=parse_dev_sync_pid(dev_sync)
                    pid_source="DEV_SYNC/NEW_PID"
                    cap=props.get(22)

                    if device_pid is None:
                        pid_mark=len(messages)
                        await tx(0x1F,b"",3,0)
                        pid_payload=await wait_data(0x1F,pid_mark,3.0)
                        if pid_payload is not None and len(pid_payload)>=2:
                            candidate_pid=int.from_bytes(pid_payload[:2],"little")
                            if candidate_pid>0:device_pid=candidate_pid;pid_source="direct NEW_PID"

                    if device_pid is None and customer_id not in (None,0,255):
                        device_pid=int(customer_id);pid_source="legacy customer_id"
                    if device_pid is None and customer_id==255 and hardware_tuple==(3,1,1,1):
                        device_pid=102;pid_source="validated model-102 fallback"

                    if cap is None:
                        cap_mark=len(messages)
                        await tx(0x16,b"",3,0)
                        cap=await wait_data(0x16,cap_mark,3.0)
                    has_dial_compress=(bool(cap[2]&0x20) if cap is not None and len(cap)>=3 else None)

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
                        "dev_sync_properties":{str(k):v.hex() for k,v in props.items()},
                        "face_slots":face_slots,"face_config_error":slot_error
                    }
                    rep["single_face_install"]["function_control"]={
                        "payload_hex":cap.hex() if cap else None,
                        "has_dial_compress":has_dial_compress,
                        "fallback_used":has_dial_compress is None,
                        "fallback_mode":"raw WF" if has_dial_compress is None else None
                    }
                    if not face_slots or face_slots.get("custom_index") is None:
                        raise RuntimeError("No se pudo resolver el slot editable de la esfera; no se seleccionará un índice a ciegas.")
'''
if old_setup not in s: raise SystemExit("V0.82: setup V0.81 no encontrado")
s=s.replace(old_setup,new_setup,1)

old_bytes='''                    file_bytes=oem_stream if has_dial_compress is not False else raw
                    rep["single_face_install"]["transfer_compressed"]=has_dial_compress is not False
'''
new_bytes='''                    # Compression is optional in the OEM SDK. Unknown capability must
                    # fall back to the raw WF, never to compressed data.
                    file_bytes=oem_stream if has_dial_compress is True else raw
                    rep["single_face_install"]["transfer_compressed"]=has_dial_compress is True
'''
if old_bytes not in s: raise SystemExit("V0.82: selector de compresión no encontrado")
s=s.replace(old_bytes,new_bytes,1)

old_pre='''                    emit("4/9 · Consultando estado de esfera 0x84 antes de instalar…")
                    before_mark=len(messages)
                    await tx(0x84,b"",3,2.0)
                    pre=dial_info(latest_data(0x84,before_mark))
                    rep["single_face_install"]["pre_dial_info"]=pre
'''
new_pre='''                    emit("4/9 · Abriendo transferencia OEM · esperando WATCH_FACE_INFO 0x84 real…")
                    pre=None;state_attempts=[]
                    for attempt in range(1,4):
                        before_mark=len(messages)
                        await tx(0x84,b"",3,0)
                        pre_payload=await wait_data(0x84,before_mark,5.0)
                        info=dial_info(pre_payload)
                        state_attempts.append({"attempt":attempt,"received":info is not None,
                                               "raw_hex":pre_payload.hex() if pre_payload else None})
                        if info is not None:
                            pre=info;break
                        await asyncio.sleep(.7)
                    rep["single_face_install"]["file_state_gate"]={"attempts":state_attempts,"ready":pre is not None}
                    rep["single_face_install"]["pre_dial_info"]=pre
                    if pre is None:
                        raise RuntimeError("El reloj ACKeó comandos pero no devolvió WATCH_FACE_INFO 0x84; transferencia NO iniciada para evitar falsos positivos.")
'''
if old_pre not in s: raise SystemExit("V0.82: pre DIAL_INFO no encontrado")
s=s.replace(old_pre,new_pre,1)

old_select_start='''                    emit("7/9 · Seleccionando el slot editable exacto de UtraWatch…")
                    post_mark=len(messages)
                    await tx(0x84,b"",3,2.0)
                    post=dial_info(latest_data(0x84,post_mark))
'''
new_select_start='''                    emit("7/9 · Seleccionando el slot editable exacto de UtraWatch…")
                    post_mark=len(messages)
                    await tx(0x84,b"",3,0)
                    post_payload=await wait_data(0x84,post_mark,5.0)
                    post=dial_info(post_payload)
'''
if old_select_start not in s: raise SystemExit("V0.82: post DIAL_INFO no encontrado")
s=s.replace(old_select_start,new_select_start,1)

old_verify='''                    await asyncio.sleep(1.2)
                    verify_mark=len(messages)
                    await tx(0x84,b"",3,2.0)
                    selected_info=dial_info(latest_data(0x84,verify_mark))
                    selection_verified=bool(selected_info and selected_info.get("index")==custom_index)
'''
new_verify='''                    await asyncio.sleep(1.2)
                    verify_mark=len(messages)
                    await tx(0x84,b"",3,0)
                    selected_payload=await wait_data(0x84,verify_mark,5.0)
                    selected_info=dial_info(selected_payload)
                    selection_verified=bool(selected_info and selected_info.get("index")==custom_index)
'''
if old_verify not in s: raise SystemExit("V0.82: verify DIAL_INFO no encontrado")
s=s.replace(old_verify,new_verify,1)

market_start='''                    # Mirror the same WF into the second user-replaceable slot (MARKET cmd=3).
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
'''
market_new='''                    # Keep this physical test minimal: first prove CUSTOMIZE is actually
                    # committed/renderable. MARKET mirroring is deferred until visual confirmation.
                    market_mirror={"attempted":False,"ok":False,
                                   "reason":"deferred until CUSTOMIZE is visibly confirmed"}
'''
if market_start not in s: raise SystemExit("V0.82: bloque MARKET no encontrado")
s=s.replace(market_start,market_new,1)

old_class='''                    all_ok=bool(custom_transfer.get("ok") and sel_status==1 and connected)
                    rep["single_face_install"]["classification"]=(
                        "custom_face_installed_selected_and_editable_slots_unified" if all_ok and market_mirror.get("ok") else
                        "custom_face_installed_and_selected" if all_ok else
                        "custom_face_install_failed"
                    )
'''
new_class='''                    all_ok=bool(custom_transfer.get("ok") and sel_status==1 and selection_verified and connected)
                    rep["single_face_install"]["protocol_acks_sent"]=protocol_acks_sent
                    rep["single_face_install"]["classification"]=(
                        "custom_face_protocol_committed_and_selected" if all_ok else
                        "custom_face_install_failed"
                    )
'''
if old_class not in s: raise SystemExit("V0.82: clasificación no encontrada")
s=s.replace(old_class,new_class,1)

s=s.replace(
    'V0.82 LISTA · 1º APLICAR ESFERA ÚNICA V0.82; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Resuelve PID + showOrder y selecciona el slot editable real.',
    'V0.82 LISTA · 1º INSTALAR ESFERA REAL V0.82; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Replica el estado de transferencia OEM y no envía el archivo hasta recibir WATCH_FACE_INFO.'
)
s=s.replace('APLICAR ESFERA ÚNICA V0.82','INSTALAR ESFERA REAL V0.82')

p.write_text(s,encoding="utf-8")
print("overlay V0.82 aplicado")
