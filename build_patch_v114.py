from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.13.0"' not in s:
    raise SystemExit('V1.14 requiere V1.13')
# V1.13 inserted the marker block with the same indentation as the install coroutine.
# Replace by stable line content instead of an indentation-sensitive multiline literal.
lines=s.splitlines(keepends=True)
start=None
end=None
for i,line in enumerate(lines):
    if "marker=Path.home()/'AppData'/'Local'/'RelojLab'/'radio-reset-v113.flag'" in line:
        # The first occurrence is the marker WRITE after radio reset; the second is the marker READ at install start.
        if start is None:
            start=-1
        else:
            start=i-1 if i>0 and lines[i-1].lstrip().startswith('try:') else i
            break
if start is None or start < 0:
    raise SystemExit('bloque post-reset V1.13 no encontrado')
base_indent=lines[start][:len(lines[start])-len(lines[start].lstrip())]
for j in range(start+1,min(len(lines),start+12)):
    if lines[j].startswith(base_indent+'except Exception as marker_ex:'):
        end=j+2
        break
if end is None:
    raise SystemExit('fin bloque post-reset V1.13 no encontrado')
new=(base_indent+'try:\n'+
     base_indent+"    marker=Path.home()/'AppData'/'Local'/'RelojLab'/'radio-reset-v113.flag'\n"+
     base_indent+'    if marker.exists():\n'+
     base_indent+'        marker.unlink(missing_ok=True)\n'+
     base_indent+'        await asyncio.sleep(12)\n'+
     base_indent+'except Exception:\n'+
     base_indent+'    pass\n')
lines[start:end]=[new]
s=''.join(lines)
s=s.replace('APP_VERSION="1.13.0"','APP_VERSION="1.14.0"',1)
s=s.replace('V1.13 LISTA','V1.14 LISTA').replace('V1.13 · POST-RESET PERSISTENTE','V1.14 · POST-RESET SEGURO')
s=s.replace('INSTALAR ESFERA SINCRONIZADA V1.13','INSTALAR ESFERA SINCRONIZADA V1.14')
p.write_text(s,encoding='utf-8')
print('overlay V1.14 aplicado: eliminado NameError progress del arranque post-reset')
