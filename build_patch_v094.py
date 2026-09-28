from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.93.0"' not in s:
    raise SystemExit("V0.94 requiere la base V0.93 aplicada")
s=s.replace('APP_VERSION="0.93.0"','APP_VERSION="0.94.0"',1)
s=s.replace('V0.93','V0.94')

conn_start=s.index("    async def connect_retry(")
conn_end=s.index("\n    def diagnose(",conn_start)
new_conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={
            "connected":False,"attempts":0,"phase":"proven_cache_on",
            "strategies":[],"used_synthetic_bledevice":False
        }
        last=None
        attempt_no=0

        def watch_score(x):
            services={str(v).lower() for v in (x.get("service_uuids") or [])}
            service_data={str(k).lower():v for k,v in (x.get("service_data") or {}).items()}
            name=(x.get("name") or "").strip().lower()
            manufacturer=x.get("manufacturer_data") or {}
            score=0
            if "0000e91a-0000-1000-8000-00805f9b34fb" in services:score+=120
            if "00003802-0000-1000-8000-00805f9b34fb" in services:score+=110
            if any("3802" in k for k in service_data):score+=110
            if name=="apple watch ultra":score+=60
            if str(manufacturer.get("255","")).lower()=="00a6":score+=40
            return score

        def adv_row(d,a):
            return {
                "device":d,
                "name":a.local_name or d.name or "(sin nombre)",
                "address":d.address,
                "rssi":a.rssi,
                "service_uuids":list(a.service_uuids or []),
                "manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},
                "service_data":{str(k):v.hex() for k,v in a.service_data.items()},
                "tx_power":a.tx_power,
            }

        async def fresh_watch(timeout=8.0):
            found=await BleakScanner.discover(timeout=timeout,return_adv=True)
            rows=[adv_row(d,a) for _,(d,a) in found.items()]
            rows=[x for x in rows if watch_score(x)>0]
            rows.sort(key=lambda x:(watch_score(x),x["rssi"] if x["rssi"] is not None else -999),reverse=True)
            if not rows:return None
            best=rows[0]
            self.selected=best
            return best

        async def connect_cached(entry,label,target,timeout_s=28):
            nonlocal last,attempt_no
            attempt_no+=1
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            client=None;keep=False
            try:
                kwargs={"timeout":22}
                if sys.platform=="win32":
                    kwargs["winrt"]={"use_cached_services":True}
                client=BleakClient(target,**kwargs)
                await asyncio.wait_for(client.connect(),timeout=timeout_s)
                if not client.is_connected:
                    raise RuntimeError("Windows no confirmó is_connected")
                services=list(client.services)
                if not services:
                    raise RuntimeError("GATT abrió sin servicios")
                char_ids=set()
                for svc in services:
                    for ch in svc.characteristics:
                        char_ids.add(str(ch.uuid).lower())
                b001="0000b001-0000-1000-8000-00805f9b34fb"
                b002="0000b002-0000-1000-8000-00805f9b34fb"
                if b001 not in char_ids or b002 not in char_ids:
                    raise RuntimeError("GATT cacheado abrió árbol incompleto: faltan B001/B002")
                keep=True
                self.selected=entry
                self.connection_state.update({
                    "connected":True,"phase":"gatt_ready","strategy":label,
                    "address":entry.get("address"),"name":entry.get("name"),
                    "cache":True
                })
                progress(label+f" · UTRAWATCH GATT OK · servicios={len(services)} · MTU={getattr(client,'mtu_size','?')}")
                return client
            except asyncio.TimeoutError as ex:
                last=ex
                progress(label+" · TIMEOUT GATT")
                return None
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                last=ex
                progress(label+" · FALLÓ · "+type(ex).__name__+": "+str(ex))
                return None
            finally:
                if client is not None and not keep:
                    try:
                        if client.is_connected:
                            await asyncio.wait_for(client.disconnect(),timeout=5)
                    except Exception:
                        pass

        remembered=self.selected or {}
        remembered_ok=bool(remembered.get("address") and watch_score(remembered)>0)

        # Proven route first. V0.91 and V0.92 both opened the real watch with
        # DIRECT WINRT + CACHE ON. Do not poison the Windows BLE stack with the
        # consistently failing CACHE OFF/RANDOM routes before trying it.
        if sys.platform=="win32" and remembered_ok:
            from bleak.backends.device import BLEDevice
            addr=remembered["address"]
            name=remembered.get("name") or "Apple Watch Ultra"
            synthetic=BLEDevice(addr,name,None)
            self.connection_state["used_synthetic_bledevice"]=True

            for direct_try in range(1,3):
                if direct_try==1:
                    progress("RUTA PROBADA · DIRECT WINRT + CACHE ON primero; sin CACHE OFF/RANDOM previos.")
                    await asyncio.sleep(2.0)
                else:
                    progress("RUTA PROBADA · segundo intento limpio tras reposo de la sesión Windows…")
                    await asyncio.sleep(5.0)
                client=await connect_cached(
                    remembered,
                    "DIRECT WINRT + CACHE ON · intento "+str(direct_try),
                    synthetic,
                    30
                )
                if client is not None:
                    return client,attempt_no

        # If direct cached connect did not open, get exactly one fresh BLEDevice and
        # try the same known-good cached route. No random-address guesses.
        progress("RECUPERACIÓN · buscando un único anuncio fresco UtraWatch…")
        entry=await fresh_watch(10.0)
        if entry is not None:
            progress("AUTO-ID · "+entry["name"]+" · "+entry["address"]+
                     " · RSSI="+str(entry.get("rssi"))+" · score="+str(watch_score(entry)))
            device=entry.get("device")
            if device is not None:
                await asyncio.sleep(2.0)
                client=await connect_cached(entry,"FRESH DEVICE + CACHE ON",device,32)
                if client is not None:
                    return client,attempt_no

                # One final cached direct attempt using the freshly confirmed address.
                if sys.platform=="win32":
                    from bleak.backends.device import BLEDevice
                    refreshed=BLEDevice(entry["address"],entry.get("name") or "Apple Watch Ultra",None)
                    await asyncio.sleep(5.0)
                    client=await connect_cached(
                        entry,"FRESH ADDRESS DIRECT WINRT + CACHE ON",refreshed,32
                    )
                    if client is not None:
                        return client,attempt_no
        else:
            progress("RECUPERACIÓN · el reloj no anunció; se mantiene la identidad conocida.")

        self.connection_state.update({"connected":False,"phase":"failed"})
        msg=(
            "La ruta probada DIRECT WINRT + CACHE ON no abrió GATT en esta sesión. "
            "V0.94 evitó CACHE OFF y RANDOM para no degradar el estado Bluetooth de Windows."
        )
        progress(msg)
        raise RuntimeError(msg)
'''
s=s[:conn_start]+new_conn+s[conn_end:]

s=s.replace(
    'V0.94 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.94; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Fuerza ATT real por B002 antes de habilitar B001.',
    'V0.94 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.94; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Prioriza la única ruta GATT que ya abrió el reloj: DIRECT WINRT + CACHE ON.'
)
s=s.replace(
    'V0.94 · ATT PREWAKE + CCCD DIRECTO · conserva la esfera sincronizada; primero valida el enlace físico con B002 WRITE RESPONSE y luego habilita B001 por helper o descriptor 0x2902.',
    'V0.94 · RUTA GATT PROBADA · elimina CACHE OFF/RANDOM antes de conectar; abre primero DIRECT WINRT + CACHE ON y conserva PREWAKE B002 + CCCD directo de V0.93.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.94 aplicado")
