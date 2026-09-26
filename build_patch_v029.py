from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.33.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.33")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.33 - HANDSHAKE B002")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PRUEBA V0.33 NO INICIADA · Bluetooth ocupado. Esperá a que termine la operación actual y volvé a pulsar el primer botón.")
                self.status.set("Bluetooth ocupado; esperá y volvé a pulsar PRUEBA V0.33.")
                return
            append("PRUEBA V0.33: prueba un frame B002 ya conocido como handshake único y luego como keepalive periódico.")
            async def work():
                c=None; report=[]; address=self.selected.get("address") or getattr(self.selected.get("device"),"address",None)
                t0=time.monotonic()
                B001="0000b001-0000-1000-8000-00805f9b34fb"
                B002="0000b002-0000-1000-8000-00805f9b34fb"
                HANDSHAKE=bytes.fromhex("00ff000101150000010010000000010000000000")
                def emit(m):
                    stamp=time.monotonic()-t0
                    line=f"+{stamp:06.2f}s · {m}"
                    report.append(line)
                    self.root.after(0,lambda x=line:(append(x),self.status.set(x)))
                async def connect_fresh(label,window=80):
                    deadline=time.monotonic()+window
                    attempt=0
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
                async def subscribe_b001(client, bucket, label):
                    def cb(sender,data):
                        h=bytes(data).hex()
                        bucket.append((time.monotonic()-t0,h))
                        self.root.after(0,lambda x=h,l=label:append(l+" RX "+x))
                    await asyncio.wait_for(client.start_notify(B001,cb),timeout=5)
                    emit(label+" · B001 NOTIFY habilitado")
                async def send_handshake(client,label):
                    await asyncio.wait_for(client.write_gatt_char(B002,HANDSHAKE,response=False),timeout=4)
                    emit(label+" · TX B002 "+HANDSHAKE.hex())

                one_shot_survived=False; periodic_survived=False
                rx_a=[]; rx_b=[]
                try:
                    emit("1/8 · FASE A: B001 + UN solo frame B002 conocido, luego 45 s sin más escrituras.")
                    c=await connect_fresh("FASE A CONEXIÓN")
                    await subscribe_b001(c,rx_a,"FASE A")
                    await asyncio.sleep(.3)
                    await send_handshake(c,"FASE A")
                    a_start=time.monotonic()
                    while time.monotonic()-a_start < 45:
                        await asyncio.sleep(1)
                        if not c.is_connected:
                            emit(f"FASE A · GATT cayó tras {time.monotonic()-a_start:.2f}s · RX={len(rx_a)}")
                            break
                        elapsed=int(time.monotonic()-a_start)
                        if elapsed and elapsed%10==0:
                            emit(f"FASE A · {elapsed}s conectado · RX={len(rx_a)}")
                            await asyncio.sleep(.15)
                    one_shot_survived=bool(c and c.is_connected and time.monotonic()-a_start>=40)
                    emit("2/8 · RESULTADO FASE A · "+("SOBREVIVIÓ" if one_shot_survived else "SE DESCONECTÓ"))
                    if c and c.is_connected:
                        try: await c.stop_notify(B001)
                        except Exception: pass
                    await disconnect_clean(c); c=None
                    await asyncio.sleep(2)

                    emit("3/8 · FASE B: reconectar y reenviar el mismo frame B002 cada 5 s durante 45 s.")
                    c=await connect_fresh("FASE B CONEXIÓN")
                    await subscribe_b001(c,rx_b,"FASE B")
                    b_start=time.monotonic(); tx_count=0
                    while time.monotonic()-b_start < 45:
                        if not c.is_connected:
                            emit(f"FASE B · GATT cayó tras {time.monotonic()-b_start:.2f}s · TX={tx_count} · RX={len(rx_b)}")
                            break
                        await send_handshake(c,f"FASE B KEEPALIVE #{tx_count+1}")
                        tx_count+=1
                        for _ in range(5):
                            await asyncio.sleep(1)
                            if not c.is_connected:
                                break
                    periodic_survived=bool(c and c.is_connected and time.monotonic()-b_start>=40)
                    emit("4/8 · RESULTADO FASE B · "+("SOBREVIVIÓ" if periodic_survived else "SE DESCONECTÓ"))
                    if c and c.is_connected:
                        try: await c.stop_notify(B001)
                        except Exception: pass
                    await disconnect_clean(c); c=None

                    emit("5/8 · INTERPRETACIÓN AUTOMÁTICA")
                    if one_shot_survived:
                        emit("El frame B002 conocido funciona como handshake suficiente para sostener la sesión.")
                    elif periodic_survived:
                        emit("El frame B002 conocido funciona como keepalive periódico, no como handshake único.")
                    else:
                        emit("El frame B002 conocido recibe/permite tráfico pero NO sostiene la sesión: necesitamos identificar el handshake exacto de la app.")
                    emit("6/8 · RX FASE A="+str(rx_a))
                    emit("7/8 · RX FASE B="+str(rx_b))
                    emit("8/8 · PRUEBA V0.33 FINALIZADA · no se escribió FFC1 ni se transfirió firmware.")
                except Exception as ex:
                    emit("PRUEBA V0.33 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=260),lambda r,e:append("PRUEBA V0.33 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.33 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.33 LISTA · 1º PRUEBA V0.33; 2º COPIAR DIAGNÓSTICO. Prueba handshake B002 único vs keepalive periódico.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.33 aplicado")
