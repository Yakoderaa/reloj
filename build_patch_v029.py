from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.45.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.45")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.45 - AISLAR OP0B")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.45 NO INICIADA · Bluetooth ocupado. Esperá a que termine y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.45.")
                return
            append("PRUEBA V0.45: aísla si OP0B solo arma la caída o si necesita una segunda escritura.")
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

                cases=[
                    ("CONTROL 0 · SOLO HANDSHAKE",[]),
                    ("CONTROL 1 · 0A→0A",[0x0A,0x0A]),
                    ("CONTROL 2 · 0C→0C",[0x0C,0x0C]),
                    ("CASO 1 · 0B SOLO",[0x0B]),
                    ("CASO 2 · 0B→0A",[0x0B,0x0A]),
                    ("CASO 3 · 0B→0C",[0x0B,0x0C]),
                    ("CASO 4 · 0B→0B",[0x0B,0x0B]),
                ]
                summary=[]; trigger=None; adv=[]
                try:
                    emit("1/10 · V0.44 mostró que 0B→0B puede hacer caer GATT. Ahora separo caída natural, opcode 0B y segunda escritura.")
                    for idx,(label,ops) in enumerate(cases,1):
                        emit(f"2/10 · FASE {idx}/7 · {label} · ops="+str([f"{x:02X}" for x in ops]))
                        c,b_rx,f_rx,current=await setup_session(label)
                        results,lost=await run_prefix(c,label,ops,f_rx,current,2.5)
                        summary.append((label,results,lost))
                        emit(label+" · caída="+str(lost))
                        if lost is not None:
                            trigger=(label,ops,lost)
                            if idx==1:
                                emit("RESULTADO CRÍTICO · cae incluso sin escribir FFC1: la caída pertenece a la sesión/handshake y no a OP0B.")
                            elif idx in (2,3):
                                emit("CONTROL INESPERADO · también cae un opcode repetido distinto de 0B; investigar repetición/estado general.")
                            elif idx==4:
                                emit("RESULTADO FUERTE · un solo OP0B basta para armar la caída diferida.")
                            elif idx==5:
                                emit("RESULTADO FUERTE · OP0B solo sobrevive, pero 0B→0A cae: cualquier segunda escritura tras 0B puede disparar el estado.")
                            elif idx==6:
                                emit("RESULTADO · 0B→0A sobrevive pero 0B→0C cae: la transición 0B→0C tiene efecto especial.")
                            else:
                                emit("RESULTADO FUERTE · solo 0B→0B cayó entre los casos probados: la repetición de OP0B es el disparador mínimo observado.")
                            c=None
                            adv=await scan_after("POST-"+label,20)
                            break
                        await disconnect_clean(c); c=None
                        await asyncio.sleep(2)

                    emit("3/10 · RESUMEN CASOS="+str(summary))
                    emit("4/10 · TRIGGER="+str(trigger))
                    emit("5/10 · ADV POST-TRIGGER="+str(adv))
                    if trigger is None:
                        emit("6/10 · Ningún caso cayó en 22 s; la V0.44 pudo depender de estado residual/intermitencia.")
                    elif trigger[0]=="CONTROL 0 · SOLO HANDSHAKE":
                        emit("6/10 · HIPÓTESIS · la sesión GATT/handshake puede tener timeout propio independiente de FFC1.")
                    elif trigger[0].startswith("CONTROL"):
                        emit("6/10 · HIPÓTESIS · la caída no es exclusiva de OP0B; revisar patrón de escrituras y estado interno.")
                    elif trigger[0]=="CASO 1 · 0B SOLO":
                        emit("6/10 · HIPÓTESIS · OP0B inicia por sí solo un estado diferido que termina cerrando GATT.")
                    elif trigger[0]=="CASO 2 · 0B→0A":
                        emit("6/10 · HIPÓTESIS · OP0B arma estado y una segunda escritura cualquiera lo completa.")
                    elif trigger[0]=="CASO 3 · 0B→0C":
                        emit("6/10 · HIPÓTESIS · OP0C completa un estado iniciado por OP0B.")
                    else:
                        emit("6/10 · HIPÓTESIS · la repetición consecutiva de OP0B es el disparador mínimo observado.")
                    emit("7/10 · Cada fase usa sesión nueva, mismo handshake, ritmo 2.5 s y observación 22 s.")
                    emit("8/10 · No se escribió FFC2 ni se transfirió firmware.")
                    emit("9/10 · La próxima prueba se elegirá directamente según el primer caso que caiga.")
                    emit("10/10 · PRUEBA V0.45 FINALIZADA")
                except Exception as ex:
                    emit("PRUEBA V0.45 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=480),lambda r,e:append("PRUEBA V0.45 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.45 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.45 LISTA · 1º PRUEBA V0.45; 2º COPIAR DIAGNÓSTICO. Aísla si OP0B solo o una segunda escritura provoca la caída.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.45 aplicado")
