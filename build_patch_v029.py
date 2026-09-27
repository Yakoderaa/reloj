from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.67.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.67")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.67 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="VALIDAR BIG-SEND OFFLINE V0.67")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            append("V0.67 · BIG-SEND OFFLINE · divide el zlib completo en mensajes WTWD, reconstruye cada payload desde sus frames y valida round-trip contra el WF original. No escribe al reloj.")
            rep=self.base_report()
            rep["big_send_offline"]={"phase":"build","candidate":{},"strategies":[],"writes_to_watch":0}
            t0=time.monotonic()

            def emit(msg):
                line=f"+{time.monotonic()-t0:06.2f}s · {msg}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def read_candidate():
                import zlib
                path=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v062","single-face-proof-v062.bin")
                if not os.path.exists(path):raise RuntimeError("Falta single-face-proof-v062.bin")
                with open(path,"rb") as fh:raw=fh.read()
                if len(raw)<54 or raw[:2]!=b"WF":raise RuntimeError("WF inválido")
                packed=zlib.compress(raw,9)
                return path,raw,packed

            def build_frames(pid,payload):
                payload=bytes(payload);n=len(payload)
                if n>4855:raise RuntimeError("payload >4855")
                if n<=10:
                    h=bytearray(20);h[1]=pid&0xff;h[4]=1;h[5]=0x83;h[8]=n&0xff;h[9]=(n>>8)&0xff;h[10:10+n]=payload
                    return [bytes(h)]
                rem=n-10;frags=rem//19+(1 if rem%19 else 0)
                h=bytearray(20);h[1]=pid&0xff;h[2]=frags;h[4]=1;h[5]=0x83;h[8]=n&0xff;h[9]=(n>>8)&0xff;h[10:20]=payload[:10]
                out=[bytes(h)];pos=10
                for i in range(frags):
                    c=bytearray(20);c[0]=i+1
                    part=payload[pos:pos+19];c[1:1+len(part)]=part
                    out.append(bytes(c));pos+=len(part)
                return out

            def rebuild(frames):
                h=frames[0];n=h[8]|(h[9]<<8)
                out=bytearray(h[10:10+min(n,10)])
                for c in frames[1:]:
                    need=n-len(out)
                    if need<=0:break
                    out.extend(c[1:1+min(19,need)])
                return bytes(out[:n])

            async def work():
                import zlib
                emit("1/6 · Cargando candidato V0.62…")
                path,raw,packed=await asyncio.to_thread(read_candidate)
                rep["big_send_offline"]["candidate"]={
                    "path":path,"raw_size":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "zlib_size":len(packed),"zlib_sha256":hashlib.sha256(packed).hexdigest()
                }

                emit("2/6 · Probando tamaños de mensaje…")
                for block in [64,128,256,300,512,1024,2048,4096,4855]:
                    pieces=[packed[i:i+block] for i in range(0,len(packed),block)]
                    rebuilt=[]
                    total_frames=0
                    message_rows=[]
                    for idx,piece in enumerate(pieces):
                        frames=build_frames(idx&0xff,piece)
                        again=rebuild(frames)
                        rebuilt.append(again)
                        total_frames+=len(frames)
                        if idx<4 or idx==len(pieces)-1:
                            message_rows.append({"index":idx,"payload_length":len(piece),"frame_count":len(frames),
                                                 "sha256":hashlib.sha256(piece).hexdigest(),
                                                 "first_frame_hex":frames[0].hex()})
                    joined=b"".join(rebuilt)
                    try:
                        roundtrip=zlib.decompress(joined)
                        decompress_ok=roundtrip==raw
                    except Exception:
                        decompress_ok=False
                    row={"block_size":block,"message_count":len(pieces),"total_ble_frames":total_frames,
                         "zlib_sha256_match":hashlib.sha256(joined).hexdigest()==hashlib.sha256(packed).hexdigest(),
                         "decompress_matches_wf":decompress_ok,"sample_messages":message_rows}
                    row["all_pass"]=row["zlib_sha256_match"] and row["decompress_matches_wf"]
                    rep["big_send_offline"]["strategies"].append(row)

                emit("3/6 · Seleccionando estrategia conservadora…")
                valid=[x for x in rep["big_send_offline"]["strategies"] if x["all_pass"]]
                if not valid:raise RuntimeError("ninguna estrategia reconstruye el stream")
                preferred=next((x for x in valid if x["block_size"]==300),valid[0])
                rep["big_send_offline"]["preferred"]=preferred
                emit("PREFERIDA · 300 bytes · mensajes="+str(preferred["message_count"])+" · frames="+str(preferred["total_ble_frames"]))

                emit("4/6 · Validando round-trip completo…")
                rep["big_send_offline"]["all_strategies_pass"]=all(x["all_pass"] for x in rep["big_send_offline"]["strategies"])
                if not rep["big_send_offline"]["all_strategies_pass"]:raise RuntimeError("alguna estrategia falló")

                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v067")
                os.makedirs(folder,exist_ok=True)
                report_path=os.path.join(folder,"big-send-offline-v067.json")
                with open(report_path,"w",encoding="utf-8") as fh:
                    json.dump(rep["big_send_offline"],fh,ensure_ascii=False,indent=2)
                rep["big_send_offline"]["report_file"]=report_path
                rep["big_send_offline"]["phase"]="complete"

                emit("5/6 · RESULTADO · todas las estrategias reconstruyen exactamente el mismo zlib/WF.")
                emit("6/6 · V0.67 FINALIZADA · big-send packetizado offline; 0 escrituras al reloj.")
                return rep

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["big_send_offline"]["phase"]="error"
                    self.report=rep;self.show()
                    append("V0.67 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.67 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                x=result["big_send_offline"]["preferred"]
                append("BIG-SEND OFFLINE OK · bloque="+str(x["block_size"])+" · mensajes="+str(x["message_count"])+" · frames="+str(x["total_ble_frames"]))
                self.status.set("V0.67 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=60),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.67 LISTA · 1º PREPARAR ESFERA ÚNICA V0.67; 2º COPIAR DIAGNÓSTICO. Valida offline la secuencia completa de mensajes 0x83 y reconstrucción exacta del zlib/WF.")'
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


# V0.67: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.67 aplicado")
