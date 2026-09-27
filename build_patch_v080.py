from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.75.0"', 'APP_VERSION="0.80.0"', 1)
s = s.replace('root.title("Reloj Lab V0.75")', 'root.title("Reloj Lab V0.80")', 1)
s = s.replace('V0.75 · análisis de transferencia', 'V0.80 · esfera única OEM', 1)
s = s.replace('ANALIZAR TRANSFERENCIA V0.75', 'INSTALAR ESFERA ÚNICA V0.80', 1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("V0.80 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.80 · INSTALACIÓN OEM DE ESFERA ÚNICA · usa el formato real de UtraWatch: consulta 0x84, compresión OEM, cabecera cmd=2 + tamaño + offset y ACK por bloque.")
            rep=self.base_report()
            rep["single_face_install"]={
                "phase":"prepare","blocks":[],"payload_bytes_written":0,"ack_count":0,
                "firmware_actions":0,"factory_faces_deleted":False
            }
            t0=time.monotonic()

            def emit(msg):
                line=f"+{time.monotonic()-t0:06.2f}s · {msg}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def crc16_8005(data):
                crc=0
                for x in data:
                    crc ^= (x&255)<<8
                    for _ in range(8):
                        crc=((crc<<1)^0x8005)&0xffff if (crc&0x8000) else (crc<<1)&0xffff
                return crc

            def oem_dial_compress(raw):
                import zlib
                co=zlib.compressobj(level=6,method=zlib.DEFLATED,wbits=9)
                comp=co.compress(raw)+co.flush()
                hdr=bytearray(20)
                total=len(comp)+20
                hdr[0:4]=total.to_bytes(4,"little")
                hdr[4:6]=crc16_8005(comp).to_bytes(2,"little")
                hdr[6:8]=bytes([0xFE,0xFE])
                hdr[8]=1
                if len(raw)>26 and raw[9]==255:
                    hdr[9]=raw[25]
                    hdr[10]=raw[26]
                elif len(raw)>9:
                    hdr[9]=raw[9]
                    hdr[10]=0
                hdr[11]=0
                return bytes(hdr)+comp,comp

            def read_candidate():
                path=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v062","single-face-proof-v062.bin")
                if not os.path.exists(path):raise RuntimeError("Falta single-face-proof-v062.bin")
                with open(path,"rb") as fh:raw=fh.read()
                if len(raw)<54 or raw[:2]!=b"WF":raise RuntimeError("WF inválido")
                expected="2d055de32cdf31712bffac39a8147f0af30848ffb3e51fece2e6085462551276"
                got=hashlib.sha256(raw).hexdigest()
                if got!=expected:raise RuntimeError("El WF candidato cambió: "+got)
                return path,raw

            def build(pid,op,payload=b"",send_type=1):
                payload=bytes(payload);n=len(payload)
                if n>4855:raise RuntimeError("payload WTWD demasiado grande")
                h=bytearray(20)
                if n<=10:
                    h[1]=pid&255;h[4]=send_type;h[5]=op;h[8]=n&255;h[9]=(n>>8)&255;h[10:10+n]=payload
                    return [bytes(h)]
                frags=((n-10)+18)//19
                h[1]=pid&255;h[2]=frags;h[4]=send_type;h[5]=op;h[8]=n&255;h[9]=(n>>8)&255;h[10:20]=payload[:10]
                out=[bytes(h)];pos=10
                for i in range(frags):
                    c=bytearray(20);c[0]=i+1
                    part=payload[pos:pos+19];c[1:1+len(part)]=part
                    out.append(bytes(c));pos+=len(part)
                return out

            def sync_payload():
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

            async def work():
                emit("1/9 · Validando WF y construyendo paquete OEM…")
                path,raw=await asyncio.to_thread(read_candidate)
                oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                rep["single_face_install"]["candidate"]={
                    "path":path,"raw_size":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "oem_stream_size":len(oem_stream),"deflate_size":len(deflated),
                    "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                    "oem_crc16":f"0x{crc16_8005(deflated):04X}",
                    "oem_header_hex":oem_stream[:20].hex()
                }

                c=None;events=[];messages=[];pid=0
                current=None
                ack83_event=asyncio.Event()
                ack83_statuses=[]

                try:
                    emit("2/9 · Conectando…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"

                    def complete_message(msg):
                        messages.append(msg)
                        if msg["opcode"]==0x83 and msg["send_type"]==4 and msg["payload"]:
                            ack83_statuses.append(msg["payload"][0])
                            ack83_event.set()

                    def rx(sender,data):
                        nonlocal current
                        b=bytes(data);events.append(b)
                        if len(b)<1:return
                        if b[0]==0:
                            if len(b)<10:return
                            plen=b[8]|(b[9]<<8)
                            take=min(10,plen)
                            current={
                                "opcode":b[5],"send_type":b[4],"pid":b[1],"expected_frags":b[2],
                                "next_frag":1,"plen":plen,"payload":bytearray(b[10:10+take])
                            }
                            if b[2]==0 or len(current["payload"])>=plen:
                                msg={k:v for k,v in current.items() if k not in ("payload","next_frag","expected_frags","plen")}
                                msg["payload"]=bytes(current["payload"][:plen])
                                complete_message(msg);current=None
                        elif current is not None and b[0]==current["next_frag"]:
                            need=current["plen"]-len(current["payload"])
                            current["payload"].extend(b[1:1+min(19,max(0,need))])
                            current["next_frag"]+=1
                            if len(current["payload"])>=current["plen"]:
                                msg={k:v for k,v in current.items() if k not in ("payload","next_frag","expected_frags","plen")}
                                msg["payload"]=bytes(current["payload"][:current["plen"]])
                                complete_message(msg);current=None

                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.25)

                    async def tx(op,payload=b"",send_type=1,wait=.5):
                        nonlocal pid
                        start=len(messages);frames=build(pid,op,payload,send_type)
                        this_pid=pid
                        for fr in frames:
                            await asyncio.wait_for(c.write_gatt_char(b002,fr,response=False),timeout=5)
                            await asyncio.sleep(.045)
                        pid=(pid+1)&255
                        if wait:await asyncio.sleep(wait)
                        return this_pid,messages[start:],frames

                    async def tx83_wait(payload,timeout=4.0):
                        before=len(ack83_statuses);ack83_event.clear()
                        this_pid,_,frames=await tx(0x83,payload,1,0)
                        if len(ack83_statuses)==before:
                            try:await asyncio.wait_for(ack83_event.wait(),timeout=timeout)
                            except asyncio.TimeoutError:pass
                        status=ack83_statuses[-1] if len(ack83_statuses)>before else None
                        return this_pid,status,frames

                    def latest_data(opcode,since=0):
                        for m in reversed(messages[since:]):
                            if m["opcode"]==opcode and m["send_type"]==1:
                                return m["payload"]
                        return None

                    def dial_info(payload):
                        if payload is None or len(payload)<17:return None
                        return {
                            "index":payload[0],
                            "cmd2_hex":payload[1:7].hex(),
                            "cmd3_raw":payload[7:9].hex(),
                            "all_len":int.from_bytes(payload[9:13],"little"),
                            "current_pos":int.from_bytes(payload[13:17],"little"),
                            "raw_hex":payload.hex()
                        }

                    emit("3/9 · Bind OEM + consulta de capacidades…")
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

                    file_bytes=oem_stream if has_dial_compress is not False else raw
                    rep["single_face_install"]["transfer_compressed"]=has_dial_compress is not False
                    rep["single_face_install"]["transfer_size"]=len(file_bytes)

                    emit("4/9 · Consultando estado de esfera 0x84 antes de instalar…")
                    before_mark=len(messages)
                    await tx(0x84,b"",3,2.0)
                    pre=dial_info(latest_data(0x84,before_mark))
                    rep["single_face_install"]["pre_dial_info"]=pre

                    chunks=[file_bytes[i:i+300] for i in range(0,len(file_bytes),300)]
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

                    emit("7/9 · Verificando DIAL_INFO y fijando la esfera activa…")
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
                    rep["single_face_install"]["connected_end"]=connected
                    rep["single_face_install"]["phase"]="complete"
                    emit("9/9 · V0.80 FINALIZADA · "+rep["single_face_install"]["classification"])
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["single_face_install"]["phase"]="error"
                    self.report=rep;self.show()
                    append("V0.80 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.80 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                append("ESFERA ÚNICA · "+result["single_face_install"]["classification"]+".")
                self.status.set("V0.80 finalizada. Revisá el reloj y COPIAR DIAGNÓSTICO.")
            self.run_async(asyncio.wait_for(work(),timeout=360),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.75 LISTA · 1º ANALIZAR TRANSFERENCIA V0.75; 2º COPIAR DIAGNÓSTICO. Calcula el plan completo offline; no usa Bluetooth.")'
new_ready='append("V0.80 LISTA · 1º INSTALAR ESFERA ÚNICA V0.80; 2º REVISAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Usa el protocolo OEM real de UtraWatch.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.75")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("overlay V0.80 aplicado")
