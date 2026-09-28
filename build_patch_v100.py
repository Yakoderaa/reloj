from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
if 'APP_VERSION="0.99.0"' not in s:
    raise SystemExit("V1.00 requiere V0.99")
s=s.replace('APP_VERSION="0.99.0"','APP_VERSION="1.00.0"',1).replace('V0.99','V1.00')

# IMPORTANT: V1.00 deliberately removes the experimental connection gates added
# after V0.88.  The watch face was physically installed before those experiments.
# Restore the exact connect_retry implementation produced by V0.88 by extracting
# it from the V0.88 overlay source that is still in the repository build chain.
v88=Path("build_patch_v088.py").read_text(encoding="utf-8")
marker="new_conn='''"
a=v88.index(marker)+len(marker)
b=v88.index("'''",a)
v88_conn=v88[a:b]

start=s.index("    async def connect_retry(")
end=s.index("\n    def diagnose(",start)
s=s[:start]+v88_conn+s[end:]

# Keep the approved V0.86 visual and all V0.88 live-data work already present in
# the accumulated app: clock sync, CUSTOMIZE steps=8, heart=4 and install battery.
# Only the post-V0.88 connection experiments are rolled back here.
s=s.replace(
    'V1.00 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.00; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Valida enlace con B001 notify + DEVICE_INFO OEM real.',
    'V1.00 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.00; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Restaura la ruta probada V0.88 sin gates experimentales.'
)
s=s.replace(
    'V1.00 · OEM EXCHANGE GATE · corrige V0.98: elimina el payload inválido de 1 byte y restaura la secuencia histórica B001 notify → frame OEM DEVICE_INFO 0x02 de 20 bytes → respuesta B001.',
    'V1.00 · RUTA PROBADA V0.88 · vuelve exactamente al connect_retry anterior a V0.89 y conserva esfera aprobada + hora/pasos/pulso vivos + batería de instalación.'
)
p.write_text(s,encoding="utf-8")
print("overlay V1.00 aplicado: conexión V0.88 restaurada")
