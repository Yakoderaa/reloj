from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

replacements = {
    'APP_VERSION="0.28.0"': 'APP_VERSION="0.29.0"',
    'root.title("Reloj Lab V0.28")': 'root.title("Reloj Lab V0.29")',
    'primary_test=ttk.Button(row,text="PRUEBA V0.28 - CONEXION LIMPIA + HUELLA OAD")\n        primary_test.pack(side="left",padx=4)': '''def copy_control_diagnostic():
            text=log.get("1.0","end-1c")
            if not text.strip():
                self.status.set("No hay diagnóstico para copiar todavía.")
                return
            try:
                w.clipboard_clear()
                w.clipboard_append(text)
                w.update_idletasks()
                self.status.set("Diagnóstico copiado al portapapeles.")
            except Exception as ex:
                messagebox.showerror("Copiar diagnóstico",repr(ex))
        primary_test=ttk.Button(row,text="PRUEBA V0.29 - RECUPERACION GATT POST-BOOT")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)''',
    'MAPA OTA V0.28: conexión serializada, seguimiento de reinicio y recuperación GATT.': 'PRUEBA V0.29: reinicio OAD + ventana extendida para recuperar GATT post-boot.',
    'emit("5/8 · Siguiendo advertising durante 45 s…")': 'emit("5/8 · Siguiendo advertising durante 60 s para separar boot temprano de GATT listo…")',
    'deadline=time.monotonic()+45': 'deadline=time.monotonic()+60',
    'for _ in range(18):': 'for _ in range(24):',
    'if stable>=2:\n                                emit("ADV ESTABLE · dos detecciones consecutivas"); break': 'if stable>=3:\n                                emit("ADV ESTABLE · tres detecciones consecutivas; espero 8 s extra antes de abrir GATT")\n                                await asyncio.sleep(8)\n                                break',
    'for attempt in range(1,9):': 'for attempt in range(1,13):',
    'await asyncio.sleep(5)': 'await asyncio.sleep(7)',
    'MAPA OTA V0.28 FINALIZADO · sin transferencia de firmware.': 'PRUEBA V0.29 FINALIZADA · reinicio confirmado; recuperación GATT medida sin transferir firmware.',
    'MAPA OTA V0.28 FINALIZADO"))': 'PRUEBA V0.29 FINALIZADA"))',
    'append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")': 'append("V0.29 LISTA · 1º PRUEBA V0.29; 2º COPIAR DIAGNÓSTICO. Pegame el texto completo al terminar.")',
}

for old, new in replacements.items():
    if old not in s:
        raise SystemExit(f"No se encontró patrón requerido: {old[:90]!r}")
    s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("build patch v0.29 aplicado")
