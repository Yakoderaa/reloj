from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.69.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.69")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.69 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="PROBAR BLOQUE 300B V0.69")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("V0.69 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.69 · BLOQUE 300B · envía sólo el primer bloque de 300 bytes del zlib del candidato, espera ACK 0x83 y hace postcheck. No envía bloques posteriores ni cierre.")
            rep=self.base_report()
            rep["block300_probe"]={"phase":"candidate","payload_bytes_written":0,"dial_sync_writes":0,"destructive_actions":0}
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

            def build(pid,cmd_type,send_type,opcode,payload=b""):
                payload=bytes(payload);n=len(payload)
                if n>4855:raise RuntimeError("payload > 4855")
                h=bytearray(20)
                if n<=10:
                    h[1]=pid&255;h[3]=cmd_type;h[4]=send_type;h[5]=opcode;h[8]=n&255;h[9]=(n>>8)&255;h[10:10+n]=payload
                    return [bytes(h)]
                rem=n-10;frags=(rem+18)//19
                h[1]=pid&255;h[2]=frags;h[3]=cmd_type;h[4]=send_type;h[5]=opcode;h[8]=n&255;h[9]=(n>>8)&255;h[10:20]=payload[:10]
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
                    bytes([0x04,0x00,0x67,0x00]),
                    bytes([12,0,0x68])+tm,
                    bytes([0x04,0x00,0x6D,0x01]),
                    bytes([0x04,0x00,0x7A,0x01]),
                    bytes([0x08,0x00,0x7C,0x01,0xFF,0xFF,0xFF,0xFF]),
                    bytes([0x05,0x00,0x78,0x01,0x00])
                ]
                body=b"".join(subs);total=len(body)+1
                return bytes([total&255,(total>>8)&255,len(subs)])+body

            async def work():
                emit("1/9 · Cargando candidato…")
                path,raw,packed=await asyncio.to_thread(read_candidate)
                payload=packed[:300]
                rep["block300_probe"]["candidate"]={"path":path,"raw_size":len(raw),"zlib_size":len(packed),"zlib_sha256":hashlib.sha256(packed).hexdigest()}
                rep["block300_probe"]["payload_sha256"]=hashlib.sha256(payload).hexdigest()

                c=None;events=[];pid=0
                try:
                    emit("2/9 · Conectando…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb";b002="0000b002-0000-1000-8000-00805f9b34fb"
                    def rx(sender,data):
                        events.append(bytes(data));emit("B001 RX · "+bytes(data).hex())
                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.3)

                    async def tx(op,payload=b"",send_type=1,wait=1.0):
                        nonlocal pid
                        start=len(events);frames=build(pid,0,send_type,op,payload)
                        for fr in frames:
                            await asyncio.wait_for(c.write_gatt_char(b002,fr,response=False),timeout=5)
                            await asyncio.sleep(.08)
                        pid=(pid+1)&255
                        await asyncio.sleep(wait)
                        return events[start:],frames

                    emit("3/9 · DEVICE_INFO + bind OEM…")
                    await tx(0x02,b"",3,1.8)
                    await tx(0x6E,sync_payload(),1,1.4)
                    await tx(0x1D,bytes([1]),1,.8)
                    await tx(0x1F,bytes([8]),1,1.4)

                    emit("4/9 · 0x83 · primer bloque 300 bytes · 17 frames BLE…")
                    rx_frames,tx_frames=await tx(0x83,payload,1,6.0)
                    ack=any(len(x)>=11 and x[0]==0 and x[4]==4 and x[5]==0x83 and x[8]==1 and x[10]==1 for x in rx_frames)
                    connected=bool(getattr(c,"is_connected",False))
                    rep["block300_probe"]["tx_frames"]=[x.hex() for x in tx_frames]
                    rep["block300_probe"]["rx_frames"]=[x.hex() for x in rx_frames]
                    rep["block300_probe"]["frame_count"]=len(tx_frames)
                    rep["block300_probe"]["ack01"]=ack
                    rep["block300_probe"]["connected_after_block"]=connected
                    rep["block300_probe"]["payload_bytes_written"]=len(payload)
                    rep["block300_probe"]["dial_sync_writes"]=1
                    emit("BLOQUE · ACK01="+str(ack)+" · conectado="+str(connected))

                    emit("5/9 · Esperando estabilidad…")
                    await asyncio.sleep(6.0)
                    stable=bool(getattr(c,"is_connected",False))
                    rep["block300_probe"]["stable_after_wait"]=stable

                    emit("6/9 · DEVICE_INFO postcheck…")
                    post=len(events)
                    await tx(0x02,b"",3,2.5)
                    emit("7/9 · DIAL_INFO postcheck…")
                    await tx(0x84,b"",3,3.5)
                    post_frames=events[post:]
                    rep["block300_probe"]["postcheck_rx"]=[x.hex() for x in post_frames]
                    post_ok=len(post_frames)>0
                    rep["block300_probe"]["classification"]="block300_accepted" if ack and stable and post_ok else "block300_not_fully_accepted"

                    emit("8/9 · CLASIFICACIÓN · "+rep["block300_probe"]["classification"])
                    rep["block300_probe"]["phase"]="complete"
                    emit("9/9 · V0.69 FINALIZADA · enviados 300/"+str(len(packed))+" bytes; no hubo segundo bloque ni cierre.")
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["block300_probe"]["phase"]="error";self.report=rep;self.show()
                    append("V0.69 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.69 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                append("BLOQUE 300B · "+result["block300_probe"]["classification"]+" · enviados 300 bytes.")
                self.status.set("V0.69 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=150),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.69 LISTA · 1º PREPARAR ESFERA ÚNICA V0.69; 2º COPIAR DIAGNÓSTICO. Prueba el primer bloque de 300 bytes por 0x83, espera ACK y verifica estabilidad/postcheck.")'
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


# V0.69: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.69 aplicado")
