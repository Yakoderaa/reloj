from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.09.0"' not in s: raise SystemExit('V1.10 requiere V1.09')
s=s.replace('APP_VERSION="1.09.0"','APP_VERSION="1.10.0"',1).replace('V1.09','V1.10')
# V1.09 reached the intended elevated recovery branch but failed before UAC
# because Path was not imported inside the frozen runtime path. Fix only that
# concrete defect; keep the proven BLE discovery, GATT and physical CCCD gate.
old="""                            import tempfile, os
                            helper=Path(tempfile.gettempdir())/'reloj_lab_bt_reset.ps1'
"""
new="""                            import tempfile, os
                            from pathlib import Path as _RecoveryPath
                            helper=_RecoveryPath(tempfile.gettempdir())/'reloj_lab_bt_reset.ps1'
"""
if old not in s: raise SystemExit('helper V1.09 no encontrado')
s=s.replace(old,new,1)
s=s.replace('V1.10 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.10; 2º ACEPTAR UAC SI WINDOWS LO PIDE; 3º REVISAR HORA/PASOS/PULSO; 4º COPIAR DIAGNÓSTICO. Recupera el adaptador Bluetooth con elevación sólo si PnP normal es denegado.','V1.10 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.10; 2º ACEPTAR UAC CUANDO WINDOWS LO PIDA; 3º REVISAR HORA/PASOS/PULSO; 4º COPIAR DIAGNÓSTICO. Corrige el helper elevado que V1.09 no llegó a ejecutar.')
s=s.replace('V1.10 · RADIO RESET CON UAC · V1.08 confirmó HRESULT 0x80041001 al deshabilitar PnP sin elevación. Mantiene intacta la ruta BLE probada; sólo si ese reset es denegado solicita UAC una vez, cicla el adaptador y continúa discovery por firma + CCCD ATT real. No toca pairing, fábrica, firmware ni esfera.','V1.10 · UAC HELPER CORREGIDO · V1.09 llegó a la recuperación elevada pero falló por NameError: Path. Se corrige ese defecto concreto y se mantiene intacta la ruta BLE: PnP normal → UAC si es denegado → reinicio del adaptador → discovery por firma → CCCD ATT real. No toca pairing, fábrica, firmware ni esfera.')
p.write_text(s,encoding='utf-8')
print('overlay V1.10 aplicado')
