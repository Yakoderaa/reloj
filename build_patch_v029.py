from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.40.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.40")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.40 - AISLAR OP07")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.40 NO INICIADA · Bluetooth ocupado. Esperá a que termine y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.40.")
                return
            append("PRUEBA V0.40: A/B OP05 vs OP07. Busca si OP07 provoca una caída diferida de la sesión.")
            async def work():
                c=None; report=[]; address=self.selected.get("address") or getattr(self.selected.get("device"),"address",None)
                t0=time.monotonic()
                B001="0000b001-0000-1000-8000-00805f9b34fb"
                B002="0000b002-0000-1000-8000-00805f9b34fb"
                FFC1="f000ffc1-0451-4000-b000-000000000000"
                FFC2="f000ffc2-0451-4000-b000-000000000000"
                HANDSHAKE=bytes.fromhex("00ff000101150000010010000000010000000000")
                KNOWN05="0600040000000000"
                KNOWN07="0800010001"
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
                async def send_op(client,op,rx,current,wait_s=2.5):
                    current["op"]=f"{op:02X}"
                    before=len(rx)
                    emit(f"TX FFC1 OP {op:02X}")
                    await asyncio.wait_for(client.write_gatt_char(FFC1,bytes([op]),response=False),timeout=4)
                    deadline=time.monotonic()+wait_s
                    while time.monotonic()<deadline and len(rx)==before and client.is_connected:
                        await asyncio.sleep(.05)
                    return rx[before:]
                async def observe_link(client,label,seconds):
                    start=time.monotonic()
                    lost=None
                    while time.monotonic()-start<seconds:
                        await asyncio.sleep(.25)
                        if not client.is_connected:
                            lost=time.monotonic()-start
                            emit(f"{label} · GATT cayó tras {lost:.2f}s")
                            break
                        elapsed=int(time.monotonic()-start)
                        if elapsed and elapsed%10==0:
                            emit(f"{label} · sigue conectado a {elapsed}s")
                            await asyncio.sleep(.15)
                    if lost is None:
                        emit(f"{label} · sobrevivió {seconds}s conectado")
                    return lost
                async def scan_transition(label,seconds=30):
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

                phase_a_lost=None; phase_b_lost=None; phase_b_adv=[]
                try:
                    emit("1/8 · FASE A CONTROL: handshake B002 + OP05 único + 35 s sin más escrituras.")
                    c,b_rx,f_rx,current=await setup_session("FASE A")
                    resp=await send_op(c,5,f_rx,current)
                    emit("FASE A OP05="+str(resp))
                    if not resp or resp[0]["rx"]!=KNOWN05:
                        emit("STOP · OP05 no coincide con la firma conocida.")
                        return report
                    phase_a_lost=await observe_link(c,"FASE A",35)
                    await disconnect_clean(c); c=None
                    await asyncio.sleep(2)

                    emit("2/8 · FASE B TEST: handshake B002 + OP07 único + 35 s sin más escrituras.")
                    c,b_rx,f_rx,current=await setup_session("FASE B")
                    resp=await send_op(c,7,f_rx,current)
                    emit("FASE B OP07="+str(resp))
                    if not resp or resp[0]["rx"]!=KNOWN07:
                        emit("STOP · OP07 no coincide con la firma conocida.")
                        return report
                    op07_sent=time.monotonic()
                    phase_b_lost=await observe_link(c,"FASE B",35)

                    emit("3/8 · COMPARACIÓN A/B")
                    emit("FASE A caída="+str(phase_a_lost))
                    emit("FASE B caída="+str(phase_b_lost))
                    if phase_a_lost is None and phase_b_lost is not None:
                        emit("RESULTADO FUERTE · OP07 provoca una caída diferida que OP05 no provoca.")
                    elif phase_a_lost is None and phase_b_lost is None:
                        emit("OP05 y OP07 sobrevivieron 35 s; la caída V0.39 no fue causada por OP07 por sí solo.")
                    elif phase_a_lost is not None and phase_b_lost is not None:
                        emit("Ambas fases cayeron; no se puede atribuir la caída exclusivamente a OP07.")
                    else:
                        emit("Resultado atípico: cayó OP05 pero no OP07.")

                    if phase_b_lost is not None:
                        emit("4/8 · OP07 produjo caída; NO desconecto manualmente. Capturo advertising real posterior.")
                        c=None
                        phase_b_adv=await scan_transition("POST-OP07",30)
                    else:
                        emit("4/8 · OP07 no produjo caída en 35 s; cierro sesión de forma controlada.")
                        await disconnect_clean(c); c=None

                    emit("5/8 · ADV POST-OP07="+str(phase_b_adv))
                    emit("6/8 · TIEMPO DESDE OP07 A CAÍDA="+str(phase_b_lost))
                    if phase_b_lost is not None and 14 <= phase_b_lost <= 24:
                        emit("VENTANA DETECTADA · caída entre 14–24 s, consistente con el retraso observado en V0.39.")
                    emit("7/8 · No se escribió FFC2 ni se transfirió firmware.")
                    emit("8/8 · PRUEBA V0.40 FINALIZADA")
                except Exception as ex:
                    emit("PRUEBA V0.40 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=260),lambda r,e:append("PRUEBA V0.40 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.40 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.40 LISTA · 1º PRUEBA V0.40; 2º COPIAR DIAGNÓSTICO. Aísla si OP07 causa la caída diferida observada en V0.39.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.40 aplicado")
