from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.94.0"' not in s:
    raise SystemExit("V0.95 requiere la base V0.94 aplicada")
s=s.replace('APP_VERSION="0.94.0"','APP_VERSION="0.95.0"',1)
s=s.replace('V0.94','V0.95')

conn_start=s.index("    async def connect_retry(")
conn_end=s.index("\n    def diagnose(",conn_start)
new_conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={
            "connected":False,"attempts":0,"phase":"physical_link",
            "strategies":[],"physical_checks":[],"pairing_checks":[]
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

        async def fresh_watch(timeout=12.0):
            found=await BleakScanner.discover(timeout=timeout,return_adv=True)
            rows=[adv_row(d,a) for _,(d,a) in found.items()]
            rows=[x for x in rows if watch_score(x)>0]
            rows.sort(key=lambda x:(watch_score(x),x["rssi"] if x["rssi"] is not None else -999),reverse=True)
            if not rows:return None
            best=rows[0]
            self.selected=best
            return best

        def enum_name(v):
            if v is None:return None
            n=getattr(v,"name",None)
            if n is not None:return str(n).lower()
            return str(v).split(".")[-1].strip().lower()

        def physical_snapshot(client):
            backend=getattr(client,"_backend",None)
            requester=getattr(backend,"_requester",None)
            session=getattr(backend,"_session",None)
            try:rstat=enum_name(getattr(requester,"connection_status",None))
            except Exception:rstat=None
            try:sstat=enum_name(getattr(session,"session_status",None))
            except Exception:sstat=None
            try:mtu=int(getattr(client,"mtu_size",0) or 0)
            except Exception:mtu=0
            try:
                di=getattr(requester,"device_information",None)
                pairing=getattr(di,"pairing",None)
                paired=bool(getattr(pairing,"is_paired",False)) if pairing is not None else None
                can_pair=bool(getattr(pairing,"can_pair",False)) if pairing is not None else None
            except Exception:
                paired=None;can_pair=None
            return {
                "is_connected":bool(getattr(client,"is_connected",False)),
                "requester_connection_status":rstat,
                "session_status":sstat,
                "mtu":mtu,
                "windows_is_paired":paired,
                "windows_can_pair":can_pair
            }

        def snapshot_is_physical(snap):
            # This model negotiated MTU=512 in the successful V0.83 path.
            # Cached-only WinRT sessions in V0.91-V0.94 sat at MTU=23 and
            # immediately returned GattCommunicationStatus.UNREACHABLE.
            requester_ok=(snap.get("requester_connection_status")=="connected")
            session_ok=(snap.get("session_status")=="active")
            mtu_ok=int(snap.get("mtu") or 0)>23
            return bool(snap.get("is_connected") and session_ok and (requester_ok or mtu_ok))

        async def wait_physical(client,label,seconds=20.0):
            deadline=time.monotonic()+seconds
            last_snap=None
            while time.monotonic()<deadline:
                snap=physical_snapshot(client);last_snap=snap
                if snapshot_is_physical(snap):
                    self.connection_state["physical_checks"].append({"stage":label,"ready":True,**snap})
                    progress(label+" · ENLACE FÍSICO OK · requester="+str(snap.get("requester_connection_status"))+
                             " · session="+str(snap.get("session_status"))+" · MTU="+str(snap.get("mtu")))
                    return True,snap
                await asyncio.sleep(.5)
            snap=last_snap or physical_snapshot(client)
            self.connection_state["physical_checks"].append({"stage":label,"ready":False,**snap})
            progress(label+" · SOLO CACHE / SIN ENLACE FÍSICO · requester="+str(snap.get("requester_connection_status"))+
                     " · session="+str(snap.get("session_status"))+" · MTU="+str(snap.get("mtu")))
            return False,snap

        def has_watch_chars(client):
            try:
                char_ids=set()
                for svc in list(client.services):
                    for ch in svc.characteristics:
                        char_ids.add(str(ch.uuid).lower())
                return (
                    "0000b001-0000-1000-8000-00805f9b34fb" in char_ids and
                    "0000b002-0000-1000-8000-00805f9b34fb" in char_ids
                )
            except Exception:
                return False

        async def connect_route(entry,label,target,use_cache,internal_timeout,outer_timeout,pair=False,physical_wait=16):
            nonlocal last,attempt_no
            attempt_no+=1
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append({
                "label":label,"cache":bool(use_cache),"pair":bool(pair),
                "internal_timeout":internal_timeout,"outer_timeout":outer_timeout
            })
            progress(f"CONEXIÓN {attempt_no} · {label}")
            client=None;keep=False
            try:
                kwargs={"timeout":internal_timeout,"pair":bool(pair)}
                if sys.platform=="win32":
                    kwargs["winrt"]={"use_cached_services":bool(use_cache)}
                client=BleakClient(target,**kwargs)
                await asyncio.wait_for(client.connect(),timeout=outer_timeout)
                if not client.is_connected:
                    raise RuntimeError("Windows no confirmó GattSession ACTIVE")
                services=list(client.services)
                if not services:
                    raise RuntimeError("GATT abrió sin servicios")
                if not has_watch_chars(client):
                    raise RuntimeError("GATT abrió árbol incompleto: faltan B001/B002")

                ready,snap=await wait_physical(client,label,physical_wait)
                self.connection_state["pairing_checks"].append({
                    "stage":label,
                    "windows_is_paired":snap.get("windows_is_paired"),
                    "windows_can_pair":snap.get("windows_can_pair")
                })
                if not ready:
                    raise RuntimeError("servicios visibles pero vínculo físico no establecido")

                keep=True
                self.selected=entry
                self.connection_state.update({
                    "connected":True,"phase":"physical_ready","strategy":label,
                    "address":entry.get("address"),"name":entry.get("name"),
                    "cache":bool(use_cache),"pair_requested":bool(pair),
                    "physical_snapshot":snap
                })
                return client
            except asyncio.TimeoutError as ex:
                last=ex
                progress(label+" · TIMEOUT")
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
                            await asyncio.wait_for(client.disconnect(),timeout=6)
                    except Exception:
                        pass

        remembered=self.selected or {}
        remembered_ok=bool(remembered.get("address") and watch_score(remembered)>0)
        live_device=remembered.get("device") if remembered_ok else None

        # 1) Restore the historical successful shape: a real BLEDevice from the
        # GUI scan, uncached services, and the original long Windows timeout.
        if live_device is not None:
            progress("RUTA FÍSICA 1 · BLEDevice REAL + CACHE OFF · timeout largo (histórico V0.83).")
            client=await connect_route(
                remembered,"LIVE DEVICE + CACHE OFF",live_device,
                False,40,48,False,12
            )
            if client is not None:return client,attempt_no

        # 2) Obtain a fresh connectable advertisement, then immediately use
        # uncached discovery. This avoids mistaking the system-wide GATT cache
        # for a live watch.
        progress("RUTA FÍSICA 2 · buscando anuncio fresco hasta 15 s…")
        fresh=await fresh_watch(15.0)
        if fresh is not None:
            progress("AUTO-ID · "+fresh["name"]+" · "+fresh["address"]+
                     " · RSSI="+str(fresh.get("rssi"))+" · score="+str(watch_score(fresh)))
            dev=fresh.get("device")
            if dev is not None:
                client=await connect_route(
                    fresh,"FRESH DEVICE + CACHE OFF",dev,
                    False,42,52,False,15
                )
                if client is not None:return client,attempt_no
        else:
            progress("RUTA FÍSICA 2 · no hubo anuncio fresco.")

        # 3) CACHE ON is only a bootstrap now. It is accepted only if the
        # underlying WinRT requester becomes physically CONNECTED or the MTU
        # negotiates above the cached-only value 23.
        base=fresh if fresh is not None else remembered
        if sys.platform=="win32" and base and base.get("address"):
            from bleak.backends.device import BLEDevice
            synthetic=BLEDevice(base["address"],base.get("name") or "Apple Watch Ultra",None)
            progress("RUTA FÍSICA 3 · CACHE ON sólo como bootstrap; esperando conexión WinRT real.")
            client=await connect_route(
                base,"DIRECT WINRT + CACHE ON + PHYSICAL GATE",synthetic,
                True,30,38,False,24
            )
            if client is not None:return client,attempt_no

            # 4) Security recovery. We had never tried Windows pairing with the
            # correct/default address type; previous PAIR attempt incorrectly
            # forced RANDOM and failed before pairing. This can establish the
            # encrypted link if Windows/watch now require it.
            progress("RUTA FÍSICA 4 · intentando pairing Windows correcto (sin RANDOM)…")
            client=await connect_route(
                base,"DIRECT WINRT + PAIR + CACHE ON",synthetic,
                True,40,55,True,24
            )
            if client is not None:return client,attempt_no

        self.connection_state.update({"connected":False,"phase":"failed"})
        msg=(
            "Windows ve el UtraWatch y conoce sus servicios, pero no logró establecer el enlace BLE físico. "
            "V0.95 ya distingue caché GATT de conexión real y probó BLEDevice real/uncached, anuncio fresco, "
            "bootstrap WinRT y pairing correcto."
        )
        progress(msg)
        raise RuntimeError(msg)
'''
s=s[:conn_start]+new_conn+s[conn_end:]

s=s.replace(
    'V0.95 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.95; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Prioriza la única ruta GATT que ya abrió el reloj: DIRECT WINRT + CACHE ON.',
    'V0.95 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.95; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. No acepta GATT cacheado: exige enlace físico WinRT antes de escribir.'
)
s=s.replace(
    'V0.95 · RUTA GATT PROBADA · elimina CACHE OFF/RANDOM antes de conectar; abre primero DIRECT WINRT + CACHE ON y conserva PREWAKE B002 + CCCD directo de V0.93.',
    'V0.95 · ENLACE FÍSICO REAL · recupera BLEDevice real + CACHE OFF con timeout largo, valida requester/session/MTU y usa pairing correcto como último recurso.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.95 aplicado")
