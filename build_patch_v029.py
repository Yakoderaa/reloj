from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.51.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.51")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.51 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="CAPTURAR CAMBIO DE ESFERA V0.51")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("CAPTURA V0.51 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.51 · CAPTURA CAMBIO DE ESFERA · durante la ventana indicada cambiá MANUALMENTE una sola esfera desde el reloj. La app compara DEVICE_INFO 0x02 + DIAL_INFO 0x84 antes/después y escucha B001. No instala ni borra esferas.")
            rep=self.base_report()
            rep["face_switch_capture"]={
                "phase":"before",
                "protocol":"E91A B002→B001",
                "before":{},
                "after":{},
                "events":[],
                "requests":[],
                "writes_safe_queries":0,
                "unknown_writes":0,
                "destructive_actions":0,
            }
            t0=time.monotonic()
            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def build_request(pid,opcode):
                pkt=bytearray(20)
                pkt[0]=0x00
                pkt[1]=pid & 0xff
                pkt[2]=0
                pkt[3]=0
                pkt[4]=0x03
                pkt[5]=opcode & 0xff
                pkt[8]=0
                pkt[9]=0
                return bytes(pkt)

            def decode(data):
                b=bytes(data)
                row={"t":round(time.monotonic()-t0,3),"hex":b.hex(),"length":len(b)}
                if len(b)>=10 and b[0]==0:
                    plen=b[8] | (b[9]<<8)
                    row.update({"kind":"header","pid":b[1],"continuations":b[2],"cmd_type":b[3],"send_type":b[4],"opcode":b[5],"payload_length":plen,"payload_first_hex":b[10:10+min(plen,10)].hex()})
                    if b[5]==0x02 and plen>=6:
                        pl=b[10:16]
                        row["device_info"]={"id_total":pl[0],"customer_id":pl[1],"hardware_id":pl[2],"code_id":pl[3],"picture_id":pl[4],"font_id":pl[5]}
                elif b:
                    row.update({"kind":"continuation","index":b[0],"payload_hex":b[1:].hex()})
                return row

            async def work():
                c=None
                events=[]
                try:
                    emit("1/9 · Conectando por la ruta robusta V0.50…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"
                    if not c.services.get_characteristic(b001) or not c.services.get_characteristic(b002):
                        raise RuntimeError("B001/B002 no disponibles en esta sesión.")

                    def rx(sender,data):
                        row=decode(data)
                        events.append(row)
                        rep["face_switch_capture"]["events"].append(row)
                        text="B001 RX · "+row["hex"]
                        if row.get("opcode") is not None:
                            text+=f" · op=0x{row['opcode']:02X} · send={row.get('send_type')} · len={row.get('payload_length')}"
                        if row.get("device_info"):
                            text+=" · DEVICE_INFO="+str(row["device_info"])
                        emit(text)

                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.4)
                    pid=0

                    async def query(label,opcode):
                        nonlocal pid
                        before_count=len(events)
                        pkt=build_request(pid,opcode)
                        rep["face_switch_capture"]["requests"].append({"label":label,"opcode":opcode,"hex":pkt.hex(),"t":round(time.monotonic()-t0,3)})
                        rep["face_switch_capture"]["writes_safe_queries"]+=1
                        emit("TX "+label+" · "+pkt.hex())
                        await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5)
                        pid=(pid+1)&0xff
                        await asyncio.sleep(1.8)
                        return events[before_count:]

                    emit("2/9 · Midiendo estado ANTES del cambio…")
                    before02=await query("ANTES · DEVICE_INFO 0x02",0x02)
                    before84=await query("ANTES · DIAL_INFO 0x84",0x84)
                    before_dev=next((x["device_info"] for x in reversed(before02) if x.get("device_info")),None)
                    rep["face_switch_capture"]["before"]={"device_info":before_dev,"device_frames":before02,"dial_frames":before84}
                    if before_dev:
                        emit("ANTES · picture_id="+str(before_dev["picture_id"])+" · font_id="+str(before_dev["font_id"]))
                    else:
                        emit("ANTES · DEVICE_INFO sin payload de 6 IDs.")

                    rep["face_switch_capture"]["phase"]="manual_switch_window"
                    emit("3/9 · AHORA CAMBIÁ UNA SOLA ESFERA DESDE EL RELOJ. Tenés 20 segundos.")
                    emit("IMPORTANTE · elegí otra esfera visible y dejala puesta; no toques botones de esta app.")
                    base_event_count=len(events)
                    for left in range(20,0,-1):
                        if left in (20,15,10,5,3,2,1):
                            self.ui_queue.put(lambda z=left:self.status.set(f"CAMBIÁ UNA ESFERA EN EL RELOJ · quedan {z}s"))
                            emit("ventana manual · quedan "+str(left)+"s")
                        await asyncio.sleep(1)
                    spontaneous=events[base_event_count:]
                    rep["face_switch_capture"]["spontaneous_during_switch"]=spontaneous
                    emit("4/9 · Ventana terminada · frames espontáneos="+str(len(spontaneous)))

                    rep["face_switch_capture"]["phase"]="after"
                    emit("5/9 · Midiendo estado DESPUÉS del cambio…")
                    after02=await query("DESPUÉS · DEVICE_INFO 0x02",0x02)
                    after84=await query("DESPUÉS · DIAL_INFO 0x84",0x84)
                    after_dev=next((x["device_info"] for x in reversed(after02) if x.get("device_info")),None)
                    rep["face_switch_capture"]["after"]={"device_info":after_dev,"device_frames":after02,"dial_frames":after84}
                    if after_dev:
                        emit("DESPUÉS · picture_id="+str(after_dev["picture_id"])+" · font_id="+str(after_dev["font_id"]))
                    else:
                        emit("DESPUÉS · DEVICE_INFO sin payload de 6 IDs.")

                    emit("6/9 · Comparando IDs…")
                    diff={}
                    if before_dev and after_dev:
                        for key in before_dev:
                            if before_dev.get(key)!=after_dev.get(key):
                                diff[key]={"before":before_dev.get(key),"after":after_dev.get(key)}
                    rep["face_switch_capture"]["id_diff"]=diff
                    emit("DIFERENCIAS DEVICE_INFO · "+str(diff if diff else "ninguna"))

                    emit("7/9 · Comparando respuestas DIAL_INFO…")
                    before_dial_hex=[x["hex"] for x in before84]
                    after_dial_hex=[x["hex"] for x in after84]
                    rep["face_switch_capture"]["dial_changed"]=before_dial_hex!=after_dial_hex
                    rep["face_switch_capture"]["dial_before_hex"]=before_dial_hex
                    rep["face_switch_capture"]["dial_after_hex"]=after_dial_hex
                    emit("DIAL_INFO cambió="+str(before_dial_hex!=after_dial_hex))

                    emit("8/9 · Clasificando tráfico espontáneo…")
                    rep["face_switch_capture"]["spontaneous_opcodes"]=sorted({x.get("opcode") for x in spontaneous if x.get("opcode") is not None})
                    emit("OPCODES ESPONTÁNEOS · "+str(rep["face_switch_capture"]["spontaneous_opcodes"]))

                    rep["face_switch_capture"]["phase"]="complete"
                    emit("9/9 · CAPTURA V0.51 FINALIZADA · cero escrituras desconocidas; cero borrados; cero instalaciones.")
                    try: await c.stop_notify(b001)
                    except Exception: pass
                    return rep
                finally:
                    if c:
                        try: await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex: rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["face_switch_capture"]["phase"]="error"
                    self.report=rep
                    self.show()
                    append("CAPTURA V0.51 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.51 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result
                self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                diff=result.get("face_switch_capture",{}).get("id_diff",{})
                spont=result.get("face_switch_capture",{}).get("spontaneous_during_switch",[])
                if diff or spont:
                    append("CAMBIO DETECTADO · ya tenemos una diferencia utilizable para aislar el selector de esfera.")
                else:
                    append("SIN CAMBIO TELEMETRADO · el reloj cambió visualmente pero no expuso selector por estas consultas; el diagnóstico igualmente sirve para la siguiente ruta.")
                self.status.set("V0.51 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=150),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.51 LISTA · 1º PREPARAR ESFERA ÚNICA V0.51; 2º COPIAR DIAGNÓSTICO. Medí antes/después: durante la ventana cambiá una sola esfera manualmente en el reloj.")'
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


# V0.51: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.51 aplicado")
