from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.11.0"' not in s: raise SystemExit('V1.12 requiere V1.11')
s=s.replace('APP_VERSION="1.11.0"','APP_VERSION="1.12.0"',1).replace('V1.11','V1.12')
old="""                                await asyncio.sleep(2)
                                raise RuntimeError('RADIO_RESET_OK_RESTART_APP')
"""
new="""                                await asyncio.sleep(2)
                                raise SystemExit(0)
"""
if old not in s: raise SystemExit('reinicio V1.11 no encontrado')
s=s.replace(old,new,1)
old2="""                        except Exception as elev_ex:
                            if str(elev_ex)=='RADIO_RESET_OK_RESTART_APP':
                                raise
                            progress('RECUPERACIÓN WINDOWS ELEVADA OMITIDA · '+type(elev_ex).__name__+': '+str(elev_ex))
"""
new2="""                        except Exception as elev_ex:
                            progress('RECUPERACIÓN WINDOWS ELEVADA OMITIDA · '+type(elev_ex).__name__+': '+str(elev_ex))
"""
if old2 not in s: raise SystemExit('handler V1.11 no encontrado')
s=s.replace(old2,new2,1)
s=s.replace('V1.12 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.12; 2º SI PIDE UAC, ACEPTAR Y REABRIR RELOJ LAB; 3º VOLVER A INSTALAR ESFERA SINCRONIZADA V1.12; 4º COPIAR DIAGNÓSTICO. Renueva WinRT/Bleak después del reset real del adaptador.','V1.12 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.12; 2º SI PIDE UAC, ACEPTAR; 3º CUANDO RELOJ LAB SE CIERRE, ABRIRLO DE NUEVO; 4º INSTALAR ESFERA SINCRONIZADA V1.12; 5º COPIAR DIAGNÓSTICO. Cierre limpio tras reset Bluetooth.')
s=s.replace('V1.12 · BLE STACK FRESH START · V1.10 confirmó que el reinicio elevado del adaptador funciona. Tras ese reset ya no reutiliza el proceso WinRT/Bleak creado antes de apagar la radio: solicita reabrir Reloj Lab y la siguiente ejecución empieza con stack Bluetooth completamente nuevo. No toca pairing, fábrica, firmware ni esfera.','V1.12 · CIERRE LIMPIO POST-RESET · V1.11 confirmó el reset elevado, pero su RuntimeError fue capturado por un handler exterior y el proceso viejo siguió intentando BLE. Ahora usa SystemExit, que no es capturado por los handlers Exception de recuperación; al reabrir Reloj Lab WinRT/Bleak nace desde cero. No toca pairing, fábrica, firmware ni esfera.')
p.write_text(s,encoding='utf-8')
print('overlay V1.12 aplicado')
