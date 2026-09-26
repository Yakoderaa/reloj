from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.32.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.32")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.32 - ENCONTRAR KEEPALIVE")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            append("PRUEBA V0.32: compara tráfico de lectura contra suscripción B001 para descubrir qué mantiene viva la sesión BLE.")
            async def work():
                c=None; report=[]; address=self.selected.get("address") or getattr(self.selected.get("device"),"address",None)
                t0=time.monotonic()
                DEVICE_NAME="00002a00-0000-1000-8000-00805f9b34fb"
                B001="0000b001-0000-1000-8000-00805f9b34fb"
                def emit(m):
                    stamp=time.monotonic()-t0
                    line=f"+{stamp:06.2f}s · {m}"
                    report.append(line)
                    self.root.after(0,lambda x=line:(append(x),self.status.set(x)))
                async def connect_fresh(label,window=75):
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

                phase_a_survived=False; phase_b_survived=False; b001_events=[]
                try:
                    emit("1/7 · FASE A: conectar y mantener tráfico inocuo leyendo Device Name cada 4 s.")
                    c=await connect_fresh("FASE A CONEXIÓN")
                    a_start=time.monotonic()
                    read_count=0
                    while time.monotonic()-a_start < 45:
                        if not c.is_connected:
                            emit(f"FASE A · GATT cayó tras {time.monotonic()-a_start:.2f}s")
                            break
                        try:
                            data=bytes(await asyncio.wait_for(c.read_gatt_char(DEVICE_NAME),timeout=3))
                            read_count+=1
                            emit(f"FASE A · KEEPALIVE READ #{read_count} · {data.hex()} · conectado={c.is_connected}")
                        except Exception as ex:
                            emit("FASE A · READ ERROR · "+type(ex).__name__+": "+str(ex))
                            if not c.is_connected:
                                break
                        await asyncio.sleep(4)
                    phase_a_survived=bool(c and c.is_connected and time.monotonic()-a_start>=40)
                    emit("2/7 · RESULTADO FASE A · "+("SOBREVIVIÓ" if phase_a_survived else "SE DESCONECTÓ"))
                    await disconnect_clean(c); c=None
                    await asyncio.sleep(2)

                    emit("3/7 · FASE B: reconectar, suscribirse SOLO a B001 y quedar en reposo 45 s.")
                    c=await connect_fresh("FASE B CONEXIÓN")
                    def b001_cb(sender,data):
                        h=bytes(data).hex(); b001_events.append((time.monotonic()-t0,h))
                        self.root.after(0,lambda x=h:append("B001 RX "+x))
                    try:
                        await asyncio.wait_for(c.start_notify(B001,b001_cb),timeout=5)
                        emit("FASE B · B001 NOTIFY habilitado")
                    except Exception as ex:
                        emit("FASE B · B001 NOTIFY ERROR · "+type(ex).__name__+": "+str(ex))
                    b_start=time.monotonic()
                    while time.monotonic()-b_start < 45:
                        await asyncio.sleep(1)
                        if not c.is_connected:
                            emit(f"FASE B · GATT cayó tras {time.monotonic()-b_start:.2f}s · eventos={len(b001_events)}")
                            break
                        elapsed=int(time.monotonic()-b_start)
                        if elapsed and elapsed%10==0:
                            emit(f"FASE B · {elapsed}s · conectado · eventos={len(b001_events)}")
                            await asyncio.sleep(.2)
                    phase_b_survived=bool(c and c.is_connected and time.monotonic()-b_start>=40)
                    emit("4/7 · RESULTADO FASE B · "+("SOBREVIVIÓ" if phase_b_survived else "SE DESCONECTÓ"))
                    if c and c.is_connected:
                        try: await c.stop_notify(B001)
                        except Exception: pass
                    await disconnect_clean(c); c=None

                    emit("5/7 · INTERPRETACIÓN AUTOMÁTICA")
                    if phase_a_survived and not phase_b_survived:
                        emit("LECTURAS periódicas mantienen vivo GATT; suscribirse a B001 por sí solo NO.")
                    elif phase_b_survived and not phase_a_survived:
                        emit("B001 NOTIFY mantiene vivo GATT; las lecturas periódicas NO.")
                    elif phase_a_survived and phase_b_survived:
                        emit("Ambas formas mantienen vivo GATT: existe timeout de inactividad y cualquier tráfico/CCCD puede evitarlo.")
                    else:
                        emit("Ninguna fase mantuvo GATT: probablemente hace falta handshake de aplicación por B002 o el reloj fuerza rotación de sesión.")

                    emit("6/7 · EVENTOS B001="+str(b001_events))
                    emit("7/7 · PRUEBA V0.32 FINALIZADA · no se escribió FFC1 ni se transfirió firmware.")
                except Exception as ex:
                    emit("PRUEBA V0.32 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    await disconnect_clean(c)
                return report
            self.run_async(asyncio.wait_for(work(),timeout=230),lambda r,e:append("PRUEBA V0.32 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.32 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.32 LISTA · 1º PRUEBA V0.32; 2º COPIAR DIAGNÓSTICO. La prueba decide si el keepalive es tráfico, B001 o un handshake B002.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.32 aplicado")
