from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.90.0"' not in s:
    raise SystemExit("V0.91 requiere la base V0.90 aplicada")
s=s.replace('APP_VERSION="0.90.0"','APP_VERSION="0.91.0"',1)
s=s.replace('V0.90','V0.91')

conn_start=s.index("    async def connect_retry(")
conn_end=s.index("\n    def diagnose(",conn_start)
new_conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={
            "connected":False,"attempts":0,"phase":"direct_winrt",
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

        async def fresh_watch(timeout=7.0):
            found=await BleakScanner.discover(timeout=timeout,return_adv=True)
            rows=[adv_row(d,a) for _,(d,a) in found.items()]
            rows=[x for x in rows if watch_score(x)>0]
            rows.sort(key=lambda x:(watch_score(x),x["rssi"] if x["rssi"] is not None else -999),reverse=True)
            if not rows:return None
            best=rows[0]
            self.selected=best
            return best

        async def connect_target(entry,label,target,use_cache=False,timeout_s=24,address_type=None,pair=False):
            nonlocal last,attempt_no
            attempt_no+=1
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append({
                "label":label,"cache":bool(use_cache),
                "address_type":address_type,"pair":bool(pair)
            })
            progress(f"CONEXIÓN {attempt_no} · {label}")
            client=None;keep=False
            try:
                kwargs={"timeout":18,"pair":bool(pair)}
                if sys.platform=="win32":
                    winrt={"use_cached_services":bool(use_cache)}
                    if address_type in ("public","random"):
                        winrt["address_type"]=address_type
                    kwargs["winrt"]=winrt
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
                    "address":entry.get("address"),"name":entry.get("name"),
                    "address_type":address_type,"paired_during_connect":bool(pair)
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

        remembered=self.selected or {}
        remembered_ok=bool(remembered.get("address") and watch_score(remembered)>0)

        # Windows-specific recovery: Bleak normally forces a scan when a plain
        # MAC string is used. A BLEDevice object bypasses that implicit scan.
        # The WinRT backend only needs the address from BLEDevice to call
        # BluetoothLEDevice.from_bluetooth_address_async(), so this can recover
        # a known watch even while it is temporarily not advertising.
        if sys.platform=="win32" and remembered_ok:
            from bleak.backends.device import BLEDevice
            addr=remembered["address"]
            name=remembered.get("name") or "Apple Watch Ultra"
            synthetic=BLEDevice(addr,name,None)
            self.connection_state["used_synthetic_bledevice"]=True
            progress("DIRECT WINRT · usando identidad conocida "+name+" · "+addr+" sin esperar un anuncio nuevo.")

            direct_strategies=[
                ("DIRECT WINRT · CACHE OFF",False,None,False,26),
                ("DIRECT WINRT · RANDOM + CACHE OFF",False,"random",False,26),
                ("DIRECT WINRT · CACHE ON",True,None,False,22),
                ("DIRECT WINRT · RANDOM + CACHE ON",True,"random",False,22),
                ("DIRECT WINRT · PAIR + RANDOM + CACHE OFF",False,"random",True,35),
            ]
            for label,use_cache,address_type,pair,timeout_s in direct_strategies:
                client=await connect_target(
                    remembered,label,synthetic,use_cache,timeout_s,address_type,pair
                )
                if client is not None:
                    return client,attempt_no
                await asyncio.sleep(1.0)

            progress("DIRECT WINRT · no abrió GATT; se intentará recuperar además por anuncio fresco.")

        # Normal scan fallback. If an advertisement returns, try the full known-good
        # ladder for that exact BLEDevice.
        for scan_round in range(1,4):
            progress("AUTO-ID · búsqueda fresca "+str(scan_round)+"/3…")
            entry=await fresh_watch(7.0 if scan_round<3 else 10.0)
            if entry is None:
                progress("AUTO-ID · no apareció UtraWatch en esta ronda.")
                continue
            progress("AUTO-ID · "+entry["name"]+" · "+entry["address"]+
                     " · RSSI="+str(entry.get("rssi"))+" · score="+str(watch_score(entry)))
            device=entry.get("device")
            if device is None:
                continue
            scan_strategies=[
                ("FRESH DEVICE + CACHE OFF",False,None,False),
                ("FRESH DEVICE + RANDOM + CACHE OFF",False,"random",False),
                ("FRESH DEVICE + CACHE ON",True,None,False),
            ]
            for label,use_cache,address_type,pair in scan_strategies:
                client=await connect_target(entry,label,device,use_cache,24,address_type,pair)
                if client is not None:
                    return client,attempt_no
                await asyncio.sleep(1.0)

        self.connection_state.update({"connected":False,"phase":"failed"})
        msg=(
            "El reloj está identificado pero Windows no consiguió abrir su sesión GATT ni por "
            "conexión WinRT directa ni por escaneo fresco. V0.91 ya no depende de que el reloj "
            "esté anunciándose para el primer intento."
        )
        progress(msg)
        raise RuntimeError(msg)
'''
s=s[:conn_start]+new_conn+s[conn_end:]

s=s.replace(
    'V0.91 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.91; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Cada anuncio fresco prueba CACHE OFF antes que CACHE ON.',
    'V0.91 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.91; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Primero abre WinRT directo con la dirección conocida, sin depender del escaneo.'
)
s=s.replace(
    'V0.91 · GATT SECUENCIA CORREGIDA · conserva V0.88; cada vez que aparece el reloj prueba DEVICE/OFF → ADDRESS/OFF → DEVICE/ON → ADDRESS/ON antes de descartarlo.',
    'V0.91 · GATT DIRECTO WINRT · conserva la esfera sincronizada; usa un BLEDevice sintético con la dirección conocida para saltar el escaneo implícito de Windows y luego prueba random/cache/pair.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.91 aplicado")
