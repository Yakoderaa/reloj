from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.63.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.63")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.63 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="PREPARAR TRANSPORTE WF V0.63")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("V0.63 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.63 · PREFLIGHT DE TRANSPORTE · valida el WF V0.62, calcula compresión/CRC/límites y enumera canales GATT/FOTA. NO envía 0x83 ni datos de firmware.")
            rep=self.base_report()
            rep["transport_preflight"]={
                "phase":"candidate",
                "candidate":{},
                "compression":{},
                "master_packet_limits":{},
                "gatt_inventory":[],
                "route_candidates":[],
                "dial_sync_0x83_writes":0,
                "fota_data_writes":0,
                "destructive_actions":0
            }
            t0=time.monotonic()

            def emit(msg):
                line=f"+{time.monotonic()-t0:06.2f}s · {msg}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def crc16_8005(data):
                crc=0
                for bv in data:
                    crc ^= (bv << 8)
                    for _ in range(8):
                        crc=((crc<<1)^0x8005)&0xffff if (crc&0x8000) else (crc<<1)&0xffff
                return crc

            def read_candidate():
                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v062")
                path=os.path.join(folder,"single-face-proof-v062.bin")
                if not os.path.exists(path):
                    raise RuntimeError("No encuentro single-face-proof-v062.bin. Ejecutá primero V0.62.")
                with open(path,"rb") as fh:data=fh.read()
                if len(data)<54 or data[:2]!=b"WF":raise RuntimeError("candidato V0.62 inválido")
                declared=int.from_bytes(data[0x30:0x34],"little")
                width=int.from_bytes(data[0x2a:0x2c],"little")
                height=int.from_bytes(data[0x2c:0x2e],"little")
                count=int.from_bytes(data[0x2e:0x30],"little")
                if declared!=len(data) or (width,height)!=(240,296) or count!=10:
                    raise RuntimeError("el candidato V0.62 no conserva su estructura esperada")
                return path,data

            async def work():
                import zlib,gzip
                emit("1/8 · Abriendo candidato V0.62…")
                path,data=await asyncio.to_thread(read_candidate)
                sha=hashlib.sha256(data).hexdigest()
                crc=crc16_8005(data)
                rep["transport_preflight"]["candidate"]={
                    "path":path,"size":len(data),"sha256":sha,"crc16_8005":f"0x{crc:04X}",
                    "declared_size":int.from_bytes(data[0x30:0x34],"little"),
                    "resolution":[int.from_bytes(data[0x2a:0x2c],"little"),int.from_bytes(data[0x2c:0x2e],"little")],
                    "element_count":int.from_bytes(data[0x2e:0x30],"little")
                }
                emit("CANDIDATO · "+str(len(data))+" bytes · "+sha)

                emit("2/8 · Calculando variantes de compresión…")
                variants={
                    "raw":data,
                    "zlib_level1":zlib.compress(data,1),
                    "zlib_level6":zlib.compress(data,6),
                    "zlib_level9":zlib.compress(data,9),
                    "gzip_level9":gzip.compress(data,compresslevel=9,mtime=0)
                }
                comp={}
                for name,blob in variants.items():
                    comp[name]={
                        "size":len(blob),
                        "ratio":round(len(blob)/len(data),4),
                        "sha256":hashlib.sha256(blob).hexdigest(),
                        "first_24_hex":blob[:24].hex()
                    }
                rep["transport_preflight"]["compression"]=comp
                emit("COMPRESIÓN · "+str({k:v["size"] for k,v in comp.items()}))

                emit("3/8 · Verificando límite del framing maestro WTWD…")
                max_payload=10+255*19
                limits={
                    "header_first_payload_bytes":10,
                    "continuation_payload_bytes":19,
                    "continuation_count_field_bits":8,
                    "max_continuations":255,
                    "max_payload_single_master_message":max_payload,
                    "candidate_raw_fits_single_master_message":len(data)<=max_payload,
                    "variants_fit_single_master_message":{k:len(v)<=max_payload for k,v in variants.items()},
                    "raw_20_byte_frames_if_naive":1+max(0,(len(data)-10+18)//19)
                }
                rep["transport_preflight"]["master_packet_limits"]=limits
                emit("MASTER · máximo="+str(max_payload)+" · raw_fits="+str(limits["candidate_raw_fits_single_master_message"]))

                emit("4/8 · Conectando sólo para inventariar GATT…")
                c=None
                try:
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    rows=[]
                    for svc in c.services:
                        srow={"uuid":str(svc.uuid).lower(),"characteristics":[]}
                        for ch in svc.characteristics:
                            crow={
                                "uuid":str(ch.uuid).lower(),
                                "handle":getattr(ch,"handle",None),
                                "properties":list(getattr(ch,"properties",[]) or [])
                            }
                            srow["characteristics"].append(crow)
                        rows.append(srow)
                    rep["transport_preflight"]["gatt_inventory"]=rows

                    flat={ch["uuid"]:ch for s in rows for ch in s["characteristics"]}
                    probes={
                        "b001":"0000b001-0000-1000-8000-00805f9b34fb",
                        "b002":"0000b002-0000-1000-8000-00805f9b34fb",
                        "b003":"0000b003-0000-1000-8000-00805f9b34fb",
                        "b005":"0000b005-0000-1000-8000-00805f9b34fb",
                        "ffc1":"f000ffc1-0451-4000-b000-000000000000",
                        "ffc2":"f000ffc2-0451-4000-b000-000000000000"
                    }
                    presence={k:(u in flat) for k,u in probes.items()}
                    rep["transport_preflight"]["characteristic_presence"]=presence
                    emit("GATT · "+str(presence))
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

                emit("5/8 · Clasificando rutas posibles…")
                presence=rep["transport_preflight"].get("characteristic_presence",{})
                routes=[]
                if presence.get("ffc1") or presence.get("ffc2"):
                    routes.append({"route":"FFC0 family","status":"present","action":"inspect handshake before any data"})
                if presence.get("b003") or presence.get("b005"):
                    routes.append({"route":"ZK/OTA side channel","status":"present","action":"inspect handshake before any data"})
                if presence.get("b002"):
                    routes.append({"route":"B002 WTWD big-send","status":"present","action":"0x83 requires multi-message state machine; single master payload is insufficient"})
                rep["transport_preflight"]["route_candidates"]=routes

                emit("6/8 · Generando plan de transporte sin escrituras…")
                smallest=min(comp.items(),key=lambda kv:kv[1]["size"])
                plan={
                    "candidate_sha256":sha,
                    "smallest_variant":smallest[0],
                    "smallest_variant_size":smallest[1]["size"],
                    "single_master_limit":max_payload,
                    "needs_large_send_state_machine":smallest[1]["size"]>max_payload,
                    "known_oem_fact":"DIAL_SYNC=0x83 and OEM app marks dial transfer as big-send/compressed",
                    "safe_next_step":"identify start/clear/data/end/CRC handshake on the present large-transfer route before sending candidate bytes",
                    "no_transfer_performed":True
                }
                rep["transport_preflight"]["plan"]=plan
                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v063")
                os.makedirs(folder,exist_ok=True)
                report_path=os.path.join(folder,"transport-preflight-v063.json")
                with open(report_path,"w",encoding="utf-8") as fh:
                    json.dump(rep["transport_preflight"],fh,ensure_ascii=False,indent=2)
                rep["transport_preflight"]["report_file"]=report_path

                emit("7/8 · PLAN · variante mínima="+smallest[0]+" ("+str(smallest[1]["size"])+" bytes) · big-send="+str(plan["needs_large_send_state_machine"]))
                rep["transport_preflight"]["phase"]="complete"
                emit("8/8 · V0.63 FINALIZADA · transporte caracterizado sin 0x83/FOTA DATA.")
                return rep

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["transport_preflight"]["phase"]="error"
                    self.report=rep;self.show()
                    append("V0.63 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.63 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                p=result["transport_preflight"]["plan"]
                append("PREFLIGHT LISTO · big-send requerido="+str(p["needs_large_send_state_machine"])+" · ninguna transferencia ejecutada.")
                self.status.set("V0.63 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=120),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.63 LISTA · 1º PREPARAR ESFERA ÚNICA V0.63; 2º COPIAR DIAGNÓSTICO. Calcula compresión/CRC/límites y enumera canales GATT para el transporte WF; sin 0x83/FOTA DATA.")'
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


# V0.63: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.63 aplicado")
