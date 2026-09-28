from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.04.0"' not in s: raise SystemExit('V1.05 requiere V1.04')
s=s.replace('APP_VERSION="1.04.0"','APP_VERSION="1.05.0"',1).replace('V1.04','V1.05')
old='''                    notify_errors=[]
                    notify_ok=False
                    for notify_try in range(1,4):
                        try:
                            emit("B001 NOTIFY "+str(notify_try)+"/3")
                            await asyncio.wait_for(c.start_notify(b001,rx),timeout=8)
                            await asyncio.sleep(.35)
                            notify_ok=True
                            emit("B001 NOTIFY OK")
                            break
                        except Exception as nex:
                            notify_errors.append(type(nex).__name__+": "+str(nex))
                            emit("B001 NOTIFY FALLÓ · "+notify_errors[-1])
                            try:
                                if c and c.is_connected: await asyncio.wait_for(c.disconnect(),timeout=4)
                            except Exception: pass
                            if notify_try>=3: break
                            await asyncio.sleep(4+notify_try*2)
                            c,_=await self.connect_retry(5,emit)
                            b001=c.services.get_characteristic("0000b001-0000-1000-8000-00805f9b34fb")
                            b002=c.services.get_characteristic("0000b002-0000-1000-8000-00805f9b34fb")
                            if b001 is None or b002 is None: raise RuntimeError("reconexión sin B001/B002")
                    rep["single_face_install"]["notify_recovery"]={"errors":notify_errors,"ok":notify_ok}
                    if not notify_ok: raise RuntimeError("B001 notify no operativo: "+" | ".join(notify_errors))
'''
new='''                    # V1.04 proved that throwing away a rare valid B001/B002 session after
                    # one notify timeout is counterproductive. Keep it alive and let WinRT/CCCD
                    # settle; retry start_notify on the SAME characteristic/session first.
                    notify_errors=[]
                    notify_ok=False
                    for notify_try,delay in enumerate((0.0,1.5,3.0,5.0),1):
                        if delay:
                            emit(f"B001 CCCD · esperando {delay:.1f}s en la MISMA sesión GATT...")
                            await asyncio.sleep(delay)
                        try:
                            emit(f"B001 NOTIFY MISMA SESIÓN {notify_try}/4 · handle={getattr(b001,'handle',None)}")
                            await asyncio.wait_for(c.start_notify(b001,rx),timeout=12)
                            await asyncio.sleep(.5)
                            notify_ok=True
                            emit("B001 NOTIFY OK · sesión GATT conservada")
                            break
                        except Exception as nex:
                            err=type(nex).__name__+": "+str(nex)
                            notify_errors.append(err)
                            emit("B001 NOTIFY FALLÓ · "+err)
                            if not c.is_connected:
                                emit("B001 · Windows marcó la sesión desconectada; no se destruye otra sesión válida innecesariamente.")
                                break
                    rep["single_face_install"]["notify_recovery"]={"errors":notify_errors,"ok":notify_ok,"strategy":"same_gatt_session_cccd_settle"}
                    if not notify_ok: raise RuntimeError("B001 notify no operativo en sesión GATT válida: "+" | ".join(notify_errors))
'''
if old not in s: raise SystemExit('V1.05: bloque notify V1.04 no encontrado')
s=s.replace(old,new,1)
s=s.replace('V1.05 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.05; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Renueva la sesión BLE automáticamente si B001 notify falla.','V1.05 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.05; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Conserva la sesión GATT válida y reintenta B001/CCCD sin reconectar.')
s=s.replace('V1.05 · RECUPERACIÓN B001 NOTIFY · V1.03 ya abrió B001/B002; ahora renueva la sesión BLE y vuelve a intentar notify antes de iniciar el protocolo OEM.','V1.05 · B001 MISMA SESIÓN · V1.04 demostró que una sesión válida con B001=44/B002=42 puede tardar en habilitar CCCD. Ya no la descarta tras el primer timeout: espera y reintenta notify sobre la misma sesión antes del protocolo OEM.')
p.write_text(s,encoding='utf-8')
print('overlay V1.05 aplicado')
