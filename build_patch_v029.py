from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.37.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.37")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.37 - MAPEAR OPCODES FFC1")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.37 NO INICIADA · Bluetooth ocupado. Esperá a que termine y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.37.")
                return
            append("PRUEBA V0.37: mapea opcodes FFC1 03–0F con parada inmediata ante respuesta nueva, caída o señal de transferencia.")
            async def work():
                c=None; report=[]; address=self.selected.get("address") or getattr(self.selected.get("device"),"address",None)
                t0=time.monotonic()
                B001="0000b001-0000-1000-8000-00805f9b34fb"
                B002="0000b002-0000-1000-8000-00805f9b34fb"
                FFC1="f000ffc1-0451-4000-b000-000000000000"
                FFC2="f000ffc2-0451-4000-b000-000000000000"
                HANDSHAKE=bytes.fromhex("00ff000101150000010010000000010000000000")
                KNOWN="0200070000100020121601"
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
                async def scan_transition(seconds=25):
                    emit(f"SCAN TRANSICIÓN · {seconds}s")
                    seen=[]
                    deadline=time.monotonic()+seconds
                    while time.monotonic()<deadline:
                        try:
                            found=await asyncio.wait_for(BleakScanner.discover(timeout=1.0,return_adv=True),timeout=2.5)
                            items=found.values() if isinstance(found,dict) else []
                            for dev,adv in items:
                                name=(getattr(dev,"name",None) or getattr(adv,"local_name",None) or "")
                                uuids=tuple(sorted(getattr(adv,"service_uuids",None) or []))
                                addr=str(getattr(dev,"address",None) or "")
                                if addr.casefold()==str(address).casefold() or "apple watch" in name.casefold():
                                    sig=(addr,name,uuids,{str(k):bytes(v).hex() for k,v in (getattr(adv,"manufacturer_data",None) or {}).items()})
                                    if sig not in seen:
                                        seen.append(sig); emit("ADV TRANSICIÓN · "+str(sig))
                        except Exception as ex:
                            emit("SCAN parcial · "+type(ex).__name__+": "+str(ex))
                        await asyncio.sleep(.15)
                    return seen

                b001_rx=[]; ffc2_rx=[]; current={"op":"--"}
                try:
                    emit("1/7 · Abriendo GATT y estableciendo handshake B002.")
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

                    emit("2/7 · Suscribiendo FFC2.")
                    def ffc2_cb(sender,data):
                        raw=bytes(data)
                        evt={"t":time.monotonic()-t0,"op":current["op"],"rx":raw.hex(),"len":len(raw)}
                        ffc2_rx.append(evt)
                        self.root.after(0,lambda e=evt:append("FFC2 RX · "+str(e)))
                    await asyncio.wait_for(c.start_notify(FFC2,ffc2_cb),timeout=5)
                    emit("FFC2 NOTIFY OK")

                    emit("3/7 · Revalidando opcode 01 conocido.")
                    current["op"]="01"; before=len(ffc2_rx)
                    await asyncio.wait_for(c.write_gatt_char(FFC1,bytes([1]),response=False),timeout=4)
                    deadline=time.monotonic()+2.5
                    while time.monotonic()<deadline and len(ffc2_rx)==before and c.is_connected:
                        await asyncio.sleep(.05)
                    base=[x for x in ffc2_rx[before:]]
                    emit("OP 01 · "+str(base))
                    if not base or base[0]["rx"]!=KNOWN:
                        emit("STOP · la firma base cambió; no continúo el mapa.")
                        return report

                    emit("4/7 · Probando opcodes FFC1 03–0F, uno por vez.")
                    results=[]; stop_reason=None
                    for op in range(3,16):
                        if not c.is_connected:
                            stop_reason=f"GATT cayó antes de OP {op:02X}"
                            break
                        current["op"]=f"{op:02X}"
                        before=len(ffc2_rx)
                        emit(f"TX FFC1 OP {op:02X}")
                        try:
                            await asyncio.wait_for(c.write_gatt_char(FFC1,bytes([op]),response=False),timeout=4)
                        except Exception as ex:
                            stop_reason=f"WRITE ERROR OP {op:02X}: {type(ex).__name__}: {ex}"
                            emit(stop_reason); break
                        deadline=time.monotonic()+1.6
                        while time.monotonic()<deadline and len(ffc2_rx)==before and c.is_connected:
                            await asyncio.sleep(.05)
                        new=ffc2_rx[before:]
                        results.append((f"{op:02X}",[x["rx"] for x in new],bool(c.is_connected)))
                        emit(f"OP {op:02X} · respuestas="+str(new)+" · GATT="+str(bool(c.is_connected)))
                        if not c.is_connected:
                            stop_reason=f"OP {op:02X} provocó desconexión"
                            break
                        if new:
                            if any(x["len"]<=4 for x in new):
                                stop_reason=f"OP {op:02X} produjo respuesta corta <=4B"
                                break
                            if any(x["rx"]!=KNOWN for x in new):
                                stop_reason=f"OP {op:02X} produjo respuesta NUEVA"
                                break
                        await asyncio.sleep(.45)

                    emit("5/7 · RESULTADOS OPCODES="+str(results))
                    emit("STOP_REASON="+str(stop_reason))
                    if stop_reason:
                        emit("6/7 · Hubo señal relevante; detengo escrituras y observo advertising.")
                        await disconnect_clean(c); c=None
                        seen=await scan_transition(25)
                        emit("ADV DESPUÉS DEL STOP="+str(seen))
                    else:
                        emit("6/7 · Ningún opcode 03–0F respondió ni alteró GATT.")
                    emit("7/7 · PRUEBA V0.37 FINALIZADA · sin escrituras FFC2 y sin bloques de firmware.")
                except Exception as ex:
                    emit("PRUEBA V0.37 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=220),lambda r,e:append("PRUEBA V0.37 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.37 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.37 LISTA · 1º PRUEBA V0.37; 2º COPIAR DIAGNÓSTICO. Mapea FFC1 03–0F y frena ante cualquier transición.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.37 aplicado")
