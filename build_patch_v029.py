from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.39.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.39")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.39 - COMPLETAR MAPA FFC1")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.39 NO INICIADA · Bluetooth ocupado. Esperá a que termine y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.39.")
                return
            append("PRUEBA V0.39: revalida OP01/05/07 y completa el mapa 08–0F, sin escribir FFC2 ni enviar firmware.")
            async def work():
                c=None; report=[]; address=self.selected.get("address") or getattr(self.selected.get("device"),"address",None)
                t0=time.monotonic()
                B001="0000b001-0000-1000-8000-00805f9b34fb"
                B002="0000b002-0000-1000-8000-00805f9b34fb"
                FFC1="f000ffc1-0451-4000-b000-000000000000"
                FFC2="f000ffc2-0451-4000-b000-000000000000"
                HANDSHAKE=bytes.fromhex("00ff000101150000010010000000010000000000")
                KNOWN={
                    1:"0200070000100020121601",
                    5:"0600040000000000",
                    7:"0800010001",
                }
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
                async def send_op(client,op,rx,current,wait_s=2.0):
                    current["op"]=f"{op:02X}"
                    before=len(rx)
                    emit(f"TX FFC1 OP {op:02X}")
                    await asyncio.wait_for(client.write_gatt_char(FFC1,bytes([op]),response=False),timeout=4)
                    deadline=time.monotonic()+wait_s
                    while time.monotonic()<deadline and len(rx)==before and client.is_connected:
                        await asyncio.sleep(.05)
                    return rx[before:]

                b001_rx=[]; ffc2_rx=[]; current={"op":"--"}
                try:
                    emit("1/8 · Abriendo GATT y estableciendo handshake B002.")
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
                        evt={"t":time.monotonic()-t0,"op":current["op"],"rx":raw.hex(),"len":len(raw)}
                        ffc2_rx.append(evt)
                        self.root.after(0,lambda e=evt:append("FFC2 RX · "+str(e)))
                    await asyncio.wait_for(c.start_notify(FFC2,ffc2_cb),timeout=5)
                    emit("FFC2 NOTIFY OK")

                    emit("3/8 · Revalidando OP01, OP05 y OP07.")
                    for op in (1,5,7):
                        new=await send_op(c,op,ffc2_rx,current,2.5)
                        emit(f"OP {op:02X} revalidación="+str(new))
                        if not new or new[0]["rx"]!=KNOWN[op]:
                            emit(f"STOP · OP {op:02X} cambió respecto de la firma conocida.")
                            return report
                        await asyncio.sleep(.8)
                    emit("OP01/05/07 ESTABLES")

                    emit("4/8 · Validando determinismo de OP07 dos veces más.")
                    op07_repeat=[]
                    for n in range(2):
                        new=await send_op(c,7,ffc2_rx,current,2.5)
                        vals=[x["rx"] for x in new]
                        op07_repeat.append(vals)
                        emit(f"OP07 repetición {n+2}="+str(new)+" · GATT="+str(bool(c.is_connected)))
                        if not new or any(x["rx"]!=KNOWN[7] for x in new):
                            emit("STOP · OP07 no fue determinista.")
                            return report
                        await asyncio.sleep(.8)

                    emit("5/8 · Mapeando OP08–OP0F. Si hay respuesta >=5B, la registro y continúo tras 4 s si GATT sigue estable.")
                    results=[]; stop_reason=None
                    for op in range(8,16):
                        if not c.is_connected:
                            stop_reason=f"GATT cayó antes de OP {op:02X}"
                            break
                        try:
                            new=await send_op(c,op,ffc2_rx,current,2.0)
                        except Exception as ex:
                            stop_reason=f"WRITE ERROR OP {op:02X}: {type(ex).__name__}: {ex}"
                            emit(stop_reason); break
                        vals=[x["rx"] for x in new]
                        results.append((f"{op:02X}",vals,bool(c.is_connected)))
                        emit(f"OP {op:02X} · respuestas="+str(new)+" · GATT="+str(bool(c.is_connected)))
                        if not c.is_connected:
                            stop_reason=f"OP {op:02X} provocó desconexión"
                            break
                        if new:
                            for evt in new:
                                raw=bytes.fromhex(evt["rx"])
                                emit(f"PARSE OP {op:02X} RX · resp_opcode=0x{raw[0]:02X} · bytes={list(raw)} · len={len(raw)}")
                            if any(x["len"]<=4 for x in new):
                                stop_reason=f"OP {op:02X} produjo respuesta corta <=4B; detención de seguridad"
                                break
                            emit(f"OP {op:02X} produjo respuesta estable candidata; observo 4 s antes de continuar.")
                            hold=time.monotonic()
                            while time.monotonic()-hold<4:
                                await asyncio.sleep(.25)
                                if not c.is_connected:
                                    stop_reason=f"OP {op:02X} produjo caída diferida"
                                    break
                            if stop_reason:
                                break
                        await asyncio.sleep(.5)

                    emit("6/8 · RESULTADOS 08–0F="+str(results))
                    emit("STOP_REASON="+str(stop_reason))
                    emit("7/8 · RESUMEN DE PATRÓN")
                    pairs=[]
                    for op,vals,alive in results:
                        if vals:
                            try:
                                first=bytes.fromhex(vals[0])
                                pairs.append((op,f"{first[0]:02X}",vals[0],alive))
                            except Exception:
                                pass
                    emit("PARES request→response="+str(pairs))
                    if pairs and all(int(resp,16)==int(req,16)+1 for req,resp,_,_ in pairs):
                        emit("PATRÓN DETECTADO · los opcodes con respuesta siguen request impar → response request+1.")
                    emit("8/8 · PRUEBA V0.39 FINALIZADA · sin escrituras FFC2 y sin bloques de firmware.")
                except Exception as ex:
                    emit("PRUEBA V0.39 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=230),lambda r,e:append("PRUEBA V0.39 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.39 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.39 LISTA · 1º PRUEBA V0.39; 2º COPIAR DIAGNÓSTICO. Revalida OP01/05/07 y completa 08–0F sin transferir firmware.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.39 aplicado")
