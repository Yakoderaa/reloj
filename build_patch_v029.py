from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.60.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.60")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.60 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="VINCULAR + BUSCAR BATERÍA WF V0.60")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("V0.60 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.60 · BATERÍA + DIAL DEFAULT · reproduce el enlace OEM conocido antes de consultar BATTERY_INFO 0x03 y escanea diales system/default buscando tipos WF nuevos. DIAL_SYNC 0x83 sigue bloqueado.")
            rep=self.base_report()
            rep["battery_binding_search"]={
                "phase":"connect",
                "protocol":"WTWD/ApWatch",
                "device_info":None,
                "oem_bind":{"writes":[],"acks":[]},
                "battery_attempts":[],
                "battery_percent":None,
                "catalogs":{},
                "known_dynamic_types":{"0x4004":"calories","0x4104":"steps","0x4204":"heart_rate"},
                "new_type_codes":{},
                "battery_binding_candidates":[],
                "dial_sync_0x83_writes":0,
                "destructive_actions":0
            }
            t0=time.monotonic()

            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def build_chunks(pid,cmd_type,send_type,opcode,payload=b""):
                payload=bytes(payload)
                n=len(payload)
                if n<=10:
                    pkt=bytearray(20)
                    pkt[0]=0;pkt[1]=pid&0xff;pkt[2]=0;pkt[3]=cmd_type&0xff;pkt[4]=send_type&0xff;pkt[5]=opcode&0xff
                    pkt[8]=n&0xff;pkt[9]=(n>>8)&0xff
                    pkt[10:10+n]=payload
                    return [bytes(pkt)]
                remain=n-10
                frags=remain//19+(1 if remain%19 else 0)
                chunks=[]
                h=bytearray(20)
                h[0]=0;h[1]=pid&0xff;h[2]=frags&0xff;h[3]=cmd_type&0xff;h[4]=send_type&0xff;h[5]=opcode&0xff
                h[8]=n&0xff;h[9]=(n>>8)&0xff;h[10:20]=payload[:10]
                chunks.append(bytes(h))
                pos=10
                for i in range(frags):
                    c=bytearray(20);c[0]=i+1
                    part=payload[pos:pos+19];c[1:1+len(part)]=part
                    chunks.append(bytes(c));pos+=len(part)
                return chunks

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
                        take=min(19,need,len(c)-1)
                        q.extend(c[1:1+take]);need-=take;used+=1;j+=1
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
                if time.daylight and time.localtime().tm_isdst:
                    offset=-time.altzone
                return now.to_bytes(4,"little",signed=False)+int(offset).to_bytes(4,"little",signed=True)+b"\\x00"

            def sync_payload():
                user=bytes([0x0C,0x00,0x66,0xE8,0x03,0x00,0x00,0x01,0x19,0xAF,0x46,0x00])
                language=bytes([0x04,0x00,0x67,0x00])
                tp=current_time_payload()
                t=bytes([12,0,0x68])+tp
                sensor=bytes([0x04,0x00,0x6D,0x01])
                calls=bytes([0x04,0x00,0x7A,0x01])
                apps=bytes([0x08,0x00,0x7C,0x01,0xFF,0xFF,0xFF,0xFF])
                pair=bytes([0x05,0x00,0x78,0x01,0x00])
                subs=[user,language,t,sensor,calls,apps,pair]
                body=b"".join(subs)
                total=len(body)+1
                return bytes([total&0xff,(total>>8)&0xff,len(subs)])+body

            def http_json(url):
                req=urllib.request.Request(url,headers={"Accept":"application/json,text/plain,*/*","User-Agent":"RelojLab/0.60 Windows"})
                try:
                    with urllib.request.urlopen(req,timeout=10) as r:
                        raw=r.read(2*1024*1024)
                    return {"ok":True,"json":json.loads(raw.decode("utf-8","replace"))}
                except Exception as ex:
                    return {"ok":False,"error":type(ex).__name__+": "+str(ex)}

            def download_bin(url):
                req=urllib.request.Request(url,headers={"Accept":"*/*","User-Agent":"RelojLab/0.60 Windows"})
                with urllib.request.urlopen(req,timeout=12) as r:
                    data=r.read(2*1024*1024)
                return data

            def parse_types(data):
                if len(data)<54 or data[:2]!=b"WF":return []
                n=int.from_bytes(data[0x2e:0x30],"little")
                out=[]
                for i in range(n):
                    off=54+i*20
                    if off+20>len(data):break
                    raw=data[off:off+20]
                    tc=int.from_bytes(raw[2:4],"little")
                    out.append({
                        "type_code":tc,"type_hex":f"0x{tc:04X}",
                        "frames":int.from_bytes(raw[4:6],"little"),
                        "x":int.from_bytes(raw[6:8],"little"),
                        "y":int.from_bytes(raw[8:10],"little"),
                        "arg2":int.from_bytes(raw[14:16],"little")
                    })
                return out

            async def work():
                c=None;events=[];pid=0
                try:
                    emit("1/12 · Conectando…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"
                    def rx(sender,data):
                        b=bytes(data);events.append(b)
                        emit("B001 RX · "+b.hex())
                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.4)

                    async def send(label,cmd_type,send_type,opcode,payload=b"",wait=1.0):
                        nonlocal pid
                        start=len(events)
                        chunks=build_chunks(pid,cmd_type,send_type,opcode,payload)
                        rep["battery_binding_search"]["oem_bind"]["writes"].append({
                            "label":label,"opcode":opcode,"cmd_type":cmd_type,"send_type":send_type,
                            "payload_hex":bytes(payload).hex(),"chunks":[x.hex() for x in chunks]
                        })
                        emit("TX "+label+" · chunks="+str(len(chunks)))
                        for chunk in chunks:
                            await asyncio.wait_for(c.write_gatt_char(b002,chunk,response=False),timeout=5)
                            await asyncio.sleep(.05)
                        pid=(pid+1)&0xff
                        await asyncio.sleep(wait)
                        packets=parse_packets(events[start:])
                        rep["battery_binding_search"]["oem_bind"]["acks"].append({"label":label,"packets":packets})
                        return packets

                    emit("2/12 · DEVICE_INFO de control…")
                    p=await send("DEVICE_INFO 0x02",0,3,0x02,b"",2.5)
                    for x in p:
                        raw=bytes.fromhex(x["payload_hex"])
                        if x["opcode"]==2 and x["send_type"]!=4 and len(raw)>=6:
                            rep["battery_binding_search"]["device_info"]={
                                "id_total":raw[0],"customer_id":raw[1],"hardware_id":raw[2],
                                "code_id":raw[3],"picture_id":raw[4],"font_id":raw[5],"payload_hex":raw.hex()
                            }

                    emit("3/12 · Enlace OEM · DEV_SYNC_SETTINGS 0x6E…")
                    await send("DEV_SYNC_SETTINGS 0x6E",0,1,0x6E,sync_payload(),2.0)
                    emit("4/12 · Enlace OEM · BLE5 0x1D + EXT_PID 0x1F…")
                    await send("SUP_BLE_50 0x1D",0,1,0x1D,b"\\x01",1.0)
                    await send("EXT_PID 0x1F · Universal",0,1,0x1F,b"\\x08",2.0)

                    emit("5/12 · Consultando BATTERY_INFO 0x03 tres veces tras bind OEM…")
                    level=None
                    for attempt in range(1,4):
                        start=len(events)
                        chunks=build_chunks(pid,0,3,0x03,b"")
                        emit(f"BATTERY {attempt}/3 · TX "+chunks[0].hex())
                        for chunk in chunks:
                            await asyncio.wait_for(c.write_gatt_char(b002,chunk,response=False),timeout=5)
                        pid=(pid+1)&0xff
                        await asyncio.sleep(5.0)
                        packets=parse_packets(events[start:])
                        candidate=None
                        for x in packets:
                            raw=bytes.fromhex(x["payload_hex"])
                            if x["opcode"]==3 and x["send_type"]!=4 and raw:
                                if 0<=raw[0]<=100:candidate=raw[0]
                        rep["battery_binding_search"]["battery_attempts"].append({
                            "attempt":attempt,"packets":packets,"percent":candidate
                        })
                        emit("BATTERY "+str(attempt)+" · "+(str(candidate)+"%" if candidate is not None else "ACK/sin datos"))
                        if candidate is not None:
                            level=candidate;break
                    rep["battery_binding_search"]["battery_percent"]=level

                    emit("6/12 · Cerrando BLE antes del análisis web…")
                    try:await c.stop_notify(b001)
                    except Exception:pass
                    await asyncio.wait_for(c.disconnect(),timeout=5);c=None

                    emit("7/12 · Escaneando catálogo normal + default/system…")
                    endpoints=["app-dial/getDialList","app-dial/getDefaultDialList"]
                    known={0x4004,0x4104,0x4204,0x0304,0x0404,0x0804,0x0904,0x0A04,0x0B04,0x1002,0x1102,0x0501,0x0601,0x0701,0x0105}
                    seen_types={}
                    for endpoint in endpoints:
                        items=[];errors=[]
                        for page in range(1,7):
                            url=f"https://wr.watchhealth.com.cn/app-halfwit/{endpoint}?currentPage={page}&pageSize=20&watchId=102"
                            res=await asyncio.to_thread(http_json,url)
                            if not res["ok"]:
                                errors.append({"page":page,"error":res["error"]});break
                            obj=res["json"]
                            rows=obj.get("data") if isinstance(obj,dict) else None
                            if not isinstance(rows,list) or not rows:break
                            for e in rows:
                                if str(e.get("resolution",""))=="240*296" and isinstance(e.get("dialFile"),str):
                                    items.append(e)
                            await asyncio.sleep(.08)
                        rep["battery_binding_search"]["catalogs"][endpoint]={"count":len(items),"errors":errors}
                        emit(endpoint+" · 240×296="+str(len(items)))
                        for idx,e in enumerate(items):
                            try:
                                data=await asyncio.to_thread(download_bin,e["dialFile"])
                                types=parse_types(data)
                                did=str(e.get("dialId") or e.get("id") or idx)
                                for d in types:
                                    tc=d["type_code"]
                                    row=seen_types.setdefault(tc,{"type_hex":d["type_hex"],"count":0,"dial_ids":[],"examples":[],"sources":set()})
                                    row["count"]+=1
                                    if did not in row["dial_ids"] and len(row["dial_ids"])<20:row["dial_ids"].append(did)
                                    if len(row["examples"])<8:row["examples"].append({"dial_id":did,"x":d["x"],"y":d["y"],"frames":d["frames"],"arg2":d["arg2"]})
                                    row["sources"].add(endpoint)
                            except Exception as ex:
                                pass

                    for tc,row in seen_types.items():
                        row["sources"]=sorted(row["sources"])
                    rep["battery_binding_search"]["all_type_codes"]={f"0x{k:04X}":v for k,v in sorted(seen_types.items())}
                    new={k:v for k,v in seen_types.items() if k not in known}
                    rep["battery_binding_search"]["new_type_codes"]={f"0x{k:04X}":v for k,v in sorted(new.items())}

                    emit("8/12 · Tipos WF nuevos fuera del mapa actual="+str([f"0x{k:04X}" for k in sorted(new)]))
                    candidates=[]
                    for tc,row in sorted(new.items()):
                        # Candidate only: no semantic claim without visual evidence.
                        if (tc & 0x00FF)==0x04 and row["count"]>=1:
                            candidates.append({
                                "type_hex":f"0x{tc:04X}","count":row["count"],
                                "dial_ids":row["dial_ids"],"reason":"tipo dinámico xx04 no presente en el corpus ya clasificado; requiere correlación visual"
                            })
                    rep["battery_binding_search"]["battery_binding_candidates"]=candidates

                    emit("9/12 · BATERÍA tras bind OEM="+(str(level)+"%" if level is not None else "sin datos"))
                    emit("10/12 · Candidatos de binding batería="+str([x["type_hex"] for x in candidates]))
                    rep["battery_binding_search"]["battery_status"]=(
                        "runtime_confirmed" if level is not None else
                        "firmware_ack_only_even_after_oem_bind"
                    )
                    rep["battery_binding_search"]["phase"]="complete"
                    emit("11/12 · SEGURIDAD · se usaron sólo comandos OEM documentados de enlace/consulta; ningún 0x83.")
                    emit("12/12 · V0.60 FINALIZADA · COPIAR DIAGNÓSTICO.")
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["battery_binding_search"]["phase"]="error"
                    self.report=rep;self.show()
                    append("V0.60 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.60 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                x=result.get("battery_binding_search",{})
                if x.get("battery_percent") is not None:
                    append("BATERÍA REAL OBTENIDA · "+str(x.get("battery_percent"))+"%.")
                else:
                    append("BATERÍA 0x03 SIGUE ACK-ONLY incluso tras bind OEM; no voy a fingir un porcentaje.")
                append("TIPOS NUEVOS PARA AISLAR · "+str([q.get("type_hex") for q in x.get("battery_binding_candidates",[])]))
                self.status.set("V0.60 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=300),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.60 LISTA · 1º PREPARAR ESFERA ÚNICA V0.60; 2º COPIAR DIAGNÓSTICO. Hace bind OEM, reintenta batería 0x03 y escanea diales default/system por tipos WF nuevos; 0x83 bloqueado.")'
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


# V0.60: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.60 aplicado")
