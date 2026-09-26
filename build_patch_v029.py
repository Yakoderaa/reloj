from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.36.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.36")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.36 - IDENTIFICAR PROTOCOLO OTA")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.36 NO INICIADA · Bluetooth ocupado. Esperá a que termine la operación actual y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.36.")
                return
            append("PRUEBA V0.36: perfila el formato real de Image Identify usando sólo cabeceras inválidas; no envía bloques de firmware.")
            async def work():
                c=None; report=[]; address=self.selected.get("address") or getattr(self.selected.get("device"),"address",None)
                t0=time.monotonic()
                B001="0000b001-0000-1000-8000-00805f9b34fb"
                B002="0000b002-0000-1000-8000-00805f9b34fb"
                FFC1="f000ffc1-0451-4000-b000-000000000000"
                FFC2="f000ffc2-0451-4000-b000-000000000000"
                HANDSHAKE=bytes.fromhex("00ff000101150000010010000000010000000000")
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

                b001_rx=[]; ffc2_rx=[]; current={"label":"—","hex":"—"}
                try:
                    emit("1/8 · Abriendo GATT fresco y estableciendo handshake B002.")
                    c=await connect_fresh("CONEXIÓN")
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

                    emit("2/8 · Suscribiendo FFC2.")
                    def ffc2_cb(sender,data):
                        raw=bytes(data)
                        evt={"t":time.monotonic()-t0,"probe":current["label"],"tx":current["hex"],"rx":raw.hex(),"len":len(raw)}
                        ffc2_rx.append(evt)
                        self.root.after(0,lambda e=evt:append("FFC2 RX · "+str(e)))
                    await asyncio.wait_for(c.start_notify(FFC2,ffc2_cb),timeout=5)
                    emit("FFC2 NOTIFY OK")

                    emit("3/8 · Consulta base FFC1=01 para capturar la firma actual.")
                    current["label"]="QUERY_01"; current["hex"]="01"
                    before=len(ffc2_rx)
                    await asyncio.wait_for(c.write_gatt_char(FFC1,bytes([1]),response=False),timeout=4)
                    deadline=time.monotonic()+3
                    while time.monotonic()<deadline and len(ffc2_rx)==before and c.is_connected:
                        await asyncio.sleep(.05)
                    base_events=ffc2_rx[before:]
                    emit("QUERY_01 respuestas="+str(base_events))
                    base_rx=base_events[0]["rx"] if base_events else None
                    if base_rx:
                        raw=bytes.fromhex(base_rx)
                        if len(raw)==11:
                            field_3_6=int.from_bytes(raw[3:7],"little")
                            emit(f"FIRMA 11B · cmd={raw[0]:02x} · status={raw[1]:02x} · campo2={raw[2]:02x} · campo[3:7]_LE=0x{field_3_6:08x} ({field_3_6}) · cola={raw[7:].hex()}")
                            if field_3_6==1048576:
                                emit("HEURÍSTICA · campo[3:7] equivale a 1 MiB; podría describir tamaño/espacio de imagen, aún no confirmado.")

                    emit("4/8 · Probando longitudes de cabecera inválida. Sólo FFC1; nunca escribo FFC2.")
                    probes=[
                        ("INVALID_8_ZERO",bytes(8)),
                        ("INVALID_12_ZERO",bytes(12)),
                        ("INVALID_16_ZERO",bytes(16)),
                        ("INVALID_16_FF",bytes([255])*16),
                        ("INVALID_TI16_ZERO_LENGTH",bytes.fromhex("0000ffff0000000045454545000001ff")),
                    ]
                    results=[]
                    stop=False
                    for label,payload in probes:
                        if stop or not c.is_connected:
                            break
                        current["label"]=label; current["hex"]=payload.hex()
                        before=len(ffc2_rx)
                        emit(f"TX {label} · len={len(payload)} · {payload.hex()}")
                        try:
                            await asyncio.wait_for(c.write_gatt_char(FFC1,payload,response=False),timeout=4)
                        except Exception as ex:
                            results.append((label,"WRITE_ERROR",repr(ex)))
                            emit(label+" · WRITE ERROR · "+type(ex).__name__+": "+str(ex))
                            continue
                        wait_until=time.monotonic()+3
                        while time.monotonic()<wait_until and len(ffc2_rx)==before and c.is_connected:
                            await asyncio.sleep(.05)
                        new=ffc2_rx[before:]
                        results.append((label,[x["rx"] for x in new]))
                        emit(label+" · respuestas="+str(new))
                        for evt in new:
                            if evt["len"]<=4:
                                emit("STOP SEGURIDAD · respuesta corta compatible con status/block request. No pruebo más cabeceras.")
                                stop=True
                                break
                            if base_rx and evt["rx"]!=base_rx:
                                emit("RESPUESTA NUEVA · difiere de QUERY_01; protocolo discrimina la forma de la cabecera.")
                        await asyncio.sleep(.8)

                    emit("5/8 · Verificando si GATT sigue vivo después de las cabeceras inválidas.")
                    emit("GATT vivo="+str(bool(c and c.is_connected)))
                    emit("6/8 · RESULTADOS="+str(results))
                    unique=sorted({x["rx"] for x in ffc2_rx})
                    emit("FFC2 ÚNICAS="+str(unique))

                    emit("7/8 · INTERPRETACIÓN AUTOMÁTICA")
                    probe_responses=[(label,r) for label,r in results if isinstance(r,list) and r]
                    if any(any(len(bytes.fromhex(h))<=4 for h in vals) for label,vals in probe_responses):
                        emit("Hay respuesta corta a una cabecera larga: comportamiento compatible con validación OAD/bloque. Se detuvo antes de transferir datos.")
                    elif probe_responses:
                        emit("Las cabeceras largas generan respuesta, pero no una solicitud corta de bloque: el perfil es probablemente una variante propietaria.")
                    else:
                        emit("Sólo QUERY_01 responde; las cabeceras TI inválidas son ignoradas. Esto apunta a un protocolo propietario sobre UUIDs OAD reutilizados.")

                    emit("8/8 · PRUEBA V0.36 FINALIZADA · cero escrituras FFC2, cero bloques de firmware.")
                except Exception as ex:
                    emit("PRUEBA V0.36 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=220),lambda r,e:append("PRUEBA V0.36 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.36 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.36 LISTA · 1º PRUEBA V0.36; 2º COPIAR DIAGNÓSTICO. Distingue TI OAD clásico de protocolo propietario sin enviar firmware.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.36 aplicado")
