from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.14.0"' not in s:
    raise SystemExit('V1.15 requiere V1.14')
# Path is imported only by build overlays, not necessarily by the generated app.
# The runtime marker write/read must not depend on pathlib.Path.
old_write="marker=Path.home()/'AppData'/'Local'/'RelojLab'/'radio-reset-v113.flag'"
new_write="marker=__import__('pathlib').Path.home()/'AppData'/'Local'/'RelojLab'/'radio-reset-v113.flag'"
count=s.count(old_write)
if count < 2:
    raise SystemExit(f'V1.15 esperaba al menos 2 usos runtime de Path; encontró {count}')
s=s.replace(old_write,new_write)
s=s.replace('APP_VERSION="1.14.0"','APP_VERSION="1.15.0"',1)
s=s.replace('V1.14 LISTA','V1.15 LISTA')
s=s.replace('V1.14 · POST-RESET SEGURO','V1.15 · POST-RESET PATH SEGURO')
s=s.replace('INSTALAR ESFERA SINCRONIZADA V1.14','INSTALAR ESFERA SINCRONIZADA V1.15')
p.write_text(s,encoding='utf-8')
print('overlay V1.15 aplicado: pathlib disponible en runtime para marcador post-reset')
