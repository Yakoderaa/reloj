from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.07.0"' not in s: raise SystemExit('V1.08 requiere V1.07')
s=s.replace('APP_VERSION="1.07.0"','APP_VERSION="1.08.0"',1).replace('V1.07','V1.08')
# V1.07 exhausted seven fresh client sessions and still hit cached GATT / ATT
# Unreachable. The next recovery boundary is the Windows Bluetooth radio itself.
# Do one controlled PowerShell PnP restart after repeated failures, then resume the
# exact signature-discovery + physical CCCD gate. This does not alter watch pairing,
# firmware, face data, or factory settings.
needle="""        for i in range(max(1,7)):
            client=None;ok=False
"""
repl="""        radio_reset_done=False
        for i in range(max(1,7)):
            client=None;ok=False
            if i==4 and not radio_reset_done:
                radio_reset_done=True
                progress('RECUPERACIÓN WINDOWS · reiniciando adaptador Bluetooth PnP una sola vez...')
                try:
                    import subprocess
                    ps=(\"$d=Get-PnpDevice -Class Bluetooth -Status OK | Where-Object { $_.FriendlyName -match 'Bluetooth|Radio|Adapter' } | Select-Object -First 1; \"
                        \"if($d){ Disable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false -ErrorAction Stop; Start-Sleep -Seconds 2; Enable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false -ErrorAction Stop; Write-Output $d.FriendlyName } else { throw 'Bluetooth adapter not found' }\")
                    cp=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-Command',ps],capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    if cp.returncode==0:
                        progress('RECUPERACIÓN WINDOWS OK · '+(cp.stdout.strip() or 'adaptador reiniciado'))
                        await asyncio.sleep(8)
                    else:
                        progress('RECUPERACIÓN WINDOWS NO DISPONIBLE · '+(cp.stderr.strip() or 'requiere permisos de Windows'))
                except Exception as rex:
                    progress('RECUPERACIÓN WINDOWS OMITIDA · '+type(rex).__name__+': '+str(rex))
            client=None;ok=False
"""
if needle not in s: raise SystemExit('loop V1.07 no encontrado')
s=s.replace(needle,repl,1)
s=s.replace('V1.08 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.08; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Recuperación física larga de Windows tras ATT Unreachable; sin tocar pairing ni fábrica.','V1.08 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.08; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Si ATT sigue muerto, reinicia una vez el adaptador Bluetooth de Windows y reintenta automáticamente.')
s=s.replace('V1.08 · RECUPERACIÓN ATT WINDOWS · V1.06 aisló la causa: incluso leer CCCD handle 46 devuelve Unreachable. Se mantiene ese gate, pero cada fallo destruye la sesión y usa cooldown progresivo + anuncio fresco hasta 7 rondas. No se envían comandos OEM hasta obtener ATT real.','V1.08 · RADIO RESET CONTROLADO · V1.07 agotó siete sesiones frescas y confirmó que el estado muerto persiste en Windows. Tras cuatro rondas fallidas intenta reiniciar una sola vez el adaptador Bluetooth PnP, espera su recuperación y continúa con discovery por firma + CCCD ATT real. No toca pairing, firmware ni esfera.')
p.write_text(s,encoding='utf-8')
print('overlay V1.08 aplicado')
