from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

replacements = {
    'APP_VERSION="0.28.0"': 'APP_VERSION="0.30.0"',
    'root.title("Reloj Lab V0.28")': 'root.title("Reloj Lab V0.30")',
    'primary_test=ttk.Button(row,text="PRUEBA V0.28 - CONEXION LIMPIA + HUELLA OAD")\n        primary_test.pack(side="left",padx=4)': '''def copy_control_diagnostic():
            text=log.get("1.0","end-1c")
            if not text.strip():
                self.status.set("No hay diagnóstico para copiar todavía.")
                return
            w.clipboard_clear(); w.clipboard_append(text); w.update_idletasks()
            self.status.set("Diagnóstico copiado al portapapeles.")
        primary_test=ttk.Button(row,text="PRUEBA V0.30 - RECUPERAR GATT LIMPIO")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)''',
    'MAPA OTA V0.28: conexión serializada, seguimiento de reinicio y recuperación GATT.': 'PRUEBA V0.30: el reloj anuncia pero Windows agota GATT; pruebo rutas de conexión frescas sin reiniciarlo.',
    'c,n=await asyncio.wait_for(self.connect_retry(4,emit),timeout=180)': '''# V0.30: no disparamos otro OAD hasta recuperar primero el GATT normal.
                    target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=12),timeout=15)
                    if target is None: raise RuntimeError("reloj no visible en advertising")
                    strategies=[
                        ("DEVICE + CACHE OFF", target, {"winrt":{"use_cached_services":False}}),
                        ("ADDRESS + CACHE OFF", address, {"winrt":{"use_cached_services":False}}),
                        ("DEVICE NORMAL", target, {}),
                        ("ADDRESS NORMAL", address, {}),
                    ]
                    last=None; c=None; n=0
                    for label,dest,kwargs in strategies:
                        n+=1; emit(f"RUTA GATT {n}/4 · {label}")
                        candidate=None
                        try:
                            candidate=BleakClient(dest,timeout=30,**kwargs)
                            await asyncio.wait_for(candidate.connect(),timeout=35)
                            if not candidate.is_connected: raise RuntimeError("is_connected=False")
                            c=candidate; emit("GATT RECUPERADO · "+label); break
                        except Exception as ex:
                            last=ex; emit("RUTA FALLÓ · "+label+" · "+type(ex).__name__+": "+str(ex))
                            if candidate:
                                try: await asyncio.wait_for(candidate.disconnect(),timeout=4)
                                except Exception: pass
                            await asyncio.sleep(4)
                    if c is None: raise RuntimeError("NINGUNA RUTA GATT ABRIÓ: "+repr(last))''',
    'emit(f"GATT PREVIO OK · estrategia {n} · servicios={len(before)} · MTU={getattr(c,\'mtu_size\',\'?\')}")': 'emit(f"GATT PREVIO RECUPERADO · ruta={n} · servicios={len(before)} · MTU={getattr(c,\'mtu_size\',\'?\')}")',
    'emit("3/8 · TX ÚNICO FFC1=01")': 'emit("3/8 · GATT YA RECUPERADO. En V0.30 NO envío FFC1=01 otra vez.")',
    '''try:
                        await asyncio.wait_for(c.write_gatt_char("f000ffc1-0451-4000-b000-000000000000",b"\\x01",response=False),timeout=4)
                        emit("FFC1=01 enviado")
                    except Exception as ex:emit("FFC1 write terminó con "+repr(ex)+"; sigo el reinicio")''': 'emit("FFC1 omitido deliberadamente para no encadenar otro reinicio antes de diagnosticar el GATT.")',
    'MAPA OTA V0.28 FINALIZADO · sin transferencia de firmware.': 'PRUEBA V0.30 FINALIZADA · rutas GATT registradas; sin transferencia de firmware.',
    'MAPA OTA V0.28 FINALIZADO"))': 'PRUEBA V0.30 FINALIZADA"))',
    'append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")': 'append("V0.30 LISTA · 1º PRUEBA V0.30; 2º COPIAR DIAGNÓSTICO. Esta prueba intenta recuperar GATT antes de volver a reiniciar el reloj.")',
}
for old,new in replacements.items():
    if old not in s: raise SystemExit(f"No se encontró patrón requerido: {old[:100]!r}")
    s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8")
print("build patch v0.30 aplicado")
