from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.66.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.66")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.66 · modo esfera única · protocolo ApWatch/WTWD', 1)

old_button = '''primary_test=ttk.Button(row,text="PRUEBA V0.28 - CONEXION LIMPIA + HUELLA OAD")
        primary_test.pack(side="left",padx=4)'''
new_button = '''def copy_control_diagnostic():
            text=log.get("1.0","end-1c")
            if not text.strip():
                self.status.set("No hay diagnóstico para copiar todavía.")
                return
            try:
                w.clipboard_clear()
                w.clipboard_append(text)
                w.update_idletasks()
                self.status.set("Diagnóstico copiado al portapapeles.")
            except Exception as ex:
                messagebox.showerror("Copiar diagnóstico",repr(ex))
        primary_test=ttk.Button(row,text="PROBAR FRAGMENTO 0x83 V0.66")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("V0.66 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.66 · 0x83 FRAGMENTADO MÍNIMO · hace bind OEM y envía sólo los primeros 11 bytes zlib del candidato V0.62, forzando exactamente 2 frames BLE. No envía el dial completo.")
            rep=self.base_report()
            rep["dial_sync_fragment_probe"]={
                "phase":"candidate",
                "protocol":"WTWD/ApWatch",
                "candidate":{},
                "bind_writes":[],
                "probe":{},
                "probe_rx":[],
                "postcheck_rx":[],
                "dial_sync_0x83_writes":0,
                "dial_payload_bytes_written":0,
                "dial_total_compressed_bytes":0,
                "destructive_actions":0
            }
            t0=time.monotonic()

            def emit(msg):
                line=f"+{time.monotonic()-t0:06.2f}s · {msg}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def read_candidate():
                import zlib
                path=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v062","single-face-proof-v062.bin")
                if not os.path.exists(path):raise RuntimeError("Falta single-face-proof-v062.bin. Ejecutá V0.62 primero.")
                with open(path,"rb") as fh:raw=fh.read()
                if len(raw)<54 or raw[:2]!=b"WF":raise RuntimeError("WF V0.62 inválido")
                if int.from_bytes(raw[0x30:0x34],"little")!=len(raw):raise RuntimeError("tamaño WF inconsistente")
                packed=zlib.compress(raw,9)
                return path,raw,packed

            def build_chunks(pid,cmd_type,send_type,opcode,payload=b""):
                payload=bytes(payload); n=len(payload)
                if n<=10:
                    pkt=bytearray(20)
                    pkt[0]=0;pkt[1]=pid&0xff;pkt[2]=0;pkt[3]=cmd_type&0xff;pkt[4]=send_type&0xff;pkt[5]=opcode&0xff
                    pkt[8]=n&0xff;pkt[9]=(n>>8)&0xff;pkt[10:10+n]=payload
                    return [bytes(pkt)]
                rem=n-10
                frags=rem//19+(1 if rem%19 else 0)
                if frags>255:raise RuntimeError("payload excede framing maestro")
                out=[];h=bytearray(20)
                h[0]=0;h[1]=pid&0xff;h[2]=frags;h[3]=cmd_type&0xff;h[4]=send_type&0xff;h[5]=opcode&0xff
                h[8]=n&0xff;h[9]=(n>>8)&0xff;h[10:20]=payload[:10]
                out.append(bytes(h));pos=10
                for i in range(frags):
                    c=bytearray(20);c[0]=i+1
                    part=payload[pos:pos+19];c[1:1+len(part)]=part
                    out.append(bytes(c));pos+=len(part)
                return out

            def parse_packets(frames):
                rows=[];i=0
                while i<len(frames):
                    b=frames[i]
                    if len(b)<10 or b[0]!=0:
                        i+=1;continue
                    plen=b[8] | (b[9]<<8)
                    q=bytearray(b[10:10+min(plen,10)])
                    need=max(0,plen-len(q));j=i+1;used=0
                    while need>0 and j<len(frames) and used<b[2]:
                        c=frames[j]
                        if not c or c[0]==0:break
                        take=min(19,need,max(0,len(c)-1))
                        q.extend(c[1:1+take]);need-=take;j+=1;used+=1
                    rows.append({
                        "pid":b[1],"cmd_type":b[3],"send_type":b[4],"opcode":b[5],
                        "payload_length":plen,"payload_hex":bytes(q[:plen]).hex(),
                        "complete":len(q)>=plen
                    })
                    i=max(i+1,j)
                return rows

            def current_time_payload():
                now=int(time.time())
                offset=-time.timezone
                if time.daylight and time.localtime().tm_isdst:offset=-time.altzone
                return now.to_bytes(4,"little",signed=False)+int(offset).to_bytes(4,"little",signed=True)+bytes([0])

            def sync_payload():
                user=bytes([0x0C,0x00,0x66,0xE8,0x03,0x00,0x00,0x01,0x19,0xAF,0x46,0x00])
                language=bytes([0x04,0x00,0x67,0x00])
                tm=bytes([12,0,0x68])+current_time_payload()
                sensor=bytes([0x04,0x00,0x6D,0x01])
                calls=bytes([0x04,0x00,0x7A,0x01])
                apps=bytes([0x08,0x00,0x7C,0x01,0xFF,0xFF,0xFF,0xFF])
                pair=bytes([0x05,0x00,0x78,0x01,0x00])
                subs=[user,language,tm,sensor,calls,apps,pair]
                body=b"".join(subs);total=len(body)+1
                return bytes([total&0xff,(total>>8)&0xff,len(subs)])+body

            async def work():
                emit("1/11 · Abriendo y comprimiendo candidato V0.62…")
                path,raw,packed=await asyncio.to_thread(read_candidate)
                prefix=packed[:11]
                rep["dial_sync_fragment_probe"]["candidate"]={
                    "path":path,"raw_size":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "zlib_size":len(packed),"zlib_sha256":hashlib.sha256(packed).hexdigest(),
                    "zlib_first_32_hex":packed[:32].hex()
                }
                rep["dial_sync_fragment_probe"]["dial_total_compressed_bytes"]=len(packed)
                emit("CANDIDATO · zlib="+str(len(packed))+" bytes · probe="+prefix.hex())

                c=None;events=[];pid=0
                try:
                    emit("2/11 · Conectando…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"

                    def rx(sender,data):
                        h=bytes(data).hex();events.append(bytes(data));emit("B001 RX · "+h)

                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.3)

                    async def send_known(label,cmd_type,send_type,opcode,payload=b"",wait=1.2):
                        nonlocal pid
                        start=len(events)
                        chunks=build_chunks(pid,cmd_type,send_type,opcode,payload)
                        rep["dial_sync_fragment_probe"]["bind_writes"].append({
                            "label":label,"pid":pid,"opcode":f"0x{opcode:02X}",
                            "payload_length":len(payload),"chunks":[x.hex() for x in chunks]
                        })
                        emit("TX "+label+" · frames="+str(len(chunks)))
                        for ch in chunks:
                            await asyncio.wait_for(c.write_gatt_char(b002,ch,response=False),timeout=5)
                            await asyncio.sleep(.06)
                        pid=(pid+1)&0xff
                        await asyncio.sleep(wait)
                        return parse_packets(events[start:])

                    emit("3/11 · DEVICE_INFO 0x02…")
                    await send_known("DEVICE_INFO",0,3,0x02,b"",2.0)
                    emit("4/11 · Bind OEM APP_SYNC 0x6E…")
                    await send_known("APP_SYNC",0,1,0x6E,sync_payload(),1.5)
                    emit("5/11 · Bind OEM BLE5 + EXT_PID…")
                    await send_known("SUP_BLE_50",0,1,0x1D,bytes([1]),.8)
                    await send_known("EXT_PID Universal",0,1,0x1F,bytes([8]),1.5)

                    emit("6/11 · PROBE · 0x83 con 11 bytes zlib; debe producir 1 header + 1 continuación…")
                    start=len(events);probe_pid=pid
                    chunks=build_chunks(pid,0,1,0x83,prefix)
                    if len(chunks)!=2:raise RuntimeError("el probe no generó exactamente 2 frames")
                    rep["dial_sync_fragment_probe"]["probe"]={
                        "pid":probe_pid,"opcode":"0x83","payload_length":len(prefix),
                        "payload_hex":prefix.hex(),"frames":[x.hex() for x in chunks]
                    }
                    rep["dial_sync_fragment_probe"]["dial_sync_0x83_writes"]=1
                    rep["dial_sync_fragment_probe"]["dial_payload_bytes_written"]=len(prefix)
                    for ch in chunks:
                        await asyncio.wait_for(c.write_gatt_char(b002,ch,response=False),timeout=5)
                        await asyncio.sleep(.12)
                    pid=(pid+1)&0xff
                    await asyncio.sleep(10.0)

                    probe_frames=events[start:]
                    packets=parse_packets(probe_frames)
                    rep["dial_sync_fragment_probe"]["probe_rx"]=[x.hex() for x in probe_frames]
                    rep["dial_sync_fragment_probe"]["probe_packets"]=packets
                    connected=bool(getattr(c,"is_connected",False))
                    rep["dial_sync_fragment_probe"]["connected_after_probe"]=connected
                    emit("PROBE · conectado="+str(connected)+" · RX="+str(len(probe_frames)))

                    p83=[x for x in packets if x.get("opcode")==0x83]
                    statuses=[]
                    for x in p83:
                        rawp=bytes.fromhex(x.get("payload_hex") or "")
                        statuses.append(rawp[0] if rawp else None)
                    rep["dial_sync_fragment_probe"]["status_bytes"]=statuses

                    if not connected:
                        emit("7/11 · Conexión cayó; reconectando para postcheck…")
                        try:await c.disconnect()
                        except Exception:pass
                        c,n2=await self.connect_retry(5,emit)
                        rep["dial_sync_fragment_probe"]["reconnect_attempts"]=n2
                        events.clear()
                        await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    else:
                        emit("7/11 · Conexión estable; postcheck DEVICE_INFO…")

                    post=len(events)
                    pkt=build_chunks(pid,0,3,0x02,b"")[0]
                    await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5);pid=(pid+1)&0xff
                    await asyncio.sleep(3.0)

                    emit("8/11 · Postcheck DIAL_INFO 0x84…")
                    pkt=build_chunks(pid,0,3,0x84,b"")[0]
                    await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5);pid=(pid+1)&0xff
                    await asyncio.sleep(4.0)
                    post_frames=events[post:]
                    rep["dial_sync_fragment_probe"]["postcheck_rx"]=[x.hex() for x in post_frames]
                    rep["dial_sync_fragment_probe"]["postcheck_packets"]=parse_packets(post_frames)

                    post_ok=bool(rep["dial_sync_fragment_probe"]["postcheck_packets"])
                    accepted=(1 in statuses) and bool(getattr(c,"is_connected",False)) and post_ok
                    rep["dial_sync_fragment_probe"]["classification"]=(
                        "fragmented_0x83_master_payload_accepted" if accepted else
                        "fragmented_0x83_returned_status" if p83 else
                        "fragmented_0x83_no_explicit_response"
                    )
                    emit("9/11 · CLASIFICACIÓN · "+rep["dial_sync_fragment_probe"]["classification"])
                    emit("10/11 · SEGURIDAD · sólo 11/"+str(len(packed))+" bytes comprimidos; no hubo finalización de dial ni FFC1.")
                    rep["dial_sync_fragment_probe"]["phase"]="complete"
                    emit("11/11 · V0.66 FINALIZADA · COPIAR DIAGNÓSTICO.")
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["dial_sync_fragment_probe"]["phase"]="error"
                    self.report=rep;self.show()
                    append("V0.66 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.66 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                x=result["dial_sync_fragment_probe"]
                append("0x83 FRAGMENTADO · "+x.get("classification","?")+" · enviados "+str(x.get("dial_payload_bytes_written"))+" bytes.")
                self.status.set("V0.66 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=160),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.66 LISTA · 1º PREPARAR ESFERA ÚNICA V0.66; 2º COPIAR DIAGNÓSTICO. Prueba 0x83 con 11 bytes zlib para forzar 2 frames BLE y verifica ACK/estado.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)


s=s.replace("    def open_control(self):", '''    async def inspect_gatt_snapshot(self,emit):
        address=(self.selected or {}).get("address")
        if not address: raise RuntimeError("Seleccioná el reloj primero.")
        client=None
        snapshot={"services":[],"errors":[],"connected":False}
        try:
            target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=8),timeout=10)
            if target is None: raise RuntimeError("El reloj seleccionado no está visible.")
            client=BleakClient(target,timeout=15,winrt={"use_cached_services":False})
            await asyncio.wait_for(client.connect(),timeout=18)
            if not client.is_connected: raise RuntimeError("GATT no conectado")
            snapshot["connected"]=True
            present=set()
            for svc in client.services:
                entry={"uuid":svc.uuid,"characteristics":[]}
                emit("SERVICIO "+svc.uuid)
                for ch in svc.characteristics:
                    present.add(ch.uuid.lower())
                    row={"uuid":ch.uuid,"handle":ch.handle,"properties":list(ch.properties)}
                    entry["characteristics"].append(row)
                    emit("  CARACTERÍSTICA "+str(row))
                snapshot["services"].append(entry)
            expected={"B001":"0000b001-0000-1000-8000-00805f9b34fb","B002":"0000b002-0000-1000-8000-00805f9b34fb","FFC1":"f000ffc1-0451-4000-b000-000000000000","FFC2":"f000ffc2-0451-4000-b000-000000000000"}
            snapshot["present"]={name:uuid in present for name,uuid in expected.items()}
            emit("PRESENCIA "+str(snapshot["present"]))
            if not snapshot["present"]["B001"]:
                emit("B001 AUSENTE en esta enumeración. Causa pendiente; no confirma modo OTA.")
        except asyncio.CancelledError: raise
        except Exception as ex:
            snapshot["errors"].append(type(ex).__name__+": "+str(ex))
            emit("ERROR DE INSPECCIÓN · "+snapshot["errors"][-1])
        finally:
            if client is not None:
                try: await asyncio.wait_for(client.disconnect(),timeout=4)
                except Exception as ex:
                    snapshot["errors"].append("Cierre: "+repr(ex))
                    emit("ERROR DE CIERRE · "+repr(ex))
        return snapshot

    def open_control(self):''',1)


# V0.66: do not depend on a second advertising cycle after the first GATT attempt.
# Reuse the BLEDevice captured by "Buscar relojes" first; fresh scanning is recovery only.
_conn_start=s.index("    async def connect_retry(")
_conn_end=s.index("\n    def diagnose(",_conn_start)
_new_connect_retry='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        selected=self.selected or {}
        address=selected.get("address") or getattr(selected.get("device"),"address",None)
        device=selected.get("device")
        if not address:raise RuntimeError("Seleccioná un reloj en Buscar relojes.")

        self.connection_state={"connected":False,"attempts":0,"phase":"starting","strategies":[]}
        last=None
        attempt_no=0

        async def try_target(label,target,use_cache):
            nonlocal last,attempt_no
            attempt_no+=1
            client=None
            keep=False
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            try:
                kwargs={"timeout":30}
                if sys.platform=="win32":
                    kwargs["winrt"]={"use_cached_services":bool(use_cache)}
                client=BleakClient(target,**kwargs)
                try:
                    await asyncio.wait_for(client.connect(),timeout=32)
                except asyncio.TimeoutError:
                    if not client.is_connected:
                        raise
                    progress(label+" · connect() agotó espera pero Windows informa enlace conectado; validando GATT…")
                if not client.is_connected:
                    raise RuntimeError("Windows no confirmó is_connected")
                try:
                    services=list(client.services)
                except Exception as ex:
                    raise RuntimeError("enlace abierto pero servicios GATT no disponibles: "+repr(ex))
                if not services:
                    raise RuntimeError("servicios GATT vacíos")
                keep=True
                self.selected["device"]=target if not isinstance(target,str) else self.selected.get("device")
                self.connection_state.update({"connected":True,"phase":"gatt_ready","strategy":label})
                progress(label+f" · GATT OK · servicios={len(services)} · MTU={getattr(client,'mtu_size','?')}")
                return client
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                last=ex
                progress(label+" · FALLÓ · "+type(ex).__name__+": "+str(ex))
                return None
            finally:
                if client is not None and not keep:
                    try:
                        if client.is_connected:
                            await asyncio.wait_for(client.disconnect(),timeout=5)
                    except Exception:
                        pass

        # The scan result already contains a WinRT BLEDevice path. This is the most
        # reliable route when the watch stops advertising after a connection attempt.
        direct=[]
        if device is not None:
            direct.extend([
                ("DEVICE + CACHE OFF",device,False),
                ("DEVICE + CACHE ON",device,True),
            ])
        direct.extend([
            ("ADDRESS + CACHE OFF",address,False),
            ("ADDRESS + CACHE ON",address,True),
        ])

        for label,target,use_cache in direct:
            client=await try_target(label,target,use_cache)
            if client is not None:return client,attempt_no
            await asyncio.sleep(2.5)

        # Only now request a fresh advertisement. Failure here does not discard the
        # direct attempts above.
        progress("RECUPERACIÓN · buscando un anuncio fresco hasta 15 s…")
        fresh=None
        try:
            fresh=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=15),timeout=17)
        except Exception as ex:
            last=ex
            progress("RECUPERACIÓN SCAN · "+type(ex).__name__+": "+str(ex))
        if fresh is not None:
            self.selected["device"]=fresh
            for label,use_cache in [("FRESH DEVICE + CACHE OFF",False),("FRESH DEVICE + CACHE ON",True)]:
                client=await try_target(label,fresh,use_cache)
                if client is not None:return client,attempt_no
                await asyncio.sleep(3)

        self.connection_state.update({"connected":False,"phase":"failed"})
        raise RuntimeError("GATT NO DISPONIBLE tras rutas DEVICE/ADDRESS y recuperación: "+str(last))
'''
s=s[:_conn_start]+_new_connect_retry+s[_conn_end:]

p.write_text(s,encoding="utf-8")
print("build patch v0.66 aplicado")
