from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.08.0"' not in s: raise SystemExit('V1.09 requiere V1.08')
s=s.replace('APP_VERSION="1.08.0"','APP_VERSION="1.09.0"',1).replace('V1.08','V1.09')
# V1.08 isolated a Windows permission boundary: Disable-PnpDevice itself failed.
# Do not change the proven watch discovery/GATT/CCCD path. If normal PnP reset is
# denied, launch ONE elevated helper via UAC (RunAs), wait for it to finish, then
# continue discovery. The helper only cycles the Bluetooth adapter; it does not
# unpair/reset/modify the watch.
old="""                    else:
                        progress('RECUPERACIÓN WINDOWS NO DISPONIBLE · '+(cp.stderr.strip() or 'requiere permisos de Windows'))
                except Exception as rex:
                    progress('RECUPERACIÓN WINDOWS OMITIDA · '+type(rex).__name__+': '+str(rex))
"""
new="""                    else:
                        progress('RECUPERACIÓN WINDOWS · PnP normal denegado; solicitando elevación UAC una sola vez...')
                        try:
                            import tempfile, os
                            helper=Path(tempfile.gettempdir())/'reloj_lab_bt_reset.ps1'
                            helper.write_text(\"$ErrorActionPreference='Stop'\\n$d=Get-PnpDevice -Class Bluetooth -Status OK | Where-Object { $_.FriendlyName -match 'Bluetooth|Radio|Adapter' } | Select-Object -First 1\\nif(-not $d){exit 21}\\nDisable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false\\nStart-Sleep -Seconds 3\\nEnable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false\\nStart-Sleep -Seconds 5\\nexit 0\\n\",encoding='utf-8')
                            launcher=(\"$p=Start-Process powershell -Verb RunAs -Wait -PassThru -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \\\"\"+str(helper)+\"\\\"'; exit $p.ExitCode\")
                            elevated=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-Command',launcher],capture_output=True,text=True,timeout=45,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                            if elevated.returncode==0:
                                progress('RECUPERACIÓN WINDOWS ELEVADA OK · adaptador Bluetooth reiniciado; esperando advertising...')
                                await asyncio.sleep(10)
                            else:
                                progress('RECUPERACIÓN WINDOWS ELEVADA NO COMPLETADA · código '+str(elevated.returncode))
                        except Exception as elev_ex:
                            progress('RECUPERACIÓN WINDOWS ELEVADA OMITIDA · '+type(elev_ex).__name__+': '+str(elev_ex))
                except Exception as rex:
                    progress('RECUPERACIÓN WINDOWS OMITIDA · '+type(rex).__name__+': '+str(rex))
"""
if old not in s: raise SystemExit('bloque radio V1.08 no encontrado')
s=s.replace(old,new,1)
s=s.replace('V1.09 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.09; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Si ATT sigue muerto, reinicia una vez el adaptador Bluetooth de Windows y reintenta automáticamente.','V1.09 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.09; 2º ACEPTAR UAC SI WINDOWS LO PIDE; 3º REVISAR HORA/PASOS/PULSO; 4º COPIAR DIAGNÓSTICO. Recupera el adaptador Bluetooth con elevación sólo si PnP normal es denegado.')
s=s.replace('V1.09 · RADIO RESET CONTROLADO · V1.07 agotó siete sesiones frescas y confirmó que el estado muerto persiste en Windows. Tras cuatro rondas fallidas intenta reiniciar una sola vez el adaptador Bluetooth PnP, espera su recuperación y continúa con discovery por firma + CCCD ATT real. No toca pairing, firmware ni esfera.','V1.09 · RADIO RESET CON UAC · V1.08 confirmó HRESULT 0x80041001 al deshabilitar PnP sin elevación. Mantiene intacta la ruta BLE probada; sólo si ese reset es denegado solicita UAC una vez, cicla el adaptador y continúa discovery por firma + CCCD ATT real. No toca pairing, fábrica, firmware ni esfera.')
p.write_text(s,encoding='utf-8')
print('overlay V1.09 aplicado')
