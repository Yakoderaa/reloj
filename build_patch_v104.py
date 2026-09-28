from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.03.0"' not in s: raise SystemExit('V1.04 requiere V1.03')
s=s.replace('APP_VERSION="1.03.0"','APP_VERSION="1.04.0"',1).replace('V1.03','V1.04')
old='''                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.25)
'''
new='''                    notify_errors=[]
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
if old not in s: raise SystemExit('V1.04: start_notify base no encontrado')
s=s.replace(old,new,1)
s=s.replace('V1.04 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.04; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Busca cada intento por firma E91A/3802 y conecta al objeto BLE recién descubierto.','V1.04 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.04; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Renueva la sesión BLE automáticamente si B001 notify falla.')
s=s.replace('V1.04 · RECUPERACIÓN BLE POR FIRMA · V1.02 falló porque find_device_by_address dejó de ver la dirección aunque el diagnóstico sí veía anuncios. Cada intento hace discovery completo, identifica E91A/3802 y conecta al objeto fresco; conserva transferencia y esfera aprobadas.','V1.04 · RECUPERACIÓN B001 NOTIFY · V1.03 ya abrió B001/B002; ahora renueva la sesión BLE y vuelve a intentar notify antes de iniciar el protocolo OEM.')
p.write_text(s,encoding='utf-8')
print('overlay V1.04 aplicado')
