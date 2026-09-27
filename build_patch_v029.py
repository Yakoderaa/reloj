from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.61.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.61")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.61 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="GENERAR MANIFIESTO WF V0.61")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("V0.61 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.61 · MAPA WF NORMALIZADO · corrige fecha/hora, fija donantes OEM de recursos y genera el manifiesto de la esfera única 240×296. BATTERY 0x03 queda marcado como ACK-only; 0x83 sigue bloqueado.")
            rep=self.base_report()
            rep["wf_manifest_v061"]={
                "phase":"identity",
                "protocol":"WTWD/ApWatch",
                "device_info":None,
                "source_dials":{},
                "type_map":{},
                "target_manifest":{},
                "battery":{"runtime_opcode":"0x03","runtime_status":"ack_only_after_full_oem_bind","native_wf_binding":None},
                "dial_sync_0x83_writes":0,
                "destructive_actions":0
            }
            t0=time.monotonic()

            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def build_request(pid,opcode):
                pkt=bytearray(20)
                pkt[0]=0;pkt[1]=pid&0xff;pkt[2]=0;pkt[3]=0;pkt[4]=3;pkt[5]=opcode&0xff
                return bytes(pkt)

            def parse_device(frames):
                i=0
                while i<len(frames):
                    b=frames[i]
                    if len(b)>=10 and b[0]==0 and b[5]==0x02:
                        plen=b[8] | (b[9]<<8)
                        q=bytearray(b[10:10+min(plen,10)])
                        need=max(0,plen-len(q));j=i+1;used=0
                        while need>0 and j<len(frames) and used<b[2]:
                            c=frames[j]
                            if not c or c[0]==0:break
                            take=min(19,need,len(c)-1)
                            q.extend(c[1:1+take]);need-=take;j+=1;used+=1
                        raw=bytes(q[:plen])
                        if b[4]!=4 and len(raw)>=6:
                            return {
                                "id_total":raw[0],"customer_id":raw[1],"hardware_id":raw[2],
                                "code_id":raw[3],"picture_id":raw[4],"font_id":raw[5],
                                "payload_hex":raw.hex()
                            }
                        i=max(i+1,j)
                    else:i+=1
                return None

            def http_json(url):
                req=urllib.request.Request(url,headers={"Accept":"application/json,text/plain,*/*","User-Agent":"RelojLab/0.61 Windows"})
                with urllib.request.urlopen(req,timeout=10) as r:
                    return json.loads(r.read(2*1024*1024).decode("utf-8","replace"))

            def download_bytes(url,max_bytes=4*1024*1024):
                req=urllib.request.Request(url,headers={"Accept":"*/*","User-Agent":"RelojLab/0.61 Windows"})
                with urllib.request.urlopen(req,timeout=15) as r:
                    data=r.read(max_bytes+1)
                if len(data)>max_bytes:raise RuntimeError("archivo OEM supera límite seguro")
                return data

            def parse_wf(data):
                if len(data)<54 or data[:2]!=b"WF":raise RuntimeError("archivo no WF")
                n=int.from_bytes(data[0x2e:0x30],"little")
                rows=[]
                for i in range(n):
                    off=54+i*20
                    if off+20>len(data):break
                    vals=[int.from_bytes(data[off+j:off+j+2],"little") for j in range(0,20,2)]
                    mode,tc,frames,x,y,w,h,arg2,arg3,ptr=vals
                    rows.append({
                        "index":i,"mode":mode,"type_code":tc,"type_hex":f"0x{tc:04X}",
                        "frames":frames,"x":x,"y":y,"width_like":w,"height_like":h,
                        "arg2":arg2,"arg3":arg3,"resource_offset_stored":ptr,
                        "raw_hex":data[off:off+20].hex()
                    })
                return {
                    "magic":"WF","version_le":int.from_bytes(data[2:4],"little"),
                    "width":int.from_bytes(data[0x2a:0x2c],"little"),
                    "height":int.from_bytes(data[0x2c:0x2e],"little"),
                    "element_count":n,
                    "declared_size":int.from_bytes(data[0x30:0x34],"little"),
                    "actual_size":len(data),
                    "descriptors":rows
                }

            async def work():
                c=None;events=[]
                try:
                    emit("1/9 · Confirmando identidad del reloj…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"
                    def rx(sender,data):
                        b=bytes(data);events.append(b);emit("B001 RX · "+b.hex())
                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.3)
                    await asyncio.wait_for(c.write_gatt_char(b002,build_request(0,0x02),response=False),timeout=5)
                    await asyncio.sleep(3)
                    dev=parse_device(events)
                    if not dev:raise RuntimeError("DEVICE_INFO incompleto")
                    rep["wf_manifest_v061"]["device_info"]=dev
                    emit("DEVICE_INFO · "+str(dev))
                    try:await c.stop_notify(b001)
                    except Exception:pass
                    await asyncio.wait_for(c.disconnect(),timeout=5);c=None

                    emit("2/9 · Descargando diales OEM de evidencia…")
                    wanted={"2011019","2029002","2011028","2014004","2011015","2014014","2011017","2011092"}
                    found={}
                    base="https://wr.watchhealth.com.cn/app-halfwit/app-dial/getDialList"
                    for page in range(1,8):
                        obj=await asyncio.to_thread(http_json,f"{base}?currentPage={page}&pageSize=20&watchId=102")
                        rows=obj.get("data") if isinstance(obj,dict) else None
                        if not isinstance(rows,list) or not rows:break
                        for e in rows:
                            did=str(e.get("dialId") or "")
                            if did in wanted and isinstance(e.get("dialFile"),str):found[did]=e
                        if wanted.issubset(found.keys()):break
                        await asyncio.sleep(.08)
                    emit("EVIDENCIA · encontrados="+str(sorted(found.keys())))
                    if len(found)<6:raise RuntimeError("faltan diales de evidencia")

                    folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v061")
                    os.makedirs(folder,exist_ok=True)

                    for did in sorted(found):
                        e=found[did]
                        data=await asyncio.to_thread(download_bytes,e["dialFile"])
                        wf=parse_wf(data)
                        wf["sha256"]=hashlib.sha256(data).hexdigest()
                        wf["resolution_meta"]=e.get("resolution")
                        wf["preview_url"]=e.get("previewImg")
                        wf["selected_descriptors"]=[
                            d for d in wf["descriptors"]
                            if d["type_code"] in (0x0101,0x0204,0x0304,0x0404,0x0504,0x0604,0x0804,0x0904,0x0A04,0x0B04,0x1002,0x1102,0x1502,0x4004,0x4104,0x4204,0x0501,0x0601,0x0701,0x0105)
                        ]
                        rep["wf_manifest_v061"]["source_dials"][did]=wf
                        with open(os.path.join(folder,f"dial-{did}.bin"),"wb") as fh:fh.write(data)
                        if isinstance(e.get("previewImg"),str):
                            try:
                                preview=await asyncio.to_thread(download_bytes,e["previewImg"],8*1024*1024)
                                with open(os.path.join(folder,f"dial-{did}-preview.png"),"wb") as ph:ph.write(preview)
                            except Exception:pass

                    emit("3/9 · Normalizando semántica de fecha/hora…")
                    type_map={
                        "0x0204":{"role":"month_number","confidence":"high","evidence":"2029002/2011028: campo izquierdo de fecha MM-DD, 10 estados"},
                        "0x0304":{"role":"day_of_month","confidence":"high","evidence":"2011019: 06 junto a MON; 2029002/2011028: campo derecho MM-DD, 10 estados"},
                        "0x0404":{"role":"weekday","confidence":"high","evidence":"7 estados y posición de MON/WED en múltiples previews"},
                        "0x0504":{"role":"hour_number","confidence":"high","evidence":"2011019 muestra 09; 2014004 muestra 10; descriptor único de 10 glifos"},
                        "0x0604":{"role":"minute_number","confidence":"high","evidence":"2011019 muestra 30; 2014004 muestra 30; descriptor único de 10 glifos"},
                        "0x0804":{"role":"hour_tens_digit","confidence":"high","evidence":"2029002 primera cifra de 23:32"},
                        "0x0904":{"role":"hour_units_digit","confidence":"high","evidence":"2029002 segunda cifra de 23:32"},
                        "0x0A04":{"role":"minute_tens_digit","confidence":"high","evidence":"2029002 tercera cifra de 23:32"},
                        "0x0B04":{"role":"minute_units_digit","confidence":"high","evidence":"2029002 cuarta cifra de 23:32"},
                        "0x1002":{"role":"static_image_or_separator","confidence":"high","evidence":"separadores ':'/'-' y capas estáticas compartidas"},
                        "0x1102":{"role":"base_image_layer","confidence":"high","evidence":"capa base centrada presente en diales muestreados"},
                        "0x1502":{"role":"weather_icon","confidence":"high","evidence":"2011015/2014014: icono meteorológico superior izquierdo, 16 estados"},
                        "0x4004":{"role":"calories_value","confidence":"high","evidence":"2011017: 3210 junto a llama"},
                        "0x4104":{"role":"steps_value","confidence":"high","evidence":"2011017/2011028/2014004: contador junto a huellas/zapatilla"},
                        "0x4204":{"role":"heart_rate_value","confidence":"high","evidence":"2011017/2011101: valor junto a corazón/BPM"},
                        "0x0501":{"role":"analog_hour_hand","confidence":"high","evidence":"grupo de 3 agujas centradas 120,148"},
                        "0x0601":{"role":"analog_minute_hand","confidence":"high","evidence":"grupo de 3 agujas centradas 120,148"},
                        "0x0701":{"role":"analog_second_hand","confidence":"high","evidence":"grupo de 3 agujas centradas 120,148"}
                    }
                    rep["wf_manifest_v061"]["type_map"]=type_map
                    emit("TIPOS · 0204=mes · 0304=día · 0404=semana · 0504=hora · 0604=minuto")

                    emit("4/9 · Cerrando falsos candidatos de batería…")
                    rep["wf_manifest_v061"]["battery"].update({
                        "standard_gatt_battery_service_present":False,
                        "standard_gatt_evidence":"inventario E91A/FFC0/1800/1801/180A; 180F/2A19 ausentes",
                        "public_catalog_dials_scanned":104,
                        "default_catalog_dials":0,
                        "candidate_0x0204":"rejected: month_number",
                        "candidate_0x0504":"rejected: hour_number",
                        "candidate_0x0604":"rejected: minute_number",
                        "do_not_guess_0x4304":True
                    })

                    emit("5/9 · Fijando donantes OEM de recursos…")
                    donors={
                        "analog_hands":{"dial_id":"2011092","types":["0x0501","0x0601","0x0701"]},
                        "digital_time_individual_digits":{"dial_id":"2029002","types":["0x0804","0x0904","0x1002","0x0A04","0x0B04"]},
                        "digital_time_compact":{"dial_id":"2011019","types":["0x0504","0x1002","0x0604"]},
                        "steps_and_heart_digits":{"dial_id":"2011017","types":["0x4104","0x4204"]},
                        "weather_reference":{"dial_id":"2011015","types":["0x1502"]}
                    }

                    emit("6/9 · Generando manifiesto de esfera única 240×296…")
                    manifest={
                        "schema":"relojlab-single-face-v3",
                        "screen":{"width":240,"height":296,"center":[120,148]},
                        "visual_target":{
                            "background":"solid_black",
                            "analog":{"center":[120,148],"white_hour_minute_hands":True,"red_second_hand":True},
                            "digital_time":{
                                "placement":"upper_left",
                                "engine_variant":"individual_digits",
                                "types":["0x0804","0x0904","0x1002","0x0A04","0x0B04"],
                                "planned_centers":[[36,54],[54,45],[69,49],[84,45],[102,54]],
                                "curved_layout":True
                            },
                            "battery":{"placement":"upper_right","planned_center":[194,54],"dynamic":True,"wf_type":None,"status":"reserved; native binding not found"},
                            "steps":{"placement":"lower_left","type":"0x4104","planned_center":[56,245],"dynamic":True},
                            "heart_rate":{"placement":"lower_right","type":"0x4204","planned_center":[186,245],"dynamic":True}
                        },
                        "resource_donors":donors,
                        "battery_blocker":{
                            "runtime_opcode_0x03":"ACK-only on this firmware even after OEM bind",
                            "standard_0x180F":"absent",
                            "native_wf_binding":"not present in 104 public dials and no default dials returned",
                            "policy":"do not invent a field type"
                        },
                        "packaging":{
                            "wf_header_confirmed":True,
                            "descriptor_size":20,
                            "resource_pointer_model":"u16 stored relative to byte 2",
                            "par_encoder":"Bluetrum ParTool rawToPar identified",
                            "ready_for_offline_candidate_build":True,
                            "safe_to_transmit":False
                        },
                        "next_gate":[
                            "build offline WF candidate with black base + OEM donor resources",
                            "re-parse candidate and validate every pointer/declared size",
                            "only then design a controlled 0x83 transfer"
                        ]
                    }
                    rep["wf_manifest_v061"]["target_manifest"]=manifest
                    rep["wf_manifest_v061"]["resource_donors"]=donors

                    type_path=os.path.join(folder,"wf-type-map-v061.json")
                    manifest_path=os.path.join(folder,"single-face-manifest-v061.json")
                    with open(type_path,"w",encoding="utf-8") as fh:json.dump(type_map,fh,ensure_ascii=False,indent=2)
                    with open(manifest_path,"w",encoding="utf-8") as fh:json.dump(manifest,fh,ensure_ascii=False,indent=2)
                    rep["wf_manifest_v061"]["type_map_file"]=type_path
                    rep["wf_manifest_v061"]["manifest_file"]=manifest_path

                    emit("7/9 · DONANTES · agujas=2011092 · hora=2029002 · pasos/pulso=2011017")
                    emit("8/9 · BATERÍA · 0204/0504/0604 descartados; área superior derecha reservada, sin tipo inventado.")
                    rep["wf_manifest_v061"]["phase"]="complete"
                    emit("9/9 · V0.61 FINALIZADA · manifiesto listo para construir candidato WF offline · 0x83 NO TOCADO.")
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["wf_manifest_v061"]["phase"]="error"
                    self.report=rep;self.show()
                    append("V0.61 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.61 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                append("MAPA NORMALIZADO · 0204=mes · 0304=día · 0404=semana · 0504=hora · 0604=minuto.")
                append("MANIFIESTO V3 LISTO · siguiente versión construirá y validará un .WF candidato offline antes de cualquier 0x83.")
                self.status.set("V0.61 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=240),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.61 LISTA · 1º PREPARAR ESFERA ÚNICA V0.61; 2º COPIAR DIAGNÓSTICO. Normaliza fecha/hora, descarta falsos candidatos de batería y genera manifiesto de esfera única; 0x83 bloqueado.")'
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


# V0.61: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.61 aplicado")
