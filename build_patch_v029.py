from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.34.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.34")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.34 - VALIDAR FFC1")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.34 NO INICIADA · Bluetooth ocupado. Esperá a que termine la operación actual y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.34.")
                return
            append("PRUEBA V0.34: con la sesión viva por B002, valida si FFC1=01 provoca realmente una transición OAD/boot.")
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
                def inv(client):
                    out={}
                    for svc in client.services:
                        out[str(svc.uuid)]=sorted((str(ch.uuid),tuple(sorted(ch.properties))) for ch in svc.characteristics)
                    return out
                def adv_sig(dev,adv):
                    name=(getattr(dev,"name",None) or getattr(adv,"local_name",None) or "")
                    uuids=tuple(sorted(getattr(adv,"service_uuids",None) or []))
                    mfg=tuple(sorted((str(k),bytes(v).hex()) for k,v in (getattr(adv,"manufacturer_data",None) or {}).items()))
                    return name,uuids,mfg
                def relevant(dev,adv):
                    name=(getattr(dev,"name",None) or getattr(adv,"local_name",None) or "")
                    uuids=[str(x).casefold() for x in (getattr(adv,"service_uuids",None) or [])]
                    addr=str(getattr(dev,"address",None) or "")
                    return (addr.casefold()==str(address).casefold()
                            or "apple watch" in name.casefold()
                            or any(x.startswith("00003802-") or x.startswith("0000e91a-") or x.startswith("f000ffc0-") for x in uuids))
                async def snapshot(label,seconds=3):
                    found=await asyncio.wait_for(BleakScanner.discover(timeout=seconds,return_adv=True),timeout=seconds+3)
                    items=found.values() if isinstance(found,dict) else []
                    out={}
                    for dev,adv in items:
                        if relevant(dev,adv):
                            out[str(getattr(dev,"address",None))]=adv_sig(dev,adv)
                    emit(label+" · relevantes="+str(out))
                    return out
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

                b001_rx=[]; ffc2_rx=[]
                try:
                    emit("1/9 · Capturando advertising base antes de conectar.")
                    baseline=await snapshot("BASELINE ADV",3)
                    emit("2/9 · Abriendo GATT fresco y estableciendo handshake B002 validado.")
                    c=await connect_fresh("CONEXIÓN PRE-FFC1")
                    before=inv(c)
                    emit("GATT PRE · servicios="+str(before))
                    def b001_cb(sender,data):
                        h=bytes(data).hex(); b001_rx.append((time.monotonic()-t0,h))
                        self.root.after(0,lambda x=h:append("B001 RX "+x))
                    await asyncio.wait_for(c.start_notify(B001,b001_cb),timeout=5)
                    emit("B001 NOTIFY OK")
                    await asyncio.wait_for(c.write_gatt_char(B002,HANDSHAKE,response=False),timeout=4)
                    emit("TX B002 HANDSHAKE · "+HANDSHAKE.hex())
                    ack_deadline=time.monotonic()+4
                    while time.monotonic()<ack_deadline and not b001_rx:
                        await asyncio.sleep(.1)
                    emit("HANDSHAKE ACK="+str(b001_rx[-1] if b001_rx else None))
                    if not c.is_connected:
                        raise RuntimeError("GATT cayó antes de probar FFC1")

                    emit("3/9 · Suscribiendo FFC2 y enviando FFC1=01 UNA sola vez con sesión B002 ya validada.")
                    def ffc2_cb(sender,data):
                        h=bytes(data).hex(); ffc2_rx.append((time.monotonic()-t0,h))
                        self.root.after(0,lambda x=h:append("FFC2 RX "+x))
                    await asyncio.wait_for(c.start_notify(FFC2,ffc2_cb),timeout=5)
                    emit("FFC2 NOTIFY OK")
                    await asyncio.wait_for(c.write_gatt_char(FFC1,b"\\x01",response=False),timeout=4)
                    ffc1_at=time.monotonic()-t0
                    emit(f"FFC1=01 ENVIADO @{ffc1_at:.2f}s")

                    emit("4/9 · Observando 45 s. El mismo handshake B002 sostuvo 45 s en V0.33; una caída ahora sí sería atribuible a FFC1.")
                    lost_at=None
                    watch_start=time.monotonic()
                    while time.monotonic()-watch_start < 45:
                        await asyncio.sleep(.25)
                        if not c.is_connected:
                            lost_at=time.monotonic()-t0
                            emit(f"DESCONEXIÓN POST-FFC1 @{lost_at:.2f}s · delta={lost_at-ffc1_at:.2f}s")
                            break
                    if lost_at is None:
                        emit("GATT SIGUE VIVO 45 s después de FFC1=01 · FFC1 NO provocó reinicio en esta sesión.")
                        emit("5/9 · RESULTADO DIRECTO: descarto FFC1=01 como disparador de boot inmediato.")
                    else:
                        emit("5/9 · RESULTADO DIRECTO: FFC1=01 venció una sesión que B002 mantenía viva; transición OAD/boot probable.")

                    await disconnect_clean(c); c=None
                    emit("6/9 · Escaneando 60 s por el mismo reloj o una identidad BLE nueva relacionada.")
                    seen={}; deadline=time.monotonic()+60
                    while time.monotonic()<deadline:
                        try:
                            found=await asyncio.wait_for(BleakScanner.discover(timeout=1.5,return_adv=True),timeout=3)
                            items=found.values() if isinstance(found,dict) else []
                            for dev,adv in items:
                                if not relevant(dev,adv):
                                    continue
                                addr=str(getattr(dev,"address",None))
                                sig=adv_sig(dev,adv)
                                if (addr,sig) not in seen:
                                    seen[(addr,sig)]=time.monotonic()-t0
                                    emit(f"ADV POST @{seen[(addr,sig)]:.2f}s · {addr} · {sig}")
                        except Exception as ex:
                            emit("SCAN POST parcial · "+type(ex).__name__+": "+str(ex))
                        await asyncio.sleep(.2)
                    new_addrs=sorted({a for (a,sig) in seen if a not in baseline})
                    emit("7/9 · DIRECCIONES NUEVAS RELEVANTES="+str(new_addrs))

                    emit("8/9 · Intentando GATT en identidad original y candidatos nuevos.")
                    candidates=[str(address)]+[a for a in new_addrs if a.casefold()!=str(address).casefold()]
                    checked=[]
                    for addr in candidates[:5]:
                        target=None; cc=None
                        try:
                            target=await asyncio.wait_for(BleakScanner.find_device_by_address(addr,timeout=5),timeout=7)
                            if target is None:
                                checked.append((addr,"sin anuncio")); continue
                            cc=BleakClient(target,timeout=12,winrt={"use_cached_services":False})
                            await asyncio.wait_for(cc.connect(),timeout=15)
                            if not cc.is_connected:
                                raise RuntimeError("is_connected=False")
                            post=inv(cc)
                            checked.append((addr,"GATT OK",post))
                            emit("CANDIDATO GATT OK · "+addr+" · "+str(post))
                        except Exception as ex:
                            checked.append((addr,type(ex).__name__,str(ex)))
                            emit("CANDIDATO GATT FALLÓ · "+addr+" · "+type(ex).__name__+": "+str(ex))
                        finally:
                            if cc:
                                try: await asyncio.wait_for(cc.disconnect(),timeout=3)
                                except Exception: pass
                    emit("9/9 · PRUEBA V0.34 FINALIZADA · FFC2="+str(ffc2_rx)+" · candidatos="+str(checked))
                except Exception as ex:
                    emit("PRUEBA V0.34 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=260),lambda r,e:append("PRUEBA V0.34 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.34 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.34 LISTA · 1º PRUEBA V0.34; 2º COPIAR DIAGNÓSTICO. Valida FFC1 con sesión B002 viva y rastrea identidad OAD.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.34 aplicado")
