from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.05.0"' not in s: raise SystemExit('V1.06 requiere V1.05')
s=s.replace('APP_VERSION="1.05.0"','APP_VERSION="1.06.0"',1).replace('V1.05','V1.06')
# V1.05 exposed the key fact: connect_retry returned as soon as cached B001/B002
# appeared, but start_notify immediately changed is_connected to false. Therefore
# that was not a usable physical ATT session. Validate the CCCD-bearing B001
# characteristic with a real descriptor read before handing the client to transfer.
needle='''                if b1 is None or b2 is None: raise RuntimeError('sesión GATT sin B001/B002')
                ok=True
                if self.selected is None:self.selected={}
'''
replacement='''                if b1 is None or b2 is None: raise RuntimeError('sesión GATT sin B001/B002')
                # PHYSICAL READY GATE: B001/B002 visibility can be cached. Reading
                # B001 CCCD (0x2902, historically handle 46) is a harmless ATT read
                # that must reach the peripheral. Only then is this session usable.
                cccd=None
                for d in (getattr(b1,'descriptors',None) or []):
                    if str(getattr(d,'uuid','')).lower()=='00002902-0000-1000-8000-00805f9b34fb':
                        cccd=d;break
                if cccd is None: raise RuntimeError('B001 sin descriptor CCCD 0x2902')
                progress(f"PHYSICAL READY · leyendo B001 CCCD handle={getattr(cccd,'handle',None)}...")
                try:
                    await asyncio.wait_for(client.read_gatt_descriptor(cccd.handle),timeout=7)
                except Exception as gate_ex:
                    raise RuntimeError('B001/B002 visibles pero ATT físico no operativo: '+type(gate_ex).__name__+': '+str(gate_ex))
                if not client.is_connected: raise RuntimeError('ATT respondió pero Windows marcó sesión desconectada')
                progress('PHYSICAL READY OK · CCCD respondió por ATT real')
                ok=True
                if self.selected is None:self.selected={}
'''
if needle not in s: raise SystemExit('V1.06: punto de conexión V1.03 no encontrado')
s=s.replace(needle,replacement,1)
s=s.replace('V1.06 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.06; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Conserva la sesión GATT válida y reintenta B001/CCCD sin reconectar.','V1.06 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.06; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Sólo acepta GATT después de una lectura ATT real del CCCD B001.')
s=s.replace('V1.06 · B001 MISMA SESIÓN · V1.04 demostró que una sesión válida con B001=44/B002=42 puede tardar en habilitar CCCD. Ya no la descarta tras el primer timeout: espera y reintenta notify sobre la misma sesión antes del protocolo OEM.','V1.06 · PHYSICAL READY CCCD · V1.05 confirmó que ver B001=44/B002=42 no demuestra una sesión física: notify la dejó desconectada. Ahora connect_retry sólo entrega una sesión si el descriptor CCCD 0x2902 de B001 responde a una lectura ATT real; si no, sigue buscando sin iniciar la transferencia.')
p.write_text(s,encoding='utf-8')
print('overlay V1.06 aplicado')
