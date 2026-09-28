from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.12.0"' not in s: raise SystemExit('V1.13 requiere V1.12')
old="""                                progress('RECUPERACIÓN WINDOWS ELEVADA OK · adaptador Bluetooth reiniciado.')
                                progress('REINICIO DE RELOJ LAB REQUERIDO · cerrando esta instancia para liberar completamente WinRT/Bleak. Abrí Reloj Lab otra vez y pulsá INSTALAR ESFERA SINCRONIZADA V1.12.')
                                await asyncio.sleep(2)
                                raise SystemExit(0)
"""
new="""                                progress('RECUPERACIÓN WINDOWS ELEVADA OK · adaptador Bluetooth reiniciado.')
                                try:
                                    marker=Path.home()/'AppData'/'Local'/'RelojLab'/'radio-reset-v113.flag'
                                    marker.parent.mkdir(parents=True,exist_ok=True)
                                    marker.write_text('1',encoding='utf-8')
                                except Exception as marker_ex:
                                    progress('MARCADOR POST-RESET OMITIDO · '+type(marker_ex).__name__+': '+str(marker_ex))
                                progress('REINICIO DE RELOJ LAB REQUERIDO · cerrando esta instancia para liberar completamente WinRT/Bleak. Abrí Reloj Lab otra vez y pulsá INSTALAR ESFERA SINCRONIZADA V1.13.')
                                await asyncio.sleep(2)
                                raise SystemExit(0)
"""
if old not in s: raise SystemExit('bloque post-reset V1.12 no encontrado')
s=s.replace(old,new,1)
lines=s.splitlines(keepends=True)
idx=None
for i,line in enumerate(lines):
    # V1.12 emits this exact progress line at the start of the install coroutine.
    # Match the stable message text rather than a literal source-code quoting style.
    if 'Cargando diseño aprobado 240×296' in line:
        idx=i; break
if idx is None: raise SystemExit('inicio instalación V1.12 no encontrado')
indent=lines[idx][:len(lines[idx])-len(lines[idx].lstrip())]
block=(indent+'try:\n'+indent+"    marker=Path.home()/'AppData'/'Local'/'RelojLab'/'radio-reset-v113.flag'\n"+indent+'    if marker.exists():\n'+indent+'        marker.unlink(missing_ok=True)\n'+indent+"        progress('POST-RESET DETECTADO · proceso WinRT/Bleak nuevo; esperando 12s a que Windows estabilice GATT antes del discovery...')\n"+indent+'        await asyncio.sleep(12)\n'+indent+'except Exception as marker_ex:\n'+indent+"    progress('POST-RESET MARKER OMITIDO · '+type(marker_ex).__name__+': '+str(marker_ex))\n")
lines.insert(idx+1,block)
s=''.join(lines)
s=s.replace('APP_VERSION="1.12.0"','APP_VERSION="1.13.0"',1).replace('V1.12','V1.13')
s=s.replace('V1.13 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.13; 2º SI PIDE UAC, ACEPTAR; 3º CUANDO RELOJ LAB SE CIERRE, ABRIRLO DE NUEVO; 4º INSTALAR ESFERA SINCRONIZADA V1.13; 5º COPIAR DIAGNÓSTICO. Cierre limpio tras reset Bluetooth.','V1.13 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.13; 2º SI PIDE UAC, ACEPTAR; 3º CUANDO SE CIERRE, ABRIR RELOJ LAB; 4º INSTALAR ESFERA SINCRONIZADA V1.13; 5º COPIAR DIAGNÓSTICO. Recuerda el reset entre procesos y deja estabilizar GATT.')
s=s.replace('V1.13 · CIERRE LIMPIO POST-RESET · V1.11 confirmó el reset elevado, pero su RuntimeError fue capturado por un handler exterior y el proceso viejo siguió intentando BLE. Ahora usa SystemExit, que no es capturado por los handlers Exception de recuperación; al reabrir Reloj Lab WinRT/Bleak nace desde cero. No toca pairing, fábrica, firmware ni esfera.','V1.13 · POST-RESET PERSISTENTE · V1.12 ya cerró correctamente después del reset elevado. Ahora guarda ese estado antes de salir; al reabrir, la nueva instancia reconoce que Windows acaba de recrear la radio, espera estabilización GATT y recién entonces inicia discovery. No toca pairing, fábrica, firmware ni esfera.')
p.write_text(s,encoding='utf-8')
print('overlay V1.13 aplicado')
