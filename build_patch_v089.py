from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.88.0"' not in s:
    raise SystemExit("V0.89 requiere la base V0.88 aplicada")
s=s.replace('APP_VERSION="0.88.0"','APP_VERSION="0.89.0"',1)
s=s.replace('V0.88','V0.89')

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

        async def still_visible(timeout=3.5):
            try:
                w=await fresh_watch(timeout)
                if w is not None:
                    self.connection_state["watch_visible_during_failures"]=True
                    return w
            except Exception:
                pass
            return None

        async def connect_one(entry,label,use_cache=False,timeout_s=13):
            nonlocal last,attempt_no
            attempt_no+=1
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            client=None;keep=False
            try:
                kwargs={"timeout":10}
                if sys.platform=="win32":
                    kwargs["winrt"]={"use_cached_services":bool(use_cache)}
                target=entry.get("device") or entry.get("address")
                client=BleakClient(target,**kwargs)
                await asyncio.wait_for(client.connect(),timeout=timeout_s)
                if not client.is_connected:
                    raise RuntimeError("Windows no confirmó is_connected")
                services=list(client.services)
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
                progress(label+" · TIMEOUT GATT · el reloj se ve por BLE pero Windows no abrió la sesión.")
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

        # V0.89 never reuses the BLEDevice captured by an old GUI scan.
        # Every GATT attempt starts from a fresh advertisement.
        selected=self.selected or {}
        if selected and watch_score(selected)<=0:
            progress("AUTO-ID · selección previa descartada: no coincide con UtraWatch.")
        progress("AUTO-ID · buscando anuncio FRESCO del reloj…")

        rounds=[
            ("FRESH DEVICE · CACHE OFF",False,13),
            ("FRESH DEVICE · CACHE ON",True,13),
            ("FRESH DEVICE FINAL · CACHE OFF",False,16),
        ]
        for round_no,(label,use_cache,timeout_s) in enumerate(rounds,1):
            entry=await fresh_watch(6.0 if round_no<3 else 8.0)
            if entry is None:
                progress(f"AUTO-ID {round_no}/3 · no apareció UtraWatch; reintentando…")
                await asyncio.sleep(1.0)
                continue
            progress("AUTO-ID · "+entry["name"]+" · "+entry["address"]+
                     " · RSSI="+str(entry.get("rssi"))+" · score="+str(watch_score(entry)))
            client=await connect_one(entry,label,use_cache,timeout_s)
            if client is not None:
                return client,attempt_no

            visible=await still_visible(3.5)
            if visible is not None:
                progress("GATT OCUPADO · el reloj SIGUE anunciándose, pero rechaza/retiene la conexión GATT.")
            await asyncio.sleep(1.5)

        self.connection_state.update({"connected":False,"phase":"failed"})
        if self.connection_state.get("watch_visible_during_failures"):
            self.connection_state["hint"]="close_phone_app_or_disable_phone_bluetooth"
            msg=(
                "RELOJ VISIBLE PERO GATT OCUPADO. Cerrá UtraWatch en el celular y apagá "
                "temporalmente el Bluetooth del teléfono durante la instalación; luego volvé a "
                "pulsar INSTALAR ESFERA SINCRONIZADA. Si el celular ya está desconectado, apagá "
                "y encendé Bluetooth de Windows una vez."
            )
            progress(msg)
            raise RuntimeError(msg)
        raise RuntimeError(
            "No se pudo abrir GATT del UtraWatch desde un anuncio fresco. "
            "Encendé la pantalla del reloj, acercalo a la PC y reintentá."
        )
'''
s=s[:conn_start]+new_conn+s[conn_end:]

s=s.replace(
    'V0.89 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.89; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Hora, pasos y pulso pasan a datos vivos del reloj.',
    'V0.89 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.89; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Cada intento GATT parte de un anuncio BLE fresco.'
)
s=s.replace(
    'V0.89 · ESFERA SINCRONIZADA · conserva el diseño aprobado pero quita los valores de muestra: hora, pasos y pulso los dibuja el firmware con datos reales; batería se lee del reloj al instalar.',
    'V0.89 · ESFERA SINCRONIZADA + GATT FRESCO · conserva V0.88 y rehace la conexión desde cero; detecta si el reloj está visible pero ocupado por otra conexión.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.89 aplicado")
