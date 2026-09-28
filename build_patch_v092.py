from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.91.0"' not in s:
    raise SystemExit("V0.92 requiere la base V0.91 aplicada")
s=s.replace('APP_VERSION="0.91.0"','APP_VERSION="0.92.0"',1)
s=s.replace('V0.91','V0.92')

old='''                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.25)
'''
new='''                    # V0.91 proved that WinRT can open GATT through CACHE ON, but the
                    # immediate B001 CCCD write may still stall. B001 is notify-only and B002
                    # is write/write-without-response on this watch. Resolve the actual
                    # characteristic object and recover the notify channel before any file write.
                    notify_recovery=[]
                    notify_ok=False
                    notify_char=c.services.get_characteristic(b001)
                    write_char=c.services.get_characteristic(b002)
                    if notify_char is None or write_char is None:
                        raise RuntimeError("GATT abrió pero faltan B001/B002 en services")
                    rep["single_face_install"]["notify_characteristics"]={
                        "b001_handle":getattr(notify_char,"handle",None),
                        "b001_properties":list(getattr(notify_char,"properties",[]) or []),
                        "b002_handle":getattr(write_char,"handle",None),
                        "b002_properties":list(getattr(write_char,"properties",[]) or []),
                        "mtu":getattr(c,"mtu_size",None)
                    }

                    async def try_notify(label,timeout_s):
                        nonlocal notify_ok
                        emit(label+" · B001 notify…")
                        try:
                            await asyncio.wait_for(c.start_notify(notify_char,rx),timeout=timeout_s)
                            notify_ok=True
                            notify_recovery.append({"stage":label,"ok":True})
                            emit(label+" · B001 NOTIFY OK")
                            return True
                        except Exception as ex:
                            notify_recovery.append({"stage":label,"ok":False,"error":type(ex).__name__+": "+str(ex)})
                            emit(label+" · B001 notify FALLÓ · "+type(ex).__name__+": "+str(ex))
                            return False

                    await asyncio.sleep(1.5)
                    await try_notify("NOTIFY 1/3 · objeto GATT real",18.0)

                    if not notify_ok and bool(getattr(c,"is_connected",False)):
                        # Wake the ATT/GATT link with a valid DEVICE_INFO request on B002.
                        # We intentionally do not count this as a face/firmware write.
                        wake=bytearray(20)
                        wake[1]=1
                        wake[3]=1
                        wake[4]=3
                        wake[5]=0x02
                        wake[8]=0
                        wake[9]=0
                        emit("NOTIFY 2/3 · despertando enlace con DEVICE_INFO por B002…")
                        try:
                            await asyncio.wait_for(c.write_gatt_char(write_char,bytes(wake),response=False),timeout=8)
                            notify_recovery.append({"stage":"B002 wake DEVICE_INFO","ok":True})
                            await asyncio.sleep(1.2)
                        except Exception as ex:
                            notify_recovery.append({"stage":"B002 wake DEVICE_INFO","ok":False,
                                                    "error":type(ex).__name__+": "+str(ex)})
                        await try_notify("NOTIFY 2/3 · después de B002 wake",20.0)

                    if not notify_ok:
                        emit("NOTIFY 3/3 · reconexión caliente para renovar CCCD B001…")
                        try:
                            if c is not None and c.is_connected:
                                await asyncio.wait_for(c.disconnect(),timeout=6)
                        except Exception:
                            pass
                        await asyncio.sleep(1.5)
                        c,n2=await self.connect_retry(5,emit)
                        rep["connection"]["attempts_after_notify_recovery"]=n2
                        rep["connection"]["strategy_after_notify_recovery"]=self.connection_state.get("strategy")
                        notify_char=c.services.get_characteristic(b001)
                        write_char=c.services.get_characteristic(b002)
                        if notify_char is None or write_char is None:
                            raise RuntimeError("Reconexión caliente abrió GATT sin B001/B002")
                        await asyncio.sleep(2.5)
                        await try_notify("NOTIFY 3/3 · tras reconexión caliente",25.0)

                    rep["single_face_install"]["notify_recovery"]=notify_recovery
                    if not notify_ok:
                        raise RuntimeError("B001 NOTIFY NO DISPONIBLE: GATT abre, pero Windows no habilita el CCCD de notificaciones.")

                    await asyncio.sleep(.25)
'''
if old not in s:
    raise SystemExit("V0.92: start_notify V0.91 no encontrado")
s=s.replace(old,new,1)

s=s.replace(
    'V0.92 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.92; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Primero abre WinRT directo con la dirección conocida, sin depender del escaneo.',
    'V0.92 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.92; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Recupera B001 notify después de abrir GATT por WinRT.'
)
s=s.replace(
    'V0.92 · GATT DIRECTO WINRT · conserva la esfera sincronizada; usa un BLEDevice sintético con la dirección conocida para saltar el escaneo implícito de Windows y luego prueba random/cache/pair.',
    'V0.92 · GATT + NOTIFY RECOVERY · conserva la esfera sincronizada; tras abrir WinRT resuelve B001/B002 reales, recupera el CCCD notify y recién entonces inicia el protocolo OEM.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.92 aplicado")
