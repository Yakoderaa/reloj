from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.64.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.64")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.64 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="AISLAR CANAL WF V0.64")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("V0.64 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.64 · AISLAMIENTO FFC0/B002 · escucha FFC2 y B001 mientras ejecuta sólo DEVICE_INFO/DIAL_INFO ya verificados. Prepara segmentación 0x83 offline; no escribe FFC1 ni 0x83.")
            rep=self.base_report()
            rep["channel_isolation"]={
                "phase":"candidate",
                "candidate":{},
                "compression":{},
                "offline_segments":[],
                "gatt":{},
                "b001_rx":[],
                "ffc2_rx":[],
                "safe_control_writes":[],
                "ffc1_writes":0,
                "dial_sync_0x83_writes":0,
                "firmware_data_writes":0,
                "destructive_actions":0
            }
            t0=time.monotonic()

            def emit(msg):
                line=f"+{time.monotonic()-t0:06.2f}s · {msg}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def build_request(pid,opcode):
                pkt=bytearray(20)
                pkt[0]=0;pkt[1]=pid&0xff;pkt[2]=0;pkt[3]=0;pkt[4]=3;pkt[5]=opcode&0xff
                return bytes(pkt)

            def read_candidate():
                path=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v062","single-face-proof-v062.bin")
                if not os.path.exists(path):raise RuntimeError("Falta single-face-proof-v062.bin")
                with open(path,"rb") as fh:data=fh.read()
                if len(data)<54 or data[:2]!=b"WF":raise RuntimeError("WF V0.62 inválido")
                if int.from_bytes(data[0x30:0x34],"little")!=len(data):raise RuntimeError("tamaño WF inconsistente")
                return path,data

            async def work():
                import zlib
                emit("1/9 · Cargando candidato V0.62…")
                path,raw=await asyncio.to_thread(read_candidate)
                packed=zlib.compress(raw,9)
                rep["channel_isolation"]["candidate"]={"path":path,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
                rep["channel_isolation"]["compression"]={"format":"zlib","level":9,"size":len(packed),"sha256":hashlib.sha256(packed).hexdigest(),"first_16_hex":packed[:16].hex()}

                emit("2/9 · Preparando segmentación lógica OFFLINE…")
                max_payload=4855
                segments=[]
                pos=0;idx=0
                while pos<len(packed):
                    chunk=packed[pos:pos+max_payload]
                    segments.append({"index":idx,"offset":pos,"length":len(chunk),
                                     "sha256":hashlib.sha256(chunk).hexdigest(),
                                     "first_16_hex":chunk[:16].hex()})
                    pos+=len(chunk);idx+=1
                rep["channel_isolation"]["offline_segments"]=segments
                emit("SEGMENTOS · "+str([x["length"] for x in segments])+" · total="+str(len(segments)))

                emit("3/9 · Conectando y enumerando FFC0…")
                c=None
                try:
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"
                    ffc1="f000ffc1-0451-4000-b000-000000000000"
                    ffc2="f000ffc2-0451-4000-b000-000000000000"

                    flat={}
                    for svc in c.services:
                        for ch in svc.characteristics:
                            flat[str(ch.uuid).lower()]={
                                "handle":getattr(ch,"handle",None),
                                "properties":list(getattr(ch,"properties",[]) or []),
                                "descriptors":[{"handle":getattr(d,"handle",None),"uuid":str(getattr(d,"uuid","")).lower()} for d in getattr(ch,"descriptors",[]) or []]
                            }
                    rep["channel_isolation"]["gatt"]={
                        "ffc1":flat.get(ffc1),"ffc2":flat.get(ffc2),
                        "classic_ti_oad_names":{"ffc1":"Image Identify","ffc2":"Image Block"},
                        "classic_oad_compatible":bool(flat.get(ffc1) and flat.get(ffc2) and
                            any(x.startswith("write") for x in flat[ffc1]["properties"]) and
                            any(x.startswith("write") for x in flat[ffc2]["properties"])),
                        "observed_direction":"FFC1 phone→device; FFC2 device→phone" if flat.get(ffc1) and flat.get(ffc2) else "incomplete"
                    }
                    emit("FFC1 · "+str(flat.get(ffc1)))
                    emit("FFC2 · "+str(flat.get(ffc2)))

                    def rx_b001(sender,data):
                        h=bytes(data).hex();rep["channel_isolation"]["b001_rx"].append(h);emit("B001 RX · "+h)
                    def rx_ffc2(sender,data):
                        h=bytes(data).hex();rep["channel_isolation"]["ffc2_rx"].append(h);emit("FFC2 RX · "+h)

                    emit("4/9 · Suscribiendo B001 + FFC2; ningún dato hacia FFC1…")
                    await asyncio.wait_for(c.start_notify(b001,rx_b001),timeout=6)
                    await asyncio.wait_for(c.start_notify(ffc2,rx_ffc2),timeout=6)
                    await asyncio.sleep(3)

                    emit("5/9 · DEVICE_INFO 0x02 por B002 (consulta conocida)…")
                    pkt=build_request(0,0x02)
                    rep["channel_isolation"]["safe_control_writes"].append({"label":"DEVICE_INFO","characteristic":"B002","hex":pkt.hex()})
                    await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5)
                    await asyncio.sleep(4)

                    emit("6/9 · DIAL_INFO 0x84 por B002 (REQUEST conocido)…")
                    pkt=build_request(1,0x84)
                    rep["channel_isolation"]["safe_control_writes"].append({"label":"DIAL_INFO","characteristic":"B002","hex":pkt.hex()})
                    await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5)
                    await asyncio.sleep(5)

                    try:await c.stop_notify(ffc2)
                    except Exception:pass
                    try:await c.stop_notify(b001)
                    except Exception:pass
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

                emit("7/9 · Clasificando independencia de canales…")
                ffc_count=len(rep["channel_isolation"]["ffc2_rx"])
                b_count=len(rep["channel_isolation"]["b001_rx"])
                g=rep["channel_isolation"]["gatt"]
                conclusion={
                    "b001_received_control_responses":b_count>0,
                    "ffc2_received_during_safe_wtwd_queries":ffc_count>0,
                    "classic_ti_oad_property_match":g.get("classic_oad_compatible"),
                    "route_assessment":(
                        "FFC2 participa en tráfico aun sin FFC1; revisar contenido antes de descartar"
                        if ffc_count>0 else
                        "FFC0 permanece separado durante control WTWD; no hay evidencia de que transporte DIAL_SYNC"
                    ),
                    "b002_big_send_still_primary_candidate":ffc_count==0
                }
                rep["channel_isolation"]["conclusion"]=conclusion
                emit("RESULTADO · B001="+str(b_count)+" frames · FFC2="+str(ffc_count)+" frames")
                emit("RUTA · "+conclusion["route_assessment"])

                emit("8/9 · Guardando plan offline…")
                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v064")
                os.makedirs(folder,exist_ok=True)
                report_path=os.path.join(folder,"channel-isolation-v064.json")
                with open(report_path,"w",encoding="utf-8") as fh:
                    json.dump(rep["channel_isolation"],fh,ensure_ascii=False,indent=2)
                rep["channel_isolation"]["report_file"]=report_path
                rep["channel_isolation"]["phase"]="complete"

                emit("9/9 · V0.64 FINALIZADA · FFC1 writes=0 · 0x83 writes=0 · firmware data writes=0.")
                return rep

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["channel_isolation"]["phase"]="error"
                    self.report=rep;self.show()
                    append("V0.64 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.64 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                x=result["channel_isolation"]["conclusion"]
                append("AISLAMIENTO COMPLETO · "+x["route_assessment"])
                self.status.set("V0.64 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=120),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.64 LISTA · 1º PREPARAR ESFERA ÚNICA V0.64; 2º COPIAR DIAGNÓSTICO. Aísla FFC0 frente a B002/B001 y prepara 5 segmentos comprimidos offline; sin FFC1/0x83.")'
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


# V0.64: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.64 aplicado")
