from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.41.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.41")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.41 - AISLAR OP0D")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.41 NO INICIADA · Bluetooth ocupado. Esperá a que termine y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.41.")
                return
            append("PRUEBA V0.41: A/B OP0C vs OP0D para aislar la caída vista en V0.39.")
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
                async def send_op(client,op,rx,current,wait_s=2.0):
                    current["op"]=f"{op:02X}"
                    before=len(rx)
                    emit(f"TX FFC1 OP {op:02X}")
                    await asyncio.wait_for(client.write_gatt_char(FFC1,bytes([op]),response=False),timeout=4)
                    deadline=time.monotonic()+wait_s
                    while time.monotonic()<deadline and len(rx)==before and client.is_connected:
                        await asyncio.sleep(.05)
                    return rx[before:]
                async def observe(client,label,seconds):
                    start=time.monotonic(); lost=None
                    last=-1
                    while time.monotonic()-start<seconds:
                        await asyncio.sleep(.2)
                        if not client.is_connected:
                            lost=time.monotonic()-start
                            emit(f"{label} · GATT cayó tras {lost:.2f}s")
                            break
                        e=int(time.monotonic()-start)
                        if e in (5,10,15,20,25) and e!=last:
                            last=e; emit(f"{label} · sigue conectado a {e}s")
                    if lost is None:
                        emit(f"{label} · sobrevivió {seconds}s conectado")
                    return lost
                async def scan_after(label,seconds=25):
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

                a_lost=None; b_lost=None; b_adv=[]
                try:
                    emit("1/8 · FASE A CONTROL: handshake + OP0C único + 25 s.")
                    c,b_rx,f_rx,current=await setup_session("FASE A")
                    r=await send_op(c,12,f_rx,current)
                    emit("FASE A OP0C respuestas="+str(r))
                    a_lost=await observe(c,"FASE A",25)
                    await disconnect_clean(c); c=None
                    await asyncio.sleep(2)

                    emit("2/8 · FASE B TEST: handshake + OP0D único + 25 s.")
                    c,b_rx,f_rx,current=await setup_session("FASE B")
                    r=await send_op(c,13,f_rx,current)
                    emit("FASE B OP0D respuestas="+str(r))
                    b_lost=await observe(c,"FASE B",25)

                    emit("3/8 · COMPARACIÓN A/B")
                    emit("OP0C caída="+str(a_lost))
                    emit("OP0D caída="+str(b_lost))
                    if a_lost is None and b_lost is not None:
                        emit("RESULTADO FUERTE · OP0D provoca la caída diferida y OP0C no.")
                    elif a_lost is None and b_lost is None:
                        emit("OP0C y OP0D sobreviven aislados: la caída V0.39 requiere una secuencia/carga acumulada.")
                    elif a_lost is not None and b_lost is not None:
                        emit("Ambos caen aislados: la causa no es exclusiva de OP0D.")
                    else:
                        emit("Resultado atípico: OP0C cae pero OP0D no.")

                    if b_lost is not None:
                        emit("4/8 · Caída tras OP0D: capturo advertising real sin desconectar manualmente.")
                        c=None
                        b_adv=await scan_after("POST-OP0D",25)
                    else:
                        emit("4/8 · OP0D estable; cierro sesión de forma controlada.")
                        await disconnect_clean(c); c=None

                    emit("5/8 · ADV POST-OP0D="+str(b_adv))
                    emit("6/8 · Si OP0D es inocuo, la próxima prueba será la secuencia 08→0D contra control.")
                    emit("7/8 · No se escribió FFC2 ni se transfirió firmware.")
                    emit("8/8 · PRUEBA V0.41 FINALIZADA")
                except Exception as ex:
                    emit("PRUEBA V0.41 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=240),lambda r,e:append("PRUEBA V0.41 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.41 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.41 LISTA · 1º PRUEBA V0.41; 2º COPIAR DIAGNÓSTICO. Aísla OP0D contra OP0C para explicar la caída de V0.39.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.41 aplicado")
