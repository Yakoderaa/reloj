from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.62.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.62")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.62 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="CONSTRUIR WF OFFLINE V0.62")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            append("V0.62 · CANDIDATO WF OFFLINE · arma un .bin local usando sólo archivos OEM públicos. No conecta ni escribe al reloj.")
            rep=self.base_report()
            rep["offline_candidate"]={"phase":"build","base":"2011017","time_donor":"2011019","writes_to_watch":0}
            t0=time.monotonic()

            def emit(msg):
                line=f"+{time.monotonic()-t0:06.2f}s · {msg}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def get_json(url):
                req=urllib.request.Request(url,headers={"User-Agent":"RelojLab/0.62","Accept":"application/json"})
                with urllib.request.urlopen(req,timeout=12) as r:
                    return json.loads(r.read().decode("utf-8","replace"))

            def get_bin(url):
                req=urllib.request.Request(url,headers={"User-Agent":"RelojLab/0.62","Accept":"*/*"})
                with urllib.request.urlopen(req,timeout=15) as r:
                    data=r.read(4*1024*1024)
                return data

            def u16(b,o): return int.from_bytes(b[o:o+2],"little")
            def u32(b,o): return int.from_bytes(b[o:o+4],"little")
            def p16(b,o,v): b[o:o+2]=int(v).to_bytes(2,"little")
            def p32(b,o,v): b[o:o+4]=int(v).to_bytes(4,"little")

            def parse(data):
                if len(data)<54 or data[:2]!=b"WF": raise RuntimeError("magic WF inválido")
                n=u16(data,0x2e); ds=[]
                for i in range(n):
                    off=54+i*20; raw=data[off:off+20]
                    if len(raw)!=20: raise RuntimeError("descriptor truncado")
                    ds.append({"index":i,"raw":bytes(raw),"type":u16(raw,2),"frames":u16(raw,4),
                               "x":u16(raw,6),"y":u16(raw,8),"ptr":u16(raw,18),"abs":u16(raw,18)+2})
                return {"version":u16(data,2),"width":u16(data,0x2a),"height":u16(data,0x2c),
                        "count":n,"declared":u32(data,0x30),"resource_base":u32(data,0x34)+2,
                        "descriptors":ds}

            def find_desc(wf,typ,occ=0):
                xs=[d for d in wf["descriptors"] if d["type"]==typ]
                if occ>=len(xs): raise RuntimeError(f"falta descriptor 0x{typ:04X}")
                return xs[occ]

            def segment(data,wf,desc):
                starts=sorted(set(d["abs"] for d in wf["descriptors"] if 0<=d["abs"]<len(data)))
                s=desc["abs"]; nxt=[x for x in starts if x>s]; e=nxt[0] if nxt else len(data)
                if e<=s: raise RuntimeError("segmento de recurso inválido")
                return bytes(data[s:e])

            def patch_desc(buf,index,donor,x,y,ptr):
                raw=bytearray(donor["raw"]); p16(raw,6,x); p16(raw,8,y); p16(raw,18,ptr)
                off=54+index*20; buf[off:off+20]=raw

            async def work():
                emit("1/7 · Buscando diales OEM 2011017 y 2011019…")
                found={}
                base="https://wr.watchhealth.com.cn/app-halfwit/app-dial/getDialList"
                for page in range(1,8):
                    obj=await asyncio.to_thread(get_json,f"{base}?currentPage={page}&pageSize=20&watchId=102")
                    rows=obj.get("data") if isinstance(obj,dict) else []
                    for e in rows or []:
                        did=str(e.get("dialId") or "")
                        if did in ("2011017","2011019") and isinstance(e.get("dialFile"),str): found[did]=e
                    if len(found)==2: break
                if len(found)!=2: raise RuntimeError("no aparecieron ambos diales OEM")

                emit("2/7 · Descargando donantes…")
                base_data=await asyncio.to_thread(get_bin,found["2011017"]["dialFile"])
                time_data=await asyncio.to_thread(get_bin,found["2011019"]["dialFile"])
                bw=parse(base_data); tw=parse(time_data)
                if (bw["width"],bw["height"],bw["count"])!=(240,296,10): raise RuntimeError("estructura base inesperada")

                hour=find_desc(tw,0x0504); sep=find_desc(tw,0x1002,1); minute=find_desc(tw,0x0604)
                donors=[("hour",hour,segment(time_data,tw,hour),48,55,1),
                        ("separator",sep,segment(time_data,tw,sep),73,48,2),
                        ("minute",minute,segment(time_data,tw,minute),98,55,5)]

                emit("3/7 · Copiando tres recursos OEM sin mover el cuerpo base…")
                cand=bytearray(base_data); copied={}
                for role,d,blob,x,y,slot in donors:
                    start=len(cand)
                    if start-2>65535: raise RuntimeError("puntero u16 excedido")
                    cand.extend(blob); ptr=start-2
                    patch_desc(cand,slot,d,x,y,ptr)
                    copied[role]={"start":start,"stored_pointer":ptr,"length":len(blob),
                                  "sha256":hashlib.sha256(blob).hexdigest()}
                p32(cand,0x30,len(cand))

                emit("4/7 · Reparseando candidato completo…")
                cw=parse(cand)
                types=[f"0x{d['type']:04X}" for d in cw["descriptors"]]
                expected=["0x1002","0x0504","0x1002","0x4204","0x4104","0x0604","0x0501","0x0601","0x0701","0x1102"]

                checks={
                    "magic":bytes(cand[:2])==b"WF",
                    "version":cw["version"]==1026,
                    "resolution":(cw["width"],cw["height"])==(240,296),
                    "count":cw["count"]==10,
                    "declared_size":cw["declared"]==len(cand),
                    "table_not_shifted":cw["resource_base"]==bw["resource_base"],
                    "all_pointers_in_file":all(0<=d["abs"]<len(cand) for d in cw["descriptors"]),
                    "type_sequence":types==expected,
                    "all_pointers_fit_u16":all(d["ptr"]<=65535 for d in cw["descriptors"])
                }
                checks["all_pass"]=all(checks.values())
                emit("5/7 · VALIDACIÓN · "+str(checks))
                if not checks["all_pass"]: raise RuntimeError("validación offline incompleta")

                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v062")
                os.makedirs(folder,exist_ok=True)
                bin_path=os.path.join(folder,"single-face-proof-v062.bin")
                report_path=os.path.join(folder,"single-face-proof-v062.json")
                with open(bin_path,"wb") as fh: fh.write(cand)

                info={"path":bin_path,"size":len(cand),"sha256":hashlib.sha256(cand).hexdigest(),
                      "base_sha256":hashlib.sha256(base_data).hexdigest(),
                      "donor_sha256":hashlib.sha256(time_data).hexdigest(),
                      "descriptor_types":types,"copied_resources":copied,
                      "layout":{"time":"upper-left compact","steps":"0x4104","heart_rate":"0x4204",
                                "analog":["0x0501","0x0601","0x0701"],"battery":"reserved"},
                      "safe_to_transmit":False}
                rep["offline_candidate"].update({"phase":"complete","candidate":info,"checks":checks})
                with open(report_path,"w",encoding="utf-8") as fh:
                    json.dump(rep["offline_candidate"],fh,ensure_ascii=False,indent=2)
                rep["offline_candidate"]["report_file"]=report_path

                emit("6/7 · CANDIDATO · "+str(len(cand))+" bytes · sha256="+info["sha256"])
                emit("7/7 · V0.62 FINALIZADA · .WF construido/validado sólo en PC · ninguna escritura al reloj.")
                return rep

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["offline_candidate"]["phase"]="error"
                    self.report=rep; self.show()
                    append("V0.62 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.62 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result; self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                c=result["offline_candidate"]["candidate"]; v=result["offline_candidate"]["checks"]
                append("WF OFFLINE LISTO · "+str(c["size"])+" bytes · validación="+str(v["all_pass"]))
                self.status.set("V0.62 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=180),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.62 LISTA · 1º PREPARAR ESFERA ÚNICA V0.62; 2º COPIAR DIAGNÓSTICO. Construye y valida un candidato WF real sólo en PC; ninguna escritura al reloj.")'
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


# V0.62: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.62 aplicado")
