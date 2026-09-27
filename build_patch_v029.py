from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.54.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.54")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.54 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="DESCUBRIR DIAL OEM V0.54")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("DESCUBRIMIENTO V0.54 NO INICIADO · Bluetooth ocupado.")
                return
            append("V0.54 · DIAL OEM REAL · lee DEVICE_INFO, cierra BLE y consulta el backend oficial WTWD sin credenciales ajenas. Busca listas de diales para candidatos acotados, extrae URLs .bin y analiza cualquier dial descargable. NO escribe 0x83.")
            rep=self.base_report()
            rep["oem_dial_discovery"]={
                "phase":"identity",
                "backend":"https://wr.watchhealth.com.cn/app-halfwit/",
                "auth_policy":"sin token; no se usan credenciales publicadas/de terceros",
                "device_info":None,
                "firmware_signature":None,
                "candidate_watch_ids":[],
                "http_results":[],
                "dial_urls":[],
                "downloads":[],
                "dial_sync_0x83_writes":0,
                "destructive_actions":0
            }
            t0=time.monotonic()
            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def build_request(pid,opcode):
                pkt=bytearray(20)
                pkt[0]=0; pkt[1]=pid&0xff; pkt[2]=0; pkt[3]=0; pkt[4]=3; pkt[5]=opcode&0xff
                pkt[8]=0; pkt[9]=0
                return bytes(pkt)

            def parse_device_frames(frames):
                for idx,row in enumerate(frames):
                    b=row
                    if len(b)>=20 and b[0]==0 and b[5]==0x02:
                        plen=b[8] | (b[9]<<8)
                        if plen>=6 and len(b)>=16:
                            payload=bytearray(b[10:20])
                            remaining=plen-len(payload)
                            j=idx+1
                            while remaining>0 and j<len(frames):
                                c=frames[j]
                                if not c or c[0]==0: break
                                take=min(19,remaining,len(c)-1)
                                payload.extend(c[1:1+take]); remaining-=take; j+=1
                            q=bytes(payload[:plen])
                            if len(q)>=6:
                                return {"id_total":q[0],"customer_id":q[1],"hardware_id":q[2],"code_id":q[3],"picture_id":q[4],"font_id":q[5],"payload_hex":q.hex()}
                return None

            def json_summary(value,limit=12000):
                try:
                    s=json.dumps(value,ensure_ascii=False,separators=(",",":"))
                except Exception:
                    s=str(value)
                return s if len(s)<=limit else s[:limit]+"…[truncado]"

            def collect_urls(obj,path="$"):
                out=[]
                if isinstance(obj,dict):
                    for k,v in obj.items():
                        out.extend(collect_urls(v,path+"."+str(k)))
                elif isinstance(obj,list):
                    for i,v in enumerate(obj):
                        out.extend(collect_urls(v,path+"["+str(i)+"]"))
                elif isinstance(obj,str) and obj.lower().startswith(("http://","https://")):
                    out.append({"path":path,"url":obj})
                return out

            def http_json(method,url,body=None):
                headers={
                    "Accept":"application/json,text/plain,*/*",
                    "Content-Type":"application/json",
                    "User-Agent":"RelojLab/0.54 Windows; BK3288 research"
                }
                data=None if body is None else json.dumps(body,separators=(",",":")).encode("utf-8")
                req=urllib.request.Request(url,data=data,headers=headers,method=method)
                started=time.monotonic()
                try:
                    with urllib.request.urlopen(req,timeout=8) as r:
                        raw=r.read(1024*1024)
                        status=getattr(r,"status",200)
                        ctype=r.headers.get("Content-Type","")
                    text=raw.decode("utf-8","replace")
                    try: parsed=json.loads(text)
                    except Exception: parsed=None
                    return {"ok":True,"status":status,"content_type":ctype,"elapsed_ms":int((time.monotonic()-started)*1000),"json":parsed,"body_preview":text[:12000]}
                except Exception as ex:
                    code=getattr(ex,"code",None)
                    body_text=""
                    try:
                        body_text=ex.read(12000).decode("utf-8","replace")
                    except Exception: pass
                    return {"ok":False,"status":code,"elapsed_ms":int((time.monotonic()-started)*1000),"error":type(ex).__name__+": "+str(ex),"body_preview":body_text}

            def download_candidate(url,folder):
                info={"url":url}
                try:
                    req=urllib.request.Request(url,headers={"User-Agent":"RelojLab/0.54 Windows","Accept":"*/*"})
                    with urllib.request.urlopen(req,timeout=12) as r:
                        ctype=r.headers.get("Content-Type","")
                        total=0; h=hashlib.sha256()
                        name=os.path.basename(urllib.request.urlparse(url).path) if hasattr(urllib.request,"urlparse") else ""
                        if not name or "." not in name: name="dial-"+hashlib.sha256(url.encode()).hexdigest()[:10]+".bin"
                        safe="".join(ch for ch in name if ch.isalnum() or ch in "._-")[:120] or "dial.bin"
                        path=os.path.join(folder,safe)
                        first=bytearray()
                        with open(path,"wb") as fh:
                            while True:
                                chunk=r.read(65536)
                                if not chunk: break
                                total+=len(chunk)
                                if total>32*1024*1024: raise RuntimeError("archivo supera límite seguro de 32 MiB")
                                h.update(chunk)
                                if len(first)<512:first.extend(chunk[:512-len(first)])
                                fh.write(chunk)
                    magic=bytes(first)
                    info.update({"ok":True,"path":path,"size":total,"sha256":h.hexdigest(),"content_type":ctype,"first_256_hex":magic[:256].hex(),"ascii_magic":magic[:16].decode("ascii","replace")})
                    for sig,label in [(b"\\x89PNG\\r\\n\\x1a\\n","png"),(b"\\xff\\xd8\\xff","jpeg")]:
                        pos=magic.find(sig)
                        if pos>=0:info[label+"_offset_first512"]=pos
                except Exception as ex:
                    info.update({"ok":False,"error":type(ex).__name__+": "+str(ex)})
                return info

            async def work():
                c=None; frames=[]
                try:
                    emit("1/8 · Conectando para leer identidad del reloj…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"
                    def rx(sender,data):
                        b=bytes(data); frames.append(b); emit("B001 RX · "+b.hex())
                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.3)
                    pkt=build_request(0,0x02)
                    emit("2/8 · TX DEVICE_INFO 0x02 · "+pkt.hex())
                    await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5)
                    await asyncio.sleep(4)
                    dev=parse_device_frames(frames)
                    rep["oem_dial_discovery"]["device_info"]=dev
                    if not dev: raise RuntimeError("DEVICE_INFO no devolvió los IDs completos.")
                    fw=f"{dev['customer_id']}.{dev['hardware_id']:02d}.{dev['code_id']}.{dev['picture_id']}.{dev['font_id']}"
                    rep["oem_dial_discovery"]["firmware_signature"]=fw
                    emit("IDENTIDAD · "+str(dev)+" · firma OEM candidata="+fw)
                    try: await c.stop_notify(b001)
                    except Exception: pass
                    await asyncio.wait_for(c.disconnect(),timeout=5); c=None

                    candidates=[]
                    for v in [102,dev["customer_id"],dev["id_total"],dev["hardware_id"],dev["code_id"]]:
                        if v not in candidates:candidates.append(v)
                    rep["oem_dial_discovery"]["candidate_watch_ids"]=candidates
                    emit("3/8 · BLE cerrado. Candidatos watchId acotados="+str(candidates))
                    base="https://wr.watchhealth.com.cn/app-halfwit/"

                    jobs=[]
                    for wid in candidates:
                        for endpoint in ["app-dial/getDialList","app-dial/getDefaultDialList"]:
                            url=base+endpoint+"?currentPage=1&pageSize=20&watchId="+str(wid)
                            jobs.append(("GET",wid,endpoint,url,None))
                    # checkForUpdate is useful only as a model discriminator; no file is written.
                    for wid in candidates:
                        body={"currentFirmware":fw,"language":"EN","macAddress":(self.selected or {}).get("address",""),"watchId":str(wid)}
                        jobs.append(("POST",wid,"app-device/checkForUpdate",base+"app-device/checkForUpdate",body))

                    emit("4/8 · Consultando backend OEM sin token · "+str(len(jobs))+" requests máximas…")
                    for idx,(method,wid,endpoint,url,body) in enumerate(jobs,1):
                        emit(f"HTTP {idx}/{len(jobs)} · {method} · watchId={wid} · {endpoint}")
                        res=await asyncio.to_thread(http_json,method,url,body)
                        row={"watch_id":wid,"endpoint":endpoint,"method":method,**res}
                        if row.get("json") is not None:
                            row["json_summary"]=json_summary(row["json"])
                            urls=collect_urls(row["json"])
                            row["urls"]=urls
                            for item in urls:
                                low=item["url"].lower().split("?",1)[0]
                                if low.endswith(".bin"):
                                    rep["oem_dial_discovery"]["dial_urls"].append({"watch_id":wid,"endpoint":endpoint,**item})
                            row.pop("json",None)
                        rep["oem_dial_discovery"]["http_results"].append(row)
                        emit("  -> status="+str(row.get("status"))+" ok="+str(row.get("ok"))+" urls="+str(len(row.get("urls",[]))))
                        await asyncio.sleep(.15)

                    # Deduplicate .bin URLs; downloading is passive and never touches the watch.
                    unique=[]; seen=set()
                    for item in rep["oem_dial_discovery"]["dial_urls"]:
                        if item["url"] not in seen:
                            seen.add(item["url"]); unique.append(item)
                    rep["oem_dial_discovery"]["dial_urls"]=unique
                    emit("5/8 · URLs .bin oficiales encontradas="+str(len(unique)))

                    folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","oem-dials-v054")
                    os.makedirs(folder,exist_ok=True)
                    rep["oem_dial_discovery"]["download_folder"]=folder
                    for i,item in enumerate(unique[:3],1):
                        emit(f"6/8 · Descargando dial OEM {i}/{min(3,len(unique))} · watchId={item['watch_id']}")
                        info=await asyncio.to_thread(download_candidate,item["url"],folder)
                        info["watch_id"]=item["watch_id"]; info["source_endpoint"]=item["endpoint"]
                        rep["oem_dial_discovery"]["downloads"].append(info)
                        emit("  -> "+("OK "+str(info.get("size"))+" bytes · sha256="+str(info.get("sha256")) if info.get("ok") else "FALLÓ "+str(info.get("error"))))

                    rep["oem_dial_discovery"]["backend_accessible"]=any(x.get("ok") for x in rep["oem_dial_discovery"]["http_results"])
                    rep["oem_dial_discovery"]["auth_blocked"]=bool(rep["oem_dial_discovery"]["http_results"]) and all(x.get("status") in (401,403) for x in rep["oem_dial_discovery"]["http_results"] if x.get("status") is not None)
                    rep["oem_dial_discovery"]["phase"]="complete"
                    emit("7/8 · RESUMEN · backend_accessible="+str(rep["oem_dial_discovery"]["backend_accessible"])+" · bins="+str(len(unique))+" · downloads_ok="+str(sum(1 for x in rep["oem_dial_discovery"]["downloads"] if x.get("ok"))))
                    emit("8/8 · V0.54 FINALIZADA · BLE sólo leyó 0x02 · 0x83 NO TOCADO · ninguna esfera instalada/borrada.")
                    return rep
                finally:
                    if c:
                        try: await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex: rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["oem_dial_discovery"]["phase"]="error"
                    self.report=rep; self.show()
                    append("DESCUBRIMIENTO V0.54 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.54 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result; self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                d=result.get("oem_dial_discovery",{})
                if d.get("downloads"):
                    append("DIAL OEM CAPTURADO/ANALIZADO · mandame este diagnóstico; ya tenemos cabecera/tamaño/hash para reconstruir el formato.")
                elif d.get("auth_blocked"):
                    append("BACKEND REQUIERE SESIÓN OEM · siguiente versión capturará una sesión legítima del companion sin usar credenciales de terceros.")
                else:
                    append("SIN .BIN DIRECTO · el diagnóstico conserva respuestas/URLs del backend para resolver el esquema en la siguiente versión.")
                self.status.set("V0.54 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=210),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.54 LISTA · 1º PREPARAR ESFERA ÚNICA V0.54; 2º COPIAR DIAGNÓSTICO. Busca el dial oficial en backend OEM, descarga/analiza .bin si aparece; 0x83 bloqueado.")'
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


# V0.54: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.54 aplicado")
