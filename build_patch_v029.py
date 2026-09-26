from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.47.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.47")', 1)

old_button = '''primary_test=ttk.Button(row,text="PRUEBA V0.28 - CONEXION LIMPIA + HUELLA OAD")
        primary_test.pack(side="left",padx=4)'''
new_button = '''def copy_control_diagnostic():
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
        primary_test=ttk.Button(row,text="INSPECCIONAR SERVICIOS V0.47")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("INSPECCIÓN V0.47 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.47 · dos inventarios GATT de lectura, sin comandos ni suscripciones.")
            async def work():
                snapshots=[]
                def emit(line):
                    self.ui_queue.put(lambda x=line:append(x))
                try:
                    for index in range(2):
                        emit(f"INSPECCIÓN {index+1}/2")
                        snapshot=await self.inspect_gatt_snapshot(emit)
                        snapshots.append(snapshot)
                        if index==0: await asyncio.sleep(3)
                    self.report=self.base_report()
                    self.report["gatt_snapshots"]=snapshots
                    self.report["errors"]=[error for snap in snapshots for error in snap["errors"]]
                    emit("RESUMEN · "+str([{"present":x.get("present"),"errors":x["errors"]} for x in snapshots]))
                    return snapshots
                finally:
                    emit("INSPECCIÓN TERMINADA · sin escrituras de características ni firmware.")
            def done(result,error):
                if error:
                    append("INSPECCIÓN V0.47 INTERRUMPIDA · "+repr(error))
                    return
                if any(snap["errors"] for snap in result):
                    append("INSPECCIÓN V0.47 COMPLETADA CON ERRORES · copiá el diagnóstico.")
                else:
                    append("INSPECCIÓN V0.47 COMPLETADA · copiá el diagnóstico.")
            self.run_async(work(),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.47 LISTA · 1º INSPECCIONAR SERVICIOS; 2º COPIAR DIAGNÓSTICO. Registra los servicios disponibles y si B001 está presente.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

s=s.replace("    def open_control(self):", '    async def inspect_gatt_snapshot(self,emit):\n        address=(self.selected or {}).get("address")\n        if not address: raise RuntimeError("Seleccioná el reloj primero.")\n        client=None\n        snapshot={"services":[],"errors":[],"connected":False}\n        try:\n            target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=8),timeout=10)\n            if target is None: raise RuntimeError("El reloj seleccionado no está visible.")\n            client=BleakClient(target,timeout=15,winrt={"use_cached_services":False})\n            await asyncio.wait_for(client.connect(),timeout=18)\n            if not client.is_connected: raise RuntimeError("GATT no conectado")\n            snapshot["connected"]=True\n            present=set()\n            for svc in client.services:\n                entry={"uuid":svc.uuid,"characteristics":[]}\n                emit("SERVICIO "+svc.uuid)\n                for ch in svc.characteristics:\n                    present.add(ch.uuid.lower())\n                    row={"uuid":ch.uuid,"handle":ch.handle,"properties":list(ch.properties)}\n                    entry["characteristics"].append(row)\n                    emit("  CARACTERÍSTICA "+str(row))\n                snapshot["services"].append(entry)\n            expected={"B001":"0000b001-0000-1000-8000-00805f9b34fb","B002":"0000b002-0000-1000-8000-00805f9b34fb","FFC1":"f000ffc1-0451-4000-b000-000000000000","FFC2":"f000ffc2-0451-4000-b000-000000000000"}\n            snapshot["present"]={name:uuid in present for name,uuid in expected.items()}\n            emit("PRESENCIA "+str(snapshot["present"]))\n            if not snapshot["present"]["B001"]:\n                emit("B001 AUSENTE en esta enumeración. Causa pendiente; no confirma modo OTA.")\n        except asyncio.CancelledError: raise\n        except Exception as ex:\n            snapshot["errors"].append(type(ex).__name__+": "+str(ex))\n            emit("ERROR DE INSPECCIÓN · "+snapshot["errors"][-1])\n        finally:\n            if client is not None:\n                try: await asyncio.wait_for(client.disconnect(),timeout=4)\n                except Exception as ex:\n                    snapshot["errors"].append("Cierre: "+repr(ex))\n                    emit("ERROR DE CIERRE · "+repr(ex))\n        return snapshot\n' + "\n    def open_control(self):",1)
p.write_text(s,encoding="utf-8")
print("build patch v0.47 aplicado")
