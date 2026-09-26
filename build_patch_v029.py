from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.35.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.35")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.35 - PERFILAR OAD")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.35 NO INICIADA · Bluetooth ocupado. Esperá a que termine la operación actual y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.35.")
                return
            append("PRUEBA V0.35: identifica hardware/firmware y perfila respuestas FFC1→FFC2 sin enviar bloques de firmware.")
            async def work():
                c=None; report=[]; address=self.selected.get("address") or getattr(self.selected.get("device"),"address",None)
                t0=time.monotonic()
                B001="0000b001-0000-1000-8000-00805f9b34fb"
                B002="0000b002-0000-1000-8000-00805f9b34fb"
                FFC1="f000ffc1-0451-4000-b000-000000000000"
                FFC2="f000ffc2-0451-4000-b000-000000000000"
                HANDSHAKE=bytes.fromhex("00ff000101150000010010000000010000000000")
                DIS=[
                    ("SYSTEM_ID","00002a23-0000-1000-8000-00805f9b34fb"),
                    ("MODEL","00002a24-0000-1000-8000-00805f9b34fb"),
                    ("SERIAL","00002a25-0000-1000-8000-00805f9b34fb"),
                    ("FIRMWARE","00002a26-0000-1000-8000-00805f9b34fb"),
                    ("HARDWARE","00002a27-0000-1000-8000-00805f9b34fb"),
                    ("SOFTWARE","00002a28-0000-1000-8000-00805f9b34fb"),
                    ("MANUFACTURER","00002a29-0000-1000-8000-00805f9b34fb"),
                    ("IEEE_11073","00002a2a-0000-1000-8000-00805f9b34fb"),
                    ("PNP_ID","00002a50-0000-1000-8000-00805f9b34fb"),
                ]
                def emit(m):
                    stamp=time.monotonic()-t0
                    line=f"+{stamp:06.2f}s · {m}"
                    report.append(line)
                    self.root.after(0,lambda x=line:(append(x),self.status.set(x)))
                async def connect_fresh(label,window=80):
                    deadline=time.monotonic()+window; attempt=0
                    while time.monotonic()<deadline:
                        try:
                            target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=4),timeout=6)
                            if target is None:
                                await asyncio.sleep(.4); continue
                            attempt+=1
                            emit(f"{label} · intento {attempt} · DEVICE + CACHE OFF")
                            client=BleakClient(target,timeout=14,winrt={"use_cached_services":False})
                            try:
                                await asyncio.wait_for(client.connect(),timeout=16)
                                if not client.is_connected:
                                    raise RuntimeError("is_connected=False")
                                emit(f"{label} · GATT OK · MTU={getattr(client,'mtu_size','?')}")
                                return client
                            except Exception as ex:
                                emit(f"{label} · intento {attempt} FALLÓ · {type(ex).__name__}: {ex}")
                                try: await asyncio.wait_for(client.disconnect(),timeout=2)
                                except Exception: pass
                        except Exception as ex:
                            emit(f"{label} · búsqueda parcial · {type(ex).__name__}: {ex}")
                        await asyncio.sleep(.5)
                    raise RuntimeError(label+" · no conectó dentro de la ventana")
                async def disconnect_clean(client):
                    if client:
                        try: await asyncio.wait_for(client.disconnect(),timeout=4)
                        except Exception: pass

                b001_rx=[]; ffc2_rx=[]; probe_results=[]
                current_probe={"label":"—","hex":"—"}
                try:
                    emit("1/8 · Abriendo GATT fresco.")
                    c=await connect_fresh("CONEXIÓN")
                    emit("2/8 · Estableciendo handshake B002 validado.")
                    def b001_cb(sender,data):
                        h=bytes(data).hex(); b001_rx.append((time.monotonic()-t0,h))
                        self.root.after(0,lambda x=h:append("B001 RX "+x))
                    await asyncio.wait_for(c.start_notify(B001,b001_cb),timeout=5)
                    await asyncio.wait_for(c.write_gatt_char(B002,HANDSHAKE,response=False),timeout=4)
                    emit("TX B002 HANDSHAKE · "+HANDSHAKE.hex())
                    ack_deadline=time.monotonic()+4
                    while time.monotonic()<ack_deadline and not b001_rx:
                        await asyncio.sleep(.1)
                    emit("HANDSHAKE ACK="+str(b001_rx[-1] if b001_rx else None))
                    if not c.is_connected:
                        raise RuntimeError("GATT cayó durante handshake")

                    emit("3/8 · Leyendo identidad estándar del dispositivo.")
                    for label,uuid in DIS:
                        try:
                            ch=c.services.get_characteristic(uuid)
                            if not ch:
                                emit(label+" · no presente"); continue
                            raw=bytes(await asyncio.wait_for(c.read_gatt_char(ch),timeout=4))
                            txt=raw.decode("utf-8",errors="replace").strip(chr(0))
                            emit(label+f" · hex={raw.hex()} · texto={txt!r}")
                        except Exception as ex:
                            emit(label+" · ERROR "+type(ex).__name__+": "+str(ex))

                    emit("4/8 · Inventario exacto FFC1/FFC2.")
                    for uuid,label in [(FFC1,"FFC1"),(FFC2,"FFC2")]:
                        ch=c.services.get_characteristic(uuid)
                        if ch:
                            emit(label+f" · handle={getattr(ch,'handle','?')} · props={list(ch.properties)} · descriptors="+str([(str(d.uuid),getattr(d,'handle','?')) for d in ch.descriptors]))
                        else:
                            emit(label+" · NO PRESENTE")

                    emit("5/8 · Suscribiendo FFC2. Sólo haré sondas FFC1 de 1 byte; no se enviarán bloques.")
                    def ffc2_cb(sender,data):
                        raw=bytes(data); h=raw.hex()
                        evt={"t":time.monotonic()-t0,"probe":current_probe["label"],"tx":current_probe["hex"],"rx":h,"len":len(raw)}
                        ffc2_rx.append(evt)
                        self.root.after(0,lambda e=evt:append("FFC2 RX · "+str(e)))
                    await asyncio.wait_for(c.start_notify(FFC2,ffc2_cb),timeout=5)
                    emit("FFC2 NOTIFY OK")

                    probes=[("FFC1=01",b"\x01"),("FFC1=00",b"\x00"),("FFC1=02",b"\x02"),("FFC1=FF",b"\xff")]
                    stop=False
                    for label,payload in probes:
                        if stop or not c.is_connected:
                            break
                        before=len(ffc2_rx)
                        current_probe["label"]=label; current_probe["hex"]=payload.hex()
                        emit("6/8 · TX "+label+" · payload="+payload.hex())
                        try:
                            await asyncio.wait_for(c.write_gatt_char(FFC1,payload,response=False),timeout=4)
                        except Exception as ex:
                            emit(label+" · WRITE ERROR "+type(ex).__name__+": "+str(ex))
                            probe_results.append((label,"write_error",repr(ex))); continue
                        deadline=time.monotonic()+3
                        while time.monotonic()<deadline and len(ffc2_rx)==before and c.is_connected:
                            await asyncio.sleep(.05)
                        new=ffc2_rx[before:]
                        probe_results.append((label,[x["rx"] for x in new]))
                        emit(label+" · respuestas="+str(new))
                        for evt in new:
                            if evt["len"]<=2:
                                emit("STOP SEGURIDAD · respuesta FFC2 de <=2 bytes: puede ser solicitud de bloque OAD. No envío nada más.")
                                stop=True
                                break
                        await asyncio.sleep(1)

                    emit("7/8 · Comparando respuestas.")
                    unique=sorted({x["rx"] for x in ffc2_rx})
                    emit("FFC2 RESPUESTAS ÚNICAS="+str(unique))
                    emit("PROBES="+str(probe_results))
                    if len(unique)==1 and unique:
                        emit("Todas las sondas respondieron igual: FFC1 parece exponer una consulta/identidad estable en este firmware.")
                    elif len(unique)>1:
                        emit("FFC1 cambia la respuesta según el byte de entrada: hay semántica de comando/identidad por mapear.")
                    elif not unique:
                        emit("Sin respuestas FFC2: el canal OAD no respondió durante esta sesión.")

                    emit("8/8 · PRUEBA V0.35 FINALIZADA · sin escrituras FFC2 y sin transferencia de firmware.")
                except Exception as ex:
                    emit("PRUEBA V0.35 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=220),lambda r,e:append("PRUEBA V0.35 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.35 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.35 LISTA · 1º PRUEBA V0.35; 2º COPIAR DIAGNÓSTICO. Lee identidad y perfila FFC1→FFC2 sin enviar firmware.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.35 aplicado")
