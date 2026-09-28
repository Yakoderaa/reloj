from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.06.0"' not in s: raise SystemExit('V1.07 requiere V1.06')
s=s.replace('APP_VERSION="1.06.0"','APP_VERSION="1.07.0"',1).replace('V1.06','V1.07')
# V1.06 proved the exact failure is below our OEM protocol: even a read-only ATT
# descriptor access on the known CCCD handle 46 returns Unreachable. Increase the
# recovery horizon instead of adding another OEM write. After an Unreachable gate,
# fully dispose the client and wait for the watch to resume advertising before a
# fresh discovery/client attempt. No pairing changes and no factory reset.
s=s.replace("for i in range(max(1,attempts)):","for i in range(max(1,7)):",1)
s=s.replace("self.connection_state['attempts']=i+1","self.connection_state['attempts']=i+1",1)
s=s.replace("progress(f\"CONEXIÓN {i+1}/{attempts} · escaneo por firma UtraWatch E91A/3802...\")","progress(f\"CONEXIÓN {i+1}/7 · escaneo por firma UtraWatch E91A/3802...\")",1)
old="""                except Exception as gate_ex:
                    raise RuntimeError('B001/B002 visibles pero ATT físico no operativo: '+type(gate_ex).__name__+': '+str(gate_ex))
"""
new="""                except Exception as gate_ex:
                    self.connection_state['last_physical_gate']=type(gate_ex).__name__+': '+str(gate_ex)
                    progress('ATT UNREACHABLE · la caché GATT existe pero Windows no tiene bearer ATT; se descartará COMPLETAMENTE esta sesión.')
                    raise RuntimeError('B001/B002 visibles pero ATT físico no operativo: '+type(gate_ex).__name__+': '+str(gate_ex))
"""
if old not in s: raise SystemExit('gate V1.06 no encontrado')
s=s.replace(old,new,1)
old2="""            if i+1<attempts:
                wait=4+2*i
                progress(f\"RECUPERACIÓN BLE · liberando sesión Windows {wait}s...\")
                await asyncio.sleep(wait)
"""
new2="""            if i+1<7:
                # Give Windows and the watch enough time to tear down the stale ATT
                # bearer. Short 4-10 s loops in V1.03-V1.06 repeatedly hit the same
                # cached/dead state. Later rounds intentionally cool down longer.
                waits=(6,10,15,20,25,30)
                wait=waits[min(i,len(waits)-1)]
                progress(f\"RECUPERACIÓN FÍSICA · sesión cerrada; esperando {wait}s y un anuncio nuevo antes de recrear BleakClient...\")
                await asyncio.sleep(wait)
"""
if old2 not in s: raise SystemExit('recovery V1.06 no encontrado')
s=s.replace(old2,new2,1)
s=s.replace('V1.07 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.07; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Sólo acepta GATT después de una lectura ATT real del CCCD B001.','V1.07 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.07; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Recuperación física larga de Windows tras ATT Unreachable; sin tocar pairing ni fábrica.')
s=s.replace('V1.07 · PHYSICAL READY CCCD · V1.05 confirmó que ver B001=44/B002=42 no demuestra una sesión física: notify la dejó desconectada. Ahora connect_retry sólo entrega una sesión si el descriptor CCCD 0x2902 de B001 responde a una lectura ATT real; si no, sigue buscando sin iniciar la transferencia.','V1.07 · RECUPERACIÓN ATT WINDOWS · V1.06 aisló la causa: incluso leer CCCD handle 46 devuelve Unreachable. Se mantiene ese gate, pero cada fallo destruye la sesión y usa cooldown progresivo + anuncio fresco hasta 7 rondas. No se envían comandos OEM hasta obtener ATT real.')
p.write_text(s,encoding='utf-8')
print('overlay V1.07 aplicado')
