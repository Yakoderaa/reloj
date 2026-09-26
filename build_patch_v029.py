from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.43.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.43")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.43 - PREFIJOS 08-0D")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.43 NO INICIADA · Bluetooth ocupado. Esperá a que termine y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.43.")
                return
            append("PRUEBA V0.43: busca el prefijo mínimo de 08→0D que reproduce la caída diferida.")
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
                async def connect_fresh(label,window=90):
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
                async def setup_session(label):
                    client=await connect_fresh(label+" CONEXIÓN")
                    b_rx=[]; f_rx=[]; current={"op":"--"}
                    def b_cb(sender,data):
                        h=bytes(data).hex(); b_rx.append((time.monotonic()-t0,h))
                        self.root.after(0,lambda x=h,l=label:append(l+" B001 RX "+x))
                    def f_cb(sender,data):
                        raw=bytes(data)
                        evt={"t":time.monotonic()-t0,"op":current["op"],"rx":raw.hex(),"len":len(raw)}
                        f_rx.append(evt)
                        self.root.after(0,lambda e=evt,l=label:append(l+" FFC2 RX · "+str(e)))
                    await asyncio.wait_for(client.start_notify(B001,b_cb),timeout=5)
                    await asyncio.wait_for(client.write_gatt_char(B002,HANDSHAKE,response=False),timeout=4)
                    emit(label+" · TX B002 HANDSHAKE")
                    ack_deadline=time.monotonic()+4
                    while time.monotonic()<ack_deadline and not b_rx:
                        await asyncio.sleep(.1)
                    emit(label+" · HANDSHAKE ACK="+str(b_rx[-1] if b_rx else None))
                    if not client.is_connected:
                        raise RuntimeError(label+" · GATT cayó durante handshake")
                    await asyncio.wait_for(client.start_notify(FFC2,f_cb),timeout=5)
                    emit(label+" · FFC2 NOTIFY OK")
                    return client,b_rx,f_rx,current
                async def run_prefix(client,label,ops,rx,current,interval=2.5):
                    results=[]
                    for idx,op in enumerate(ops,1):
                        if not client.is_connected:
                            return results,("durante",{"before":f"{op:02X}","index":idx})
                        current["op"]=f"{op:02X}"
                        before=len(rx); sent=time.monotonic()
                        emit(f"{label} · TX {idx}/{len(ops)} · OP {op:02X}")
                        try:
                            await asyncio.wait_for(client.write_gatt_char(FFC1,bytes([op]),response=False),timeout=4)
                        except Exception as ex:
                            return results,("write_error",repr(ex))
                        while time.monotonic()-sent<interval:
                            await asyncio.sleep(.1)
                            if not client.is_connected:
                                delta=time.monotonic()-sent
                                emit(f"{label} · GATT cayó {delta:.2f}s después de OP {op:02X}")
                                results.append((f"{op:02X}",[x["rx"] for x in rx[before:]],False))
                                return results,("durante",{"after":f"{op:02X}","delta":delta})
                        new=rx[before:]
                        results.append((f"{op:02X}",[x["rx"] for x in new],True))
                        emit(label+f" · OP {op:02X} · respuestas="+str(new)+" · GATT=True")
                    start=time.monotonic(); last=-1
                    while time.monotonic()-start<22:
                        await asyncio.sleep(.2)
                        if not client.is_connected:
                            lost=time.monotonic()-start
                            emit(f"{label} · GATT cayó {lost:.2f}s después de terminar el prefijo")
                            return results,("después",lost)
                        e=int(time.monotonic()-start)
                        if e in (5,10,15,20) and e!=last:
                            last=e; emit(f"{label} · sigue conectado a +{e}s")
                    emit(label+" · sobrevivió 22s después del prefijo")
                    return results,None
                async def scan_after(label,seconds=20):
                    emit(f"{label} · escaneo post-caída {seconds}s")
                    seen=[]
                    deadline=time.monotonic()+seconds
                    while time.monotonic()<deadline:
                        try:
                            found=await asyncio.wait_for(BleakScanner.discover(timeout=1.0,return_adv=True),timeout=2.5)
                            items=found.values() if isinstance(found,dict) else []
                            for dev,adv in items:
                                name=(getattr(dev,"name",None) or getattr(adv,"local_name",None) or "")
                                addr=str(getattr(dev,"address",None) or "")
                                if addr.casefold()==str(address).casefold() or "apple watch" in name.casefold():
                                    sig=(addr,name,tuple(sorted(getattr(adv,"service_uuids",None) or [])),{str(k):bytes(v).hex() for k,v in (getattr(adv,"manufacturer_data",None) or {}).items()})
                                    if sig not in seen:
                                        seen.append(sig); emit(label+" ADV · "+str(sig))
                        except Exception as ex:
                            emit(label+" scan parcial · "+type(ex).__name__+": "+str(ex))
                        await asyncio.sleep(.15)
                    return seen

                prefixes=[
                    ("PREFIJO 08-0A",list(range(8,11))),
                    ("PREFIJO 08-0B",list(range(8,12))),
                    ("PREFIJO 08-0C",list(range(8,13))),
                    ("PREFIJO 08-0D",list(range(8,14))),
                ]
                summary=[]; trigger=None; adv=[]
                try:
                    emit("1/8 · Cada prefijo usa una sesión nueva, mismo handshake y mismo ritmo de 2.5 s.")
                    for idx,(label,ops) in enumerate(prefixes,1):
                        emit(f"2/8 · FASE {idx}/4 · {label} · ops="+str([f"{x:02X}" for x in ops]))
                        c,b_rx,f_rx,current=await setup_session(label)
                        results,lost=await run_prefix(c,label,ops,f_rx,current,2.5)
                        summary.append((label,results,lost))
                        emit(label+" · caída="+str(lost))
                        if lost is not None:
                            trigger=(label,ops,lost)
                            emit("PREFIJO DISPARADOR ENCONTRADO · "+str(trigger))
                            c=None
                            adv=await scan_after("POST-"+label,20)
                            break
                        await disconnect_clean(c); c=None
                        await asyncio.sleep(2)

                    emit("3/8 · RESUMEN PREFIJOS="+str(summary))
                    emit("4/8 · TRIGGER="+str(trigger))
                    if trigger:
                        emit("5/8 · ADV POST-TRIGGER="+str(adv))
                        emit("6/8 · El primer prefijo que cae acota la orden necesaria; la próxima versión aislará el último opcode añadido.")
                    else:
                        emit("5/8 · Ningún prefijo cayó en 22 s.")
                        emit("6/8 · La caída V0.42 no se reprodujo; puede depender de estado previo o ser intermitente.")
                    emit("7/8 · No se escribió FFC2 ni se transfirió firmware.")
                    emit("8/8 · PRUEBA V0.43 FINALIZADA")
                except Exception as ex:
                    emit("PRUEBA V0.43 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=360),lambda r,e:append("PRUEBA V0.43 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.43 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.43 LISTA · 1º PRUEBA V0.43; 2º COPIAR DIAGNÓSTICO. Busca el prefijo mínimo de 08→0D que reproduce la caída.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.43 aplicado")
