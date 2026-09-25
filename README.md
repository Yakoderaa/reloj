# Reloj Lab

Herramienta de ingeniería inversa para identificar el hardware y protocolo BLE del smartwatch.

## V0.1 Hardware Discovery
- Escaneo BLE.
- Datos de advertising y fabricante.
- Conexión GATT de solo lectura.
- Enumeración de servicios, características y descriptores.
- Lectura de características que anuncian propiedad `read`.
- Lecturas estándar Device Information cuando existen.
- Botón **DIAGNÓSTICO COMPLETO** y exportación JSON/TXT.

> V0.1 no escribe características, no actualiza firmware y no flashea el reloj.

## Windows
Descargá el artefacto **RelojLab-Windows** generado por GitHub Actions y ejecutá `RelojLab.exe`.
