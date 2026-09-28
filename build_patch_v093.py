from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.92.0"' not in s:
    raise SystemExit("V0.93 requiere la base V0.92 aplicada")
s=s.replace('APP_VERSION="0.92.0"','APP_VERSION="0.93.0"',1)
s=s.replace('V0.92','V0.93')

old='''                    # V0.91 proved that WinRT can open GATT through CACHE ON, but the
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
new='''                    # V0.92 proved that CACHE ON opens the correct GATT tree, but the very
                    # first *physical* ATT operation (B001 CCCD) returned Unreachable and dropped
                    # the session. V0.93 therefore forces a real write-with-response on B002
                    # BEFORE touching B001, then subscribes. If Bleak's CCCD helper still fails,
                    # it falls back to the actual 0x2902 descriptor.
                    notify_recovery=[]
                    notify_ok=False
                    manual_notify_token=None
                    notify_char=c.services.get_characteristic(b001)
                    write_char=c.services.get_characteristic(b002)
                    if notify_char is None or write_char is None:
                        raise RuntimeError("GATT abrió pero faltan B001/B002 en services")

                    descriptors=[]
                    for d in list(getattr(notify_char,"descriptors",[]) or []):
                        descriptors.append({
                            "uuid":str(getattr(d,"uuid","")),
                            "handle":getattr(d,"handle",None)
                        })

                    rep["single_face_install"]["notify_characteristics"]={
                        "b001_handle":getattr(notify_char,"handle",None),
                        "b001_properties":list(getattr(notify_char,"properties",[]) or []),
                        "b001_descriptors":descriptors,
                        "b002_handle":getattr(write_char,"handle",None),
                        "b002_properties":list(getattr(write_char,"properties",[]) or []),
                        "mtu_before_prewake":getattr(c,"mtu_size",None)
                    }

                    # Valid CEProtocolB DEVICE_INFO request. The write response itself is the
                    # important part here: it proves the ATT link is physically alive.
                    wake=bytearray(20)
                    wake[1]=1
                    wake[3]=1
                    wake[4]=3
                    wake[5]=0x02
                    wake[8]=0
                    wake[9]=0

                    async def prewake(label):
                        emit(label+" · B002 WRITE WITH RESPONSE…")
                        try:
                            await asyncio.wait_for(
                                c.write_gatt_char(write_char,bytes(wake),response=True),
                                timeout=14
                            )
                            notify_recovery.append({
                                "stage":label,"ok":True,
                                "mtu_after":getattr(c,"mtu_size",None),
                                "connected":bool(getattr(c,"is_connected",False))
                            })
                            emit(label+" · ATT FÍSICO OK")
                            await asyncio.sleep(1.0)
                            return True
                        except Exception as ex:
                            notify_recovery.append({
                                "stage":label,"ok":False,
                                "error":type(ex).__name__+": "+str(ex),
                                "connected":bool(getattr(c,"is_connected",False))
                            })
                            emit(label+" · FALLÓ · "+type(ex).__name__+": "+str(ex))
                            return False

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
                            notify_recovery.append({
                                "stage":label,"ok":False,
                                "error":type(ex).__name__+": "+str(ex),
                                "connected":bool(getattr(c,"is_connected",False))
                            })
                            emit(label+" · B001 notify FALLÓ · "+type(ex).__name__+": "+str(ex))
                            return False

                    async def manual_cccd_notify(label):
                        nonlocal notify_ok,manual_notify_token
                        emit(label+" · escribiendo descriptor 0x2902 directamente…")
                        cccd=None
                        for d in list(getattr(notify_char,"descriptors",[]) or []):
                            if str(getattr(d,"uuid","")).lower()=="00002902-0000-1000-8000-00805f9b34fb":
                                cccd=d
                                break
                        if cccd is None:
                            notify_recovery.append({"stage":label,"ok":False,"error":"CCCD 0x2902 no encontrado"})
                            return False
                        try:
                            loop=asyncio.get_running_loop()
                            winrt_char=getattr(notify_char,"obj",None)
                            if winrt_char is None:
                                raise RuntimeError("B001 sin objeto WinRT")
                            def _manual_value_changed(sender,args):
                                try:
                                    data=bytearray(args.characteristic_value)
                                    loop.call_soon_threadsafe(rx,sender,data)
                                except Exception:
                                    pass
                            manual_notify_token=winrt_char.add_value_changed(_manual_value_changed)
                            await asyncio.wait_for(
                                c.write_gatt_descriptor(cccd,b"\\x01\\x00"),
                                timeout=16
                            )
                            notify_ok=True
                            notify_recovery.append({
                                "stage":label,"ok":True,
                                "descriptor_handle":getattr(cccd,"handle",None)
                            })
                            emit(label+" · B001 NOTIFY OK por CCCD directo")
                            return True
                        except Exception as ex:
                            try:
                                if manual_notify_token is not None and getattr(notify_char,"obj",None) is not None:
                                    notify_char.obj.remove_value_changed(manual_notify_token)
                            except Exception:
                                pass
                            manual_notify_token=None
                            notify_recovery.append({
                                "stage":label,"ok":False,
                                "error":type(ex).__name__+": "+str(ex),
                                "connected":bool(getattr(c,"is_connected",False))
                            })
                            emit(label+" · FALLÓ · "+type(ex).__name__+": "+str(ex))
                            return False

                    await asyncio.sleep(1.0)
                    att_live=await prewake("PREWAKE 1/2")
                    if not att_live:
                        # One reconnect only; unlike V0.92, do not burn many stale-cache loops.
                        emit("PREWAKE · reconectando una vez antes de tocar B001…")
                        try:
                            if c is not None and c.is_connected:
                                await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception:
                            pass
                        await asyncio.sleep(1.0)
                        c,n2=await self.connect_retry(5,emit)
                        rep["connection"]["attempts_after_prewake_recovery"]=n2
                        rep["connection"]["strategy_after_prewake_recovery"]=self.connection_state.get("strategy")
                        notify_char=c.services.get_characteristic(b001)
                        write_char=c.services.get_characteristic(b002)
                        if notify_char is None or write_char is None:
                            raise RuntimeError("Reconexión abrió GATT sin B001/B002")
                        att_live=await prewake("PREWAKE 2/2")

                    if not att_live:
                        rep["single_face_install"]["notify_recovery"]=notify_recovery
                        raise RuntimeError("B002 ATT NO RESPONDE: servicios GATT visibles pero enlace físico no operativo.")

                    await try_notify("NOTIFY 1/2 · después de PREWAKE",18.0)
                    if not notify_ok and bool(getattr(c,"is_connected",False)):
                        await manual_cccd_notify("NOTIFY 2/2 · CCCD 0x2902 directo")

                    rep["single_face_install"]["notify_recovery"]=notify_recovery
                    rep["single_face_install"]["notify_characteristics"]["mtu_after_prewake"]=getattr(c,"mtu_size",None)
                    if not notify_ok:
                        raise RuntimeError("B001 NOTIFY NO DISPONIBLE incluso con ATT prewake + CCCD directo.")

                    await asyncio.sleep(.25)
'''
if old not in s:
    raise SystemExit("V0.93: bloque notify V0.92 no encontrado")
s=s.replace(old,new,1)

s=s.replace(
    'V0.93 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.93; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Recupera B001 notify después de abrir GATT por WinRT.',
    'V0.93 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.93; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Fuerza ATT real por B002 antes de habilitar B001.'
)
s=s.replace(
    'V0.93 · GATT + NOTIFY RECOVERY · conserva la esfera sincronizada; tras abrir WinRT resuelve B001/B002 reales, recupera el CCCD notify y recién entonces inicia el protocolo OEM.',
    'V0.93 · ATT PREWAKE + CCCD DIRECTO · conserva la esfera sincronizada; primero valida el enlace físico con B002 WRITE RESPONSE y luego habilita B001 por helper o descriptor 0x2902.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.93 aplicado")
