from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.10.0"' not in s: raise SystemExit('V1.11 requiere V1.10')
s=s.replace('APP_VERSION="1.10.0"','APP_VERSION="1.11.0"',1).replace('V1.10','V1.11')
# V1.10 proves the elevated PnP cycle succeeds. The remaining failure happens
# after the adapter is recreated: the already-running process keeps using the
# pre-reset WinRT/Bleak state. Exit cleanly after the successful radio reset so
# the user can reopen Reloj Lab and create a completely fresh Windows BLE stack.
old="""                            if elevated.returncode==0:
                                progress('RECUPERACIÓN WINDOWS ELEVADA OK · adaptador Bluetooth reiniciado; esperando advertising...')
                                await asyncio.sleep(10)
"""
new="""                            if elevated.returncode==0:
                                progress('RECUPERACIÓN WINDOWS ELEVADA OK · adaptador Bluetooth reiniciado.')
                                progress('REINICIO DE RELOJ LAB REQUERIDO · cerrando esta instancia para liberar completamente WinRT/Bleak. Abrí Reloj Lab otra vez y pulsá INSTALAR ESFERA SINCRONIZADA V1.11.')
                                await asyncio.sleep(2)
                                raise RuntimeError('RADIO_RESET_OK_RESTART_APP')
"""
if old not in s: raise SystemExit('bloque V1.10 radio reset no encontrado')
s=s.replace(old,new,1)
# Do not swallow the intentional process-stack reset marker inside the generic
# elevated-helper exception handler.
old2="""                        except Exception as elev_ex:
                            progress('RECUPERACIÓN WINDOWS ELEVADA OMITIDA · '+type(elev_ex).__name__+': '+str(elev_ex))
"""
new2="""                        except Exception as elev_ex:
                            if str(elev_ex)=='RADIO_RESET_OK_RESTART_APP':
                                raise
                            progress('RECUPERACIÓN WINDOWS ELEVADA OMITIDA · '+type(elev_ex).__name__+': '+str(elev_ex))
"""
if old2 not in s: raise SystemExit('handler elevado V1.10 no encontrado')
s=s.replace(old2,new2,1)
s=s.replace('V1.11 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.11; 2º ACEPTAR UAC CUANDO WINDOWS LO PIDA; 3º REVISAR HORA/PASOS/PULSO; 4º COPIAR DIAGNÓSTICO. Corrige el helper elevado que V1.09 no llegó a ejecutar.','V1.11 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.11; 2º SI PIDE UAC, ACEPTAR Y REABRIR RELOJ LAB; 3º VOLVER A INSTALAR ESFERA SINCRONIZADA V1.11; 4º COPIAR DIAGNÓSTICO. Renueva WinRT/Bleak después del reset real del adaptador.')
s=s.replace('V1.11 · UAC HELPER CORREGIDO · V1.09 llegó a la recuperación elevada pero falló por NameError: Path. Se corrige ese defecto concreto y se mantiene intacta la ruta BLE: PnP normal → UAC si es denegado → reinicio del adaptador → discovery por firma → CCCD ATT real. No toca pairing, fábrica, firmware ni esfera.','V1.11 · BLE STACK FRESH START · V1.10 confirmó que el reinicio elevado del adaptador funciona. Tras ese reset ya no reutiliza el proceso WinRT/Bleak creado antes de apagar la radio: solicita reabrir Reloj Lab y la siguiente ejecución empieza con stack Bluetooth completamente nuevo. No toca pairing, fábrica, firmware ni esfera.')
p.write_text(s,encoding='utf-8')
print('overlay V1.11 aplicado')
