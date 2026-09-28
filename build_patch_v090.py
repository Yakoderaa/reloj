from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.89.0"' not in s:
    raise SystemExit("V0.90 requiere la base V0.89 aplicada")
s=s.replace('APP_VERSION="0.89.0"','APP_VERSION="0.90.0"',1)
s=s.replace('V0.89','V0.90')

conn_start=s.index("    async def connect_retry(")
conn_end=s.index("\n    def diagnose(",conn_start)
new_conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={
            "connected":False,"attempts":0,"phase":"fresh_scan",
            "strategies":[],"watch_visible_during_failures":False
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

        async def fresh_watch(timeout=6.0):
            found=await BleakScanner.discover(timeout=timeout,return_adv=True)
            rows=[adv_row(d,a) for _,(d,a) in found.items()]
            rows=[x for x in rows if watch_score(x)>0]
            rows.sort(key=lambda x:(watch_score(x),x["rssi"] if x["rssi"] is not None else -999),reverse=True)
            if not rows:return None
            best=rows[0]
            self.selected=best
            return best

        async def connect_target(entry,label,target,use_cache=False,timeout_s=22):
            nonlocal last,attempt_no
            attempt_no+=1
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            client=None;keep=False
            try:
                kwargs={"timeout":16}
                if sys.platform=="win32":
                    kwargs["winrt"]={"use_cached_services":bool(use_cache)}
                client=BleakClient(target,**kwargs)
                await asyncio.wait_for(client.connect(),timeout=timeout_s)
                if not client.is_connected:
                    raise RuntimeError("Windows no confirmó is_connected")
                services=list(client.services)
                if not services:
                    raise RuntimeError("GATT abierto sin servicios")
                char_ids=set()
                for svc in services:
                    for ch in svc.characteristics:
                        char_ids.add(str(ch.uuid).lower())
                b001="0000b001-0000-1000-8000-00805f9b34fb"
                b002="0000b002-0000-1000-8000-00805f9b34fb"
                if b001 not in char_ids or b002 not in char_ids:
                    raise RuntimeError("GATT abierto pero no corresponde al UtraWatch B001/B002")
                keep=True
                self.selected=entry
                self.connection_state.update({
                    "connected":True,"phase":"gatt_ready","strategy":label,
                    "address":entry.get("address"),"name":entry.get("name")
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
                            await asyncio.wait_for(client.disconnect(),timeout=4)
                    except Exception:
                        pass

        progress("AUTO-ID · esperando anuncio fresco UtraWatch…")
        for scan_round in range(1,4):
            entry=await fresh_watch(7.0 if scan_round<3 else 10.0)
            if entry is None:
                progress(f"AUTO-ID {scan_round}/3 · no apareció UtraWatch.")
                await asyncio.sleep(1.0)
                continue

            self.connection_state["watch_visible_during_failures"]=True
            progress("AUTO-ID · "+entry["name"]+" · "+entry["address"]+
                     " · RSSI="+str(entry.get("rssi"))+" · score="+str(watch_score(entry)))

            # IMPORTANT: every fresh advertisement gets the full strategy ladder.
            # V0.89 incorrectly tied CACHE OFF to scan #1 and CACHE ON to scan #2,
            # so if the watch only appeared on scan #2 the known-good OFF path
            # was never attempted.
            strategies=[]
            device=entry.get("device")
            address=entry.get("address")
            if device is not None:
                strategies.append(("FRESH DEVICE + CACHE OFF",device,False))
            if address:
                strategies.append(("FRESH ADDRESS + CACHE OFF",address,False))
            if device is not None:
                strategies.append(("FRESH DEVICE + CACHE ON",device,True))
            if address:
                strategies.append(("FRESH ADDRESS + CACHE ON",address,True))

            for label,target,use_cache in strategies:
                client=await connect_target(entry,label,target,use_cache,22)
                if client is not None:
                    return client,attempt_no
                await asyncio.sleep(1.2)

            progress("RONDA "+str(scan_round)+" · el reloj apareció, pero ninguna ruta GATT abrió; se buscará un anuncio nuevo.")
            await asyncio.sleep(2.0)

        self.connection_state.update({"connected":False,"phase":"failed"})
        if self.connection_state.get("watch_visible_during_failures"):
            self.connection_state["hint"]="close_phone_app_or_disable_phone_bluetooth"
            msg=(
                "RELOJ VISIBLE PERO GATT NO ABRE. La PC encontró correctamente el UtraWatch, "
                "pero Windows no pudo tomar su conexión. Durante la instalación cerrá UtraWatch "
                "en el celular y apagá temporalmente el Bluetooth del teléfono. Si ya está apagado, "
                "apagá/encendé Bluetooth de Windows y reintentá."
            )
            progress(msg)
            raise RuntimeError(msg)
        raise RuntimeError(
            "El UtraWatch no apareció en tres escaneos frescos. Encendé la pantalla del reloj "
            "y acercalo a la PC."
        )
'''
s=s[:conn_start]+new_conn+s[conn_end:]

s=s.replace(
    'V0.90 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.90; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Cada intento GATT parte de un anuncio BLE fresco.',
    'V0.90 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.90; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Cada anuncio fresco prueba CACHE OFF antes que CACHE ON.'
)
s=s.replace(
    'V0.90 · ESFERA SINCRONIZADA + GATT FRESCO · conserva V0.88 y rehace la conexión desde cero; detecta si el reloj está visible pero ocupado por otra conexión.',
    'V0.90 · GATT SECUENCIA CORREGIDA · conserva V0.88; cada vez que aparece el reloj prueba DEVICE/OFF → ADDRESS/OFF → DEVICE/ON → ADDRESS/ON antes de descartarlo.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.90 aplicado")
