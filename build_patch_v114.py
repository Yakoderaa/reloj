from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.13.0"' not in s:
    raise SystemExit('V1.14 requiere V1.13')
old="""try:
    marker=Path.home()/'AppData'/'Local'/'RelojLab'/'radio-reset-v113.flag'
    if marker.exists():
        marker.unlink(missing_ok=True)
        progress('POST-RESET DETECTADO · proceso WinRT/Bleak nuevo; esperando 12s a que Windows estabilice GATT antes del discovery...')
        await asyncio.sleep(12)
except Exception as marker_ex:
    progress('POST-RESET MARKER OMITIDO · '+type(marker_ex).__name__+': '+str(marker_ex))
"""
if old not in s:
    raise SystemExit('bloque defectuoso V1.13 no encontrado')
new="""try:
    marker=Path.home()/'AppData'/'Local'/'RelojLab'/'radio-reset-v113.flag'
    if marker.exists():
        marker.unlink(missing_ok=True)
        await asyncio.sleep(12)
except Exception:
    pass
"""
s=s.replace(old,new,1)
s=s.replace('APP_VERSION="1.13.0"','APP_VERSION="1.14.0"',1)
s=s.replace('V1.13 LISTA','V1.14 LISTA').replace('V1.13 · POST-RESET PERSISTENTE','V1.14 · POST-RESET SEGURO')
s=s.replace('INSTALAR ESFERA SINCRONIZADA V1.13','INSTALAR ESFERA SINCRONIZADA V1.14')
p.write_text(s,encoding='utf-8')
print('overlay V1.14 aplicado: eliminado NameError progress del arranque post-reset')
