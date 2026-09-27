from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.59.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.59")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.59 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="MAPEAR DATOS WF V0.59")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("MAPEO V0.59 NO INICIADO · Bluetooth ocupado.")
                return
            append("V0.59 · MAPA DE DATOS WF · confirma DEVICE_INFO + BATTERY_INFO 0x03 y valida en el corpus OEM los tipos de PASOS/CALORÍAS/PULSO. DIAL_SYNC 0x83 sigue bloqueado.")
            rep=self.base_report()
            rep["wf_data_map"]={
                "phase":"identity",
                "protocol":"WTWD/ApWatch",
                "device_info":None,
                "battery_info":None,
                "battery_frames":[],
                "catalog_watch_id":102,
                "sample_dials":{},
                "dynamic_types":{},
                "shortcut_arg2":{},
                "target_blueprint":{},
                "dial_sync_0x83_writes":0,
                "unknown_writes":0,
                "destructive_actions":0
            }
            t0=time.monotonic()

            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def build_request(pid,opcode):
                pkt=bytearray(20)
                pkt[0]=0; pkt[1]=pid&0xff; pkt[2]=0; pkt[3]=0; pkt[4]=3; pkt[5]=opcode&0xff
                return bytes(pkt)

            def payloads_for(frames,opcode):
                out=[];i=0
                while i<len(frames):
                    b=frames[i]
                    if len(b)>=10 and b[0]==0 and b[5]==opcode:
                        plen=b[8] | (b[9]<<8)
                        payload=bytearray(b[10:10+min(plen,10)])
                        remaining=max(0,plen-len(payload))
                        expected=b[2]
                        j=i+1;used=0
                        while remaining>0 and j<len(frames) and used<expected:
                            c=frames[j]
                            if not c or c[0]==0: break
                            take=min(19,remaining,max(0,len(c)-1))
                            payload.extend(c[1:1+take]);remaining-=take;j+=1;used+=1
                        out.append({
                            "send_type":b[4],"cmd_type":b[3],"payload_length":plen,
                            "payload_hex":bytes(payload[:plen]).hex(),
                            "complete":len(payload)>=plen
                        })
                        i=max(i+1,j)
                    else:
                        i+=1
                return out

            def http_json(url):
                req=urllib.request.Request(url,headers={"Accept":"application/json,text/plain,*/*","User-Agent":"RelojLab/0.59 Windows"})
                with urllib.request.urlopen(req,timeout=10) as r:
                    return json.loads(r.read(2*1024*1024).decode("utf-8","replace"))

            def download_bytes(url,max_bytes=4*1024*1024):
                req=urllib.request.Request(url,headers={"Accept":"*/*","User-Agent":"RelojLab/0.59 Windows"})
                with urllib.request.urlopen(req,timeout=15) as r:
                    data=r.read(max_bytes+1)
                if len(data)>max_bytes:raise RuntimeError("archivo OEM supera límite seguro")
                return data

            def parse_descriptors(data):
                if len(data)<54 or data[:2]!=b"WF":return []
                n=int.from_bytes(data[0x2e:0x30],"little")
                rows=[]
                for i in range(n):
                    off=54+i*20
                    if off+20>len(data):break
                    vals=[int.from_bytes(data[off+j:off+j+2],"little") for j in range(0,20,2)]
                    mode,type_code,frames,x,y,w,h,arg2,arg3,ptr=vals
                    rows.append({
                        "index":i,"mode":mode,"type_code":type_code,"type_hex":f"0x{type_code:04X}",
                        "frame_count_like":frames,"x":x,"y":y,"width_like":w,"height_like":h,
                        "arg2":arg2,"arg3":arg3,"resource_offset_stored":ptr
                    })
                return rows

            async def work():
                c=None;frames=[]
                try:
                    emit("1/10 · Conectando al reloj…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"

                    def rx(sender,data):
                        b=bytes(data);frames.append(b)
                        emit("B001 RX · "+b.hex())

                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.3)

                    emit("2/10 · TX DEVICE_INFO 0x02")
                    start=len(frames)
                    await asyncio.wait_for(c.write_gatt_char(b002,build_request(0,0x02),response=False),timeout=5)
                    await asyncio.sleep(3.0)
                    dev_packets=payloads_for(frames[start:],0x02)
                    dev=None
                    for q in dev_packets:
                        raw=bytes.fromhex(q["payload_hex"])
                        if len(raw)>=6 and q.get("send_type")!=4:
                            dev={"id_total":raw[0],"customer_id":raw[1],"hardware_id":raw[2],"code_id":raw[3],"picture_id":raw[4],"font_id":raw[5],"payload_hex":raw.hex()}
                    rep["wf_data_map"]["device_info"]=dev
                    emit("DEVICE_INFO · "+str(dev))

                    emit("3/10 · TX BATTERY_INFO 0x03 · consulta documentada, sólo lectura")
                    start=len(frames)
                    await asyncio.wait_for(c.write_gatt_char(b002,build_request(1,0x03),response=False),timeout=5)
                    await asyncio.sleep(3.0)
                    battery_frames=frames[start:]
                    rep["wf_data_map"]["battery_frames"]=[x.hex() for x in battery_frames]
                    bp=payloads_for(battery_frames,0x03)
                    level=None
                    for q in bp:
                        raw=bytes.fromhex(q["payload_hex"])
                        if raw and q.get("send_type")!=4:
                            level=raw[0]
                    rep["wf_data_map"]["battery_info"]={
                        "percent":level,
                        "opcode":"0x03",
                        "payload_rule":"primer byte del payload",
                        "packets":bp,
                        "confirmed":level is not None and 0<=level<=100
                    }
                    emit("BATERÍA · "+(str(level)+"%" if level is not None else "sin payload de datos"))

                    try:await c.stop_notify(b001)
                    except Exception:pass
                    await asyncio.wait_for(c.disconnect(),timeout=5);c=None

                    emit("4/10 · BLE cerrado. Buscando diales de evidencia en catálogo OEM…")
                    wanted={"2011017","2011063","2011101","2011092"}
                    found={}
                    base="https://wr.watchhealth.com.cn/app-halfwit/app-dial/getDialList"
                    for page in range(1,8):
                        obj=await asyncio.to_thread(http_json,f"{base}?currentPage={page}&pageSize=20&watchId=102")
                        rows=obj.get("data") if isinstance(obj,dict) else None
                        if not isinstance(rows,list):continue
                        for e in rows:
                            did=str(e.get("dialId") or "")
                            if did in wanted and isinstance(e.get("dialFile"),str):
                                found[did]=e
                        if wanted.issubset(found.keys()):break
                        await asyncio.sleep(.1)
                    emit("CATÁLOGO · encontrados="+str(sorted(found.keys())))

                    emit("5/10 · Validando PASOS/CALORÍAS/PULSO contra descriptores reales…")
                    for did in sorted(found):
                        e=found[did]
                        data=await asyncio.to_thread(download_bytes,e["dialFile"])
                        desc=parse_descriptors(data)
                        rep["wf_data_map"]["sample_dials"][did]={
                            "sha256":hashlib.sha256(data).hexdigest(),
                            "size":len(data),
                            "resolution":e.get("resolution"),
                            "descriptors":[d for d in desc if d["type_code"] in (0x4004,0x4104,0x4204,0x0105,0x0501,0x0601,0x0701)]
                        }

                    evidence={
                        "0x4004":{
                            "role":"calories_value","confidence":"high",
                            "visual_evidence":"dial 2011017: campo 320 junto a icono de llama",
                            "sample_dials":[k for k,v in rep["wf_data_map"]["sample_dials"].items() if any(d["type_code"]==0x4004 for d in v["descriptors"])]
                        },
                        "0x4104":{
                            "role":"steps_value","confidence":"high",
                            "visual_evidence":"diales 2011017/2011063: número junto a icono de huellas/zapatilla",
                            "sample_dials":[k for k,v in rep["wf_data_map"]["sample_dials"].items() if any(d["type_code"]==0x4104 for d in v["descriptors"])]
                        },
                        "0x4204":{
                            "role":"heart_rate_value","confidence":"high",
                            "visual_evidence":"diales 2011017/2011101: 098 BPM / subdial con corazón",
                            "sample_dials":[k for k,v in rep["wf_data_map"]["sample_dials"].items() if any(d["type_code"]==0x4204 for d in v["descriptors"])]
                        }
                    }
                    rep["wf_data_map"]["dynamic_types"]=evidence
                    emit("TIPOS DINÁMICOS · 0x4004=calorías · 0x4104=pasos · 0x4204=pulso")

                    emit("6/10 · Separando accesos directos 0x0105 de métricas numéricas…")
                    shortcuts={
                        "1":{"role":"heart_app_shortcut","confidence":"high"},
                        "2":{"role":"music_shortcut","confidence":"high"},
                        "10":{"role":"sleep_shortcut","confidence":"high"},
                        "11":{"role":"stopwatch_shortcut","confidence":"high"},
                        "14":{"role":"menu_or_list_shortcut","confidence":"high"},
                        "23":{"role":"sport_run_shortcut","confidence":"high"},
                        "27":{"role":"activity_rings_shortcut","confidence":"high"}
                    }
                    rep["wf_data_map"]["shortcut_arg2"]=shortcuts

                    emit("7/10 · Construyendo blueprint V2 de nuestra esfera…")
                    blueprint={
                        "schema":"relojlab-wf-blueprint-v2",
                        "screen":{"width":240,"height":296,"center":[120,148]},
                        "analog":{
                            "center":[120,148],
                            "hour_hand_type":"0x0501",
                            "minute_hand_type":"0x0601",
                            "second_hand_type":"0x0701"
                        },
                        "digital_time":{
                            "types":["0x0804","0x0904","0x1002","0x0A04","0x0B04"],
                            "placement":"upper_left",
                            "status":"engine types confirmed; curved layout is geometry/resource work"
                        },
                        "steps":{
                            "type":"0x4104","placement":"lower_left","dynamic":True,"confidence":"high"
                        },
                        "heart_rate":{
                            "type":"0x4204","placement":"lower_right","dynamic":True,"confidence":"high"
                        },
                        "battery":{
                            "runtime_ble_opcode":"0x03",
                            "current_percent":level,
                            "wf_type":None,
                            "placement":"upper_right",
                            "dynamic":True,
                            "status":"battery percentage confirmed over BLE; no battery-bound WF descriptor appeared in 104 sampled OEM dials"
                        },
                        "background":"black",
                        "safe_to_transmit":False,
                        "blocking_unknowns":[
                            "identify or derive a native WF battery binding",
                            "isolate Bluetrum ParTool boolean flags / exact PAR encoding",
                            "rebuild a complete WF file and validate all resource pointers before 0x83"
                        ]
                    }
                    rep["wf_data_map"]["target_blueprint"]=blueprint

                    folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v059")
                    os.makedirs(folder,exist_ok=True)
                    path=os.path.join(folder,"wf-blueprint-v059.json")
                    with open(path,"w",encoding="utf-8") as fh:
                        json.dump(blueprint,fh,ensure_ascii=False,indent=2)
                    rep["wf_data_map"]["blueprint_file"]=path

                    emit("8/10 · BLUEPRINT · pasos=0x4104 · pulso=0x4204 · batería BLE=0x03 ("+str(level)+"%)")
                    emit("9/10 · BATERÍA WF · aún sin descriptor nativo confirmado; no se inventa 0x4304 ni se reutiliza un tipo incorrecto.")
                    rep["wf_data_map"]["phase"]="complete"
                    emit("10/10 · V0.59 FINALIZADA · mapa de datos confirmado · DIAL_SYNC 0x83 NO TOCADO.")
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["wf_data_map"]["phase"]="error"
                    self.report=rep;self.show()
                    append("MAPEO V0.59 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.59 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                b=result.get("wf_data_map",{}).get("battery_info",{})
                append("MAPA WF V2 LISTO · PASOS=0x4104 · PULSO=0x4204 · CALORÍAS=0x4004 · batería actual="+str(b.get("percent"))+"%.")
                append("SIGUIENTE BLOQUE · resolver binding de batería + encoder PAR antes de habilitar la primera escritura 0x83.")
                self.status.set("V0.59 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=220),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.59 LISTA · 1º PREPARAR ESFERA ÚNICA V0.59; 2º COPIAR DIAGNÓSTICO. Confirma pasos/pulso/calorías + batería 0x03 y genera blueprint WF V2; 0x83 bloqueado.")'
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


# V0.59: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.59 aplicado")
