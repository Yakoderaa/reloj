from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
if 'APP_VERSION="1.01.0"' not in s:
    raise SystemExit("V1.02 requiere V1.01")
s=s.replace('APP_VERSION="1.01.0"','APP_VERSION="1.02.0"',1).replace('V1.01','V1.02')

# V1.01 proved the later V0.87 auto-ID route itself now spends ~145 s timing out.
# The face-transfer success originated earlier: V0.83 used the simple clean
# advertising -> fresh BLEDevice -> BleakClient loop. Restore that exact strategy,
# while keeping the approved V0.86 raster and V0.88 live-data work above it.
start=s.index("    async def connect_retry(")
end=s.index("\n    def diagnose(",start)
conn='''    async def connect_retry(self,attempts=4,progress=None):
        progress=progress or (lambda message:None)
        selected=dict(self.selected or {})
        address=selected.get("address") or getattr(selected.get("device"),"address",None)
        if not address:raise RuntimeError("Seleccioná un reloj en Buscar relojes.")
        last=None
        self.connection_state={"connected":False,"attempts":0,"phase":"v083_clean","strategies":[]}
        for i in range(max(1,attempts)):
            client=None;connected=False
            try:
                self.connection_state["attempts"]=i+1
                progress(f"CONEXIÓN LIMPIA V0.83 {i+1}/{attempts} · esperando anuncio fresco...")
                target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=8),timeout=10)
                if target is None:raise RuntimeError("reloj no visible en advertising")
                progress("ANUNCIO FRESCO · creando sesión GATT nueva...")
                client=BleakClient(target,timeout=18)
                await asyncio.wait_for(client.connect(),timeout=22)
                if not client.is_connected:raise RuntimeError("Windows no confirmó is_connected")
                _=client.services
                connected=True
                if self.selected is not None:self.selected["device"]=target
                self.connection_state.update({"connected":True,"phase":"gatt_open","strategy":"V0.83 fresh advertising","attempts":i+1})
                progress("GATT ABIERTO V0.83 · continúa directamente con B001/B002 OEM")
                return client,i+1
            except asyncio.CancelledError:raise
            except Exception as ex:
                last=ex;progress(f"INTENTO {i+1} FALLÓ · {type(ex).__name__}: {ex}")
            finally:
                if client is not None and not connected:
                    try:await asyncio.wait_for(client.disconnect(),timeout=3)
                    except Exception:pass
            if i+1<attempts:
                cooldown=6+4*i
                progress(f"LIBERANDO WINRT {cooldown}s antes del siguiente intento...")
                await asyncio.sleep(cooldown)
        self.connection_state.update({"connected":False,"phase":"failed"})
        raise RuntimeError("GATT NO DISPONIBLE tras intentos limpios V0.83: "+str(last))
'''
s=s[:start]+conn+s[end:]

s=s.replace(
 'V1.02 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.02; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Build limpio desde V0.88; sin PREWAKE ni gates posteriores.',
 'V1.02 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.02; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Conexión original V0.83: anuncio fresco → sesión GATT limpia.'
)
s=s.replace(
 'V1.02 · BASE V0.88 LIMPIA · conserva exactamente la ruta que ya instalaba CUSTOMIZE y los bindings vivos de V0.88; elimina por construcción todos los experimentos de conexión V0.89–V1.00.',
 'V1.02 · CONEXIÓN ORIGINAL V0.83 · elimina también el auto-ID V0.87 que V1.01 demostró problemático; conserva esfera aprobada V0.86 y bindings vivos V0.88.'
)
p.write_text(s,encoding="utf-8")
print("overlay V1.02 aplicado: connect_retry original V0.83 restaurado")
