from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.52.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.52")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.52 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="MAPEAR DIAL_INFO V0.52")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("MAPEO V0.52 NO INICIADO · Bluetooth ocupado.")
                return
            append("V0.52 · DIAL_INFO REAL · corrige el reensamblado de fragmentos y compara 0x84 como REQUEST vs SEND sin payload. No toca DIAL_SYNC 0x83, no instala ni borra esferas.")
            rep=self.base_report()
            rep["dial_info_map"]={
                "phase":"start",
                "protocol":"WTWD/ApWatch E91A B002→B001",
                "requests":[],
                "events":[],
                "transactions":[],
                "destructive_actions":0,
                "dial_sync_0x83_writes":0,
                "unknown_writes":0
            }
            t0=time.monotonic()
            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def build_packet(pid,send_type,opcode,payload=b""):
                payload=bytes(payload)
                if len(payload)>10:
                    raise RuntimeError("V0.52 sólo usa consultas cortas.")
                pkt=bytearray(20)
                pkt[0]=0
                pkt[1]=pid&0xff
                pkt[2]=0
                pkt[3]=0
                pkt[4]=send_type&0xff
                pkt[5]=opcode&0xff
                pkt[8]=len(payload)&0xff
                pkt[9]=(len(payload)>>8)&0xff
                pkt[10:10+len(payload)]=payload
                return bytes(pkt)

            def decode_frame(data):
                b=bytes(data)
                row={"t":round(time.monotonic()-t0,3),"hex":b.hex(),"length":len(b)}
                if len(b)>=10 and b[0]==0:
                    plen=b[8] | (b[9]<<8)
                    row.update({
                        "kind":"header","pid":b[1],"continuations":b[2],
                        "cmd_type":b[3],"send_type":b[4],"opcode":b[5],
                        "payload_length":plen,
                        "payload_first_hex":b[10:10+min(plen,10)].hex()
                    })
                elif b:
                    row.update({"kind":"continuation","index":b[0],"payload_hex":b[1:].hex()})
                return row

            def reassemble(rows):
                out=[]
                i=0
                while i<len(rows):
                    h=rows[i]
                    if h.get("kind")!="header":
                        i+=1
                        continue
                    plen=int(h.get("payload_length",0))
                    payload=bytearray.fromhex(h.get("payload_first_hex",""))
                    used=[]
                    remaining=max(0,plen-len(payload))
                    j=i+1
                    expected=int(h.get("continuations",0))
                    while remaining>0 and j<len(rows) and len(used)<expected:
                        c=rows[j]
                        if c.get("kind")!="continuation":
                            break
                        raw=bytes.fromhex(c.get("payload_hex",""))
                        take=min(19,remaining,len(raw))
                        payload.extend(raw[:take])
                        used.append({"index":c.get("index"),"used_hex":raw[:take].hex(),"ignored_padding_hex":raw[take:].hex()})
                        remaining-=take
                        j+=1
                    item={
                        "t":h.get("t"),"opcode":h.get("opcode"),"pid":h.get("pid"),
                        "send_type":h.get("send_type"),"cmd_type":h.get("cmd_type"),
                        "declared_length":plen,"payload_hex":bytes(payload[:plen]).hex(),
                        "complete":len(payload)>=plen,"continuations_used":used
                    }
                    if item["opcode"]==0x02 and len(payload)>=6:
                        q=payload
                        item["device_info"]={
                            "id_total":q[0],"customer_id":q[1],"hardware_id":q[2],
                            "code_id":q[3],"picture_id":q[4],"font_id":q[5]
                        }
                    item["ack_only"]=bool(item["send_type"]==4 and plen==1 and bytes(payload[:1])==b"\\x01")
                    out.append(item)
                    i=max(i+1,j)
                return out

            async def work():
                c=None
                events=[]
                try:
                    emit("1/8 · Conectando…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"
                    if not c.services.get_characteristic(b001) or not c.services.get_characteristic(b002):
                        raise RuntimeError("B001/B002 no disponibles.")
                    def rx(sender,data):
                        row=decode_frame(data)
                        events.append(row)
                        rep["dial_info_map"]["events"].append(row)
                        msg="B001 RX · "+row["hex"]
                        if row.get("opcode") is not None:
                            msg+=f" · op=0x{row['opcode']:02X} · send={row.get('send_type')} · len={row.get('payload_length')}"
                        emit(msg)
                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.4)
                    pid=0
                    async def transact(label,send_type,opcode,wait=3.0):
                        nonlocal pid
                        start=len(events)
                        pkt=build_packet(pid,send_type,opcode)
                        rep["dial_info_map"]["requests"].append({"label":label,"send_type":send_type,"opcode":opcode,"hex":pkt.hex(),"t":round(time.monotonic()-t0,3)})
                        emit("TX "+label+" · "+pkt.hex())
                        await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5)
                        pid=(pid+1)&0xff
                        await asyncio.sleep(wait)
                        frames=events[start:]
                        packets=reassemble(frames)
                        tx={"label":label,"frames":frames,"packets":packets}
                        rep["dial_info_map"]["transactions"].append(tx)
                        emit(label+" · paquetes reensamblados="+str(len(packets)))
                        for q in packets:
                            emit("  RX PACKET · op="+("0x%02X"%q["opcode"] if q.get("opcode") is not None else "?")+" · send="+str(q.get("send_type"))+" · len="+str(q.get("declared_length"))+" · payload="+q.get("payload_hex","")+" · ack_only="+str(q.get("ack_only")))
                        return tx

                    emit("2/8 · DEVICE_INFO de control (REQUEST)…")
                    ctrl=await transact("CONTROL DEVICE_INFO 0x02 · REQUEST",3,0x02,3.2)
                    dev=next((x.get("device_info") for x in ctrl["packets"] if x.get("device_info")),None)
                    rep["dial_info_map"]["device_info"]=dev
                    if dev:
                        emit("DEVICE IDs · customer="+str(dev["customer_id"])+" hardware="+str(dev["hardware_id"])+" code="+str(dev["code_id"])+" picture="+str(dev["picture_id"])+" font="+str(dev["font_id"]))

                    emit("3/8 · DIAL_INFO 0x84 como REQUEST, protocolo OEM de consulta…")
                    qreq=await transact("DIAL_INFO 0x84 · REQUEST",3,0x84,4.0)

                    emit("4/8 · Pausa limpia…")
                    await asyncio.sleep(2)

                    emit("5/8 · DIAL_INFO 0x84 como SEND vacío; 0 bytes de contenido, sin 0x83…")
                    qsend=await transact("DIAL_INFO 0x84 · SEND VACÍO",1,0x84,4.0)

                    emit("6/8 · Repetición DEVICE_INFO para confirmar que no cambió el estado…")
                    ctrl2=await transact("CONTROL FINAL DEVICE_INFO 0x02 · REQUEST",3,0x02,3.0)
                    dev2=next((x.get("device_info") for x in ctrl2["packets"] if x.get("device_info")),None)
                    rep["dial_info_map"]["device_info_after"]=dev2
                    rep["dial_info_map"]["device_info_changed"]=bool(dev and dev2 and dev!=dev2)

                    def useful(tx):
                        return [x for x in tx["packets"] if x.get("opcode")==0x84 and not x.get("ack_only")]
                    rep["dial_info_map"]["request_useful_packets"]=useful(qreq)
                    rep["dial_info_map"]["send_useful_packets"]=useful(qsend)
                    rep["dial_info_map"]["request_has_data"]=bool(rep["dial_info_map"]["request_useful_packets"])
                    rep["dial_info_map"]["send_has_data"]=bool(rep["dial_info_map"]["send_useful_packets"])

                    emit("7/8 · RESULTADO · REQUEST datos="+str(rep["dial_info_map"]["request_has_data"])+" · SEND datos="+str(rep["dial_info_map"]["send_has_data"])+" · DEVICE cambió="+str(rep["dial_info_map"]["device_info_changed"]))
                    rep["dial_info_map"]["phase"]="complete"
                    emit("8/8 · MAPEO V0.52 FINALIZADO · 0x83 NO TOCADO · cero borrados · cero instalaciones.")
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
                    rep["dial_info_map"]["phase"]="error"
                    self.report=rep
                    self.show()
                    append("MAPEO V0.52 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.52 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result
                self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                if result.get("dial_info_map",{}).get("request_has_data") or result.get("dial_info_map",{}).get("send_has_data"):
                    append("DIAL_INFO REAL DETECTADO · ya tenemos una respuesta 0x84 que no es sólo ACK.")
                else:
                    append("0x84 SIGUE SIENDO ACK-ONLY · la próxima ruta será obtener el paquete real de dial desde el backend/captura OEM, sin adivinar 0x83.")
                self.status.set("V0.52 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=120),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.52 LISTA · 1º PREPARAR ESFERA ÚNICA V0.52; 2º COPIAR DIAGNÓSTICO. Prueba segura 0x84 REQUEST/SEND con reensamblado exacto; no toca DIAL_SYNC 0x83.")'
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


# V0.52: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.52 aplicado")
