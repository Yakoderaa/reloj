from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.31.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.31")', 1)

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
        primary_test=ttk.Button(row,text="PRUEBA V0.31 - CAPTURAR SALIDA BOOT")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            append("PRUEBA V0.31: A/B sin FFC2 ni escrituras; captura el salto boot/app y reconecta en el primer anuncio.")
            async def work():
                c=None; report=[]; address=self.selected.get("address") or getattr(self.selected.get("device"),"address",None)
                t0=time.monotonic()
                def emit(m):
                    stamp=time.monotonic()-t0
                    line=f"+{stamp:06.2f}s · {m}"
                    report.append(line)
                    self.root.after(0,lambda x=line:(append(x),self.status.set(x)))
                def inventory(client):
                    out={}
                    for svc in client.services:
                        out[str(svc.uuid)]=sorted((str(ch.uuid),tuple(sorted(ch.properties))) for ch in svc.characteristics)
                    return out
                def adv_data(dev,adv):
                    name=(getattr(dev,"name",None) or getattr(adv,"local_name",None) or "")
                    uuids=list(sorted(getattr(adv,"service_uuids",None) or []))
                    mfg={str(k):bytes(v).hex() for k,v in (getattr(adv,"manufacturer_data",None) or {}).items()}
                    return name,uuids,mfg
                try:
                    emit("1/6 · Buscando el reloj y abriendo GATT con DEVICE + CACHE OFF…")
                    target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=12),timeout=15)
                    if target is None:
                        raise RuntimeError("reloj no visible en advertising")
                    c=BleakClient(target,timeout=25,winrt={"use_cached_services":False})
                    await asyncio.wait_for(c.connect(),timeout=30)
                    if not c.is_connected:
                        raise RuntimeError("is_connected=False")
                    before=inventory(c)
                    emit(f"2/6 · GATT INICIAL OK · servicios={len(before)} · MTU={getattr(c,'mtu_size','?')}")
                    for u,chars in before.items():
                        emit("PRE SERVICE "+u+" · chars="+str(chars))
                    emit("3/6 · CONTROL A/B: 35 s conectado SIN FFC2 notify y SIN escribir FFC1.")
                    lost_at=None
                    for tick in range(140):
                        await asyncio.sleep(.25)
                        if not c.is_connected:
                            lost_at=time.monotonic()-t0
                            emit(f"DESCONEXIÓN ESPONTÁNEA detectada @{lost_at:.2f}s")
                            break
                        if tick and tick%40==0:
                            emit(f"GATT sigue conectado · {(tick+1)//4}s de observación")
                    if lost_at is None:
                        emit("GATT SOBREVIVIÓ 35 s sin FFC2: la desconexión anterior estaba ligada a la ruta OAD/notify o a su estado.")
                        try: await asyncio.wait_for(c.disconnect(),timeout=4)
                        except Exception: pass
                        c=None
                        emit("4/6 · Desconexión controlada; pruebo reconexión fresca para verificar estabilidad.")
                    else:
                        try: await asyncio.wait_for(c.disconnect(),timeout=3)
                        except Exception: pass
                        c=None
                        emit("4/6 · Busco inmediatamente el PRIMER advertising tras la caída.")
                    post=None; post_adv=None; attempts=0
                    deadline=time.monotonic()+75
                    while time.monotonic()<deadline and post is None:
                        try:
                            found=await asyncio.wait_for(BleakScanner.discover(timeout=1.0,return_adv=True),timeout=2.5)
                            items=found.values() if isinstance(found,dict) else []
                            match=None
                            for dev,adv in items:
                                if str(getattr(dev,"address",None)).casefold()==str(address).casefold():
                                    match=(dev,adv); break
                            if match is None:
                                await asyncio.sleep(.15)
                                continue
                            dev,adv=match
                            name,uuids,mfg=adv_data(dev,adv)
                            attempts+=1
                            emit(f"ADV #{attempts} · name={name!r} · services={uuids} · mfg={mfg}")
                            post_adv=(name,uuids,mfg)
                            candidate=BleakClient(dev,timeout=10,winrt={"use_cached_services":False})
                            try:
                                emit(f"RECONEXIÓN INMEDIATA #{attempts} · DEVICE + CACHE OFF")
                                await asyncio.wait_for(candidate.connect(),timeout=12)
                                if not candidate.is_connected:
                                    raise RuntimeError("is_connected=False")
                                c=candidate
                                post=inventory(c)
                                emit(f"5/6 · GATT POST OK · servicios={len(post)} · MTU={getattr(c,'mtu_size','?')}")
                            except Exception as ex:
                                emit(f"RECONEXIÓN #{attempts} FALLÓ · {type(ex).__name__}: {ex}")
                                try: await asyncio.wait_for(candidate.disconnect(),timeout=2)
                                except Exception: pass
                                await asyncio.sleep(.25)
                        except Exception as ex:
                            emit("SCAN/RECONNECT parcial · "+type(ex).__name__+": "+str(ex))
                    emit("6/6 · RESULTADO")
                    if post is None:
                        emit("No logré abrir GATT en la ventana inmediata de 75 s.")
                    else:
                        emit("CAMBIO GATT="+str(post!=before))
                        for u in sorted(set(before)|set(post)):
                            if before.get(u)!=post.get(u):
                                emit("DIF GATT "+u+" PRE="+str(before.get(u))+" POST="+str(post.get(u)))
                        for u,chars in post.items():
                            emit("POST SERVICE "+u+" · chars="+str(chars))
                        if post_adv:
                            emit("ADV QUE PERMITIÓ CONEXIÓN="+str(post_adv))
                    emit("PRUEBA V0.31 FINALIZADA · sin FFC1, sin transferencia de firmware.")
                except Exception as ex:
                    emit("PRUEBA V0.31 ERROR: "+type(ex).__name__+": "+str(ex))
                finally:
                    if c:
                        try: await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception: pass
                return report
            self.run_async(asyncio.wait_for(work(),timeout=180),lambda r,e:append("PRUEBA V0.31 WATCHDOG: "+repr(e)) if e else append("PRUEBA V0.31 FINALIZADA"))
'''
s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.31 LISTA · 1º PRUEBA V0.31; 2º COPIAR DIAGNÓSTICO. Pegame el texto completo al terminar.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

p.write_text(s,encoding="utf-8")
print("build patch v0.31 aplicado")
