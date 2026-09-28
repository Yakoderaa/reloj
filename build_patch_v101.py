from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
if 'APP_VERSION="0.88.0"' not in s:
    raise SystemExit("V1.01 debe aplicarse directamente sobre V0.88")
s=s.replace('APP_VERSION="0.88.0"','APP_VERSION="1.01.0"',1)
s=s.replace('V0.88','V1.01')
s=s.replace(
    'V1.01 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.01; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Hora, pasos y pulso pasan a datos vivos del reloj.',
    'V1.01 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.01; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Build limpio desde V0.88; sin PREWAKE ni gates posteriores.'
)
s=s.replace(
    'V1.01 · ESFERA SINCRONIZADA · conserva el diseño aprobado pero quita los valores de muestra: hora, pasos y pulso los dibuja el firmware con datos reales; batería se lee del reloj al instalar.',
    'V1.01 · BASE V0.88 LIMPIA · conserva exactamente la ruta que ya instalaba CUSTOMIZE y los bindings vivos de V0.88; elimina por construcción todos los experimentos de conexión V0.89–V1.00.'
)
p.write_text(s,encoding="utf-8")
print("V1.01 aplicado directamente sobre V0.88")
