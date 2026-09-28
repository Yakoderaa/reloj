from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.95.0"' not in s:
    raise SystemExit("V0.96 requiere la base V0.95 aplicada")
s=s.replace('APP_VERSION="0.95.0"','APP_VERSION="0.96.0"',1)
s=s.replace('V0.95','V0.96')

conn_start=s.index("    async def connect_retry(")
conn_end=s.index("\n    def diagnose(",conn_start)
new_conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={
            "connected":False,"attempts":0,"phase":"targeted_uncached_probe",
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

        async def fresh_watch(timeout=10.0):
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

        async def targeted_uncached_probe(client,label,seconds=24.0):
            # CACHE ON can expose a stale tree. This probe bypasses that cache only
            # for the single service that owns B001/B002. A SUCCESS here proves
            # real ATT traffic reached the watch.
            import uuid as _uuid
            from winrt.windows.devices.bluetooth import BluetoothCacheMode

            b001="0000b001-0000-1000-8000-00805f9b34fb"
            b002="0000b002-0000-1000-8000-00805f9b34fb"
            cached_b001=client.services.get_characteristic(b001)
            cached_b002=client.services.get_characteristic(b002)
            if cached_b001 is None or cached_b002 is None:
                self.connection_state["physical_checks"].append({
                    "stage":label,"ready":False,"reason":"cached tree missing B001/B002"
                })
                return False

            service_uuid=str(getattr(cached_b002,"service_uuid","") or getattr(cached_b001,"service_uuid",""))
            if not service_uuid:
                self.connection_state["physical_checks"].append({
                    "stage":label,"ready":False,"reason":"parent service uuid unavailable"
                })
                return False

            backend=getattr(client,"_backend",None)
            requester=getattr(backend,"_requester",None)
            session=getattr(backend,"_session",None)
            if requester is None or session is None:
                self.connection_state["physical_checks"].append({
                    "stage":label,"ready":False,"reason":"missing WinRT requester/session"
                })
                return False

            deadline=time.monotonic()+seconds
            probe_no=0
            while time.monotonic()<deadline:
                probe_no+=1
                snap={
                    "probe":probe_no,
                    "service_uuid":service_uuid,
                    "client_is_connected":bool(getattr(client,"is_connected",False)),
                    "requester_connection_status":enum_name(getattr(requester,"connection_status",None)),
                    "session_status":enum_name(getattr(session,"session_status",None)),
                    "mtu":getattr(client,"mtu_size",None),
                }
                try:
                    result=await asyncio.wait_for(
                        requester.get_gatt_services_for_uuid_with_cache_mode_async(
                            _uuid.UUID(service_uuid),BluetoothCacheMode.UNCACHED
                        ),
                        timeout=6.0
                    )
                    status=enum_name(getattr(result,"status",None))
                    snap["service_status"]=status
                    snap["service_protocol_error"]=getattr(result,"protocol_error",None)
                    if status=="success":
                        native_services=list(getattr(result,"services",[]) or [])
                        found=set()
                        char_statuses=[]
                        for svc in native_services:
                            try:
                                cres=await asyncio.wait_for(
                                    svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.UNCACHED),
                                    timeout=6.0
                                )
                                cstatus=enum_name(getattr(cres,"status",None))
                                char_statuses.append(cstatus)
                                if cstatus=="success":
                                    for ch in list(getattr(cres,"characteristics",[]) or []):
                                        found.add(str(getattr(ch,"uuid","")).lower())
                            finally:
                                try:svc.close()
                                except Exception:pass
                        snap["characteristic_statuses"]=char_statuses
                        snap["native_characteristics"]=sorted(found)
                        ready=(b001 in found and b002 in found)
                        snap["ready"]=ready
                        self.connection_state["physical_checks"].append(snap)
                        if ready:
                            progress(label+" · UNCACHED TARGET SUCCESS · B001/B002 físicos confirmados · MTU="+str(snap.get("mtu")))
                            return True
                    self.connection_state["physical_checks"].append(snap)
                    progress(label+" · probe "+str(probe_no)+" · status="+str(status)+
                             " · requester="+str(snap.get("requester_connection_status"))+
                             " · session="+str(snap.get("session_status")))
                except Exception as ex:
                    snap["ready"]=False
                    snap["error"]=type(ex).__name__+": "+str(ex)
                    self.connection_state["physical_checks"].append(snap)
                    progress(label+" · probe "+str(probe_no)+" · "+type(ex).__name__+": "+str(ex))

                if not bool(getattr(client,"is_connected",False)):
                    progress(label+" · la sesión se cerró durante el probe físico.")
                    return False
                await asyncio.sleep(1.0)
            return False

        async def explicit_pair(client,label):
            rec={"stage":label}
            try:
                backend=getattr(client,"_backend",None)
                requester=getattr(backend,"_requester",None)
                try:
                    di=getattr(requester,"device_information",None)
                    pairing=getattr(di,"pairing",None)
                    rec["before_is_paired"]=bool(getattr(pairing,"is_paired",False)) if pairing is not None else None
                    rec["before_can_pair"]=bool(getattr(pairing,"can_pair",False)) if pairing is not None else None
                except Exception:
                    rec["before_is_paired"]=None;rec["before_can_pair"]=None
                emit_msg="PAIRING WINDOWS · "+label
                progress(emit_msg)
                await asyncio.wait_for(client.pair(),timeout=35)
                rec["ok"]=True
                try:
                    requester=getattr(getattr(client,"_backend",None),"_requester",None)
                    di=getattr(requester,"device_information",None)
                    pairing=getattr(di,"pairing",None)
                    rec["after_is_paired"]=bool(getattr(pairing,"is_paired",False)) if pairing is not None else None
                except Exception:
                    rec["after_is_paired"]=None
                progress(emit_msg+" · OK")
                return True
            except Exception as ex:
                rec["ok"]=False
                rec["error"]=type(ex).__name__+": "+str(ex)
                progress("PAIRING WINDOWS · FALLÓ · "+rec["error"])
                return False
            finally:
                self.connection_state["pairing_checks"].append(rec)

        async def connect_bootstrap(entry,label,target,outer_timeout=34,pair_after_probe=False):
            nonlocal last,attempt_no
            attempt_no+=1
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            client=None;keep=False
            try:
                kwargs={"timeout":26}
                if sys.platform=="win32":
                    kwargs["winrt"]={"use_cached_services":True}
                client=BleakClient(target,**kwargs)
                await asyncio.wait_for(client.connect(),timeout=outer_timeout)
                if not client.is_connected:
                    raise RuntimeError("Windows no confirmó GattSession ACTIVE")
                services=list(client.services)
                if not services:
                    raise RuntimeError("bootstrap GATT sin servicios")
                if client.services.get_characteristic("0000b001-0000-1000-8000-00805f9b34fb") is None or \
                   client.services.get_characteristic("0000b002-0000-1000-8000-00805f9b34fb") is None:
                    raise RuntimeError("bootstrap cacheado sin B001/B002")

                progress(label+" · cache visible; validando servicio físico UNCACHED dirigido…")
                ready=await targeted_uncached_probe(client,label+" PHYSICAL",24.0)
                if not ready and pair_after_probe and bool(getattr(client,"is_connected",False)):
                    await explicit_pair(client,label)
                    await asyncio.sleep(2.0)
                    ready=await targeted_uncached_probe(client,label+" POST-PAIR",24.0)

                if not ready:
                    raise RuntimeError("bootstrap cacheado sin confirmación ATT UNCACHED física")

                keep=True
                self.selected=entry
                self.connection_state.update({
                    "connected":True,"phase":"physical_ready","strategy":label,
                    "address":entry.get("address"),"name":entry.get("name"),
                    "cache_bootstrap":True,"targeted_uncached_verified":True
                })
                return client
            except asyncio.TimeoutError as ex:
                last=ex;progress(label+" · TIMEOUT")
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

        # Use the remembered address to bootstrap immediately, but only accept it
        # after the targeted UNCACHED probe physically confirms B001+B002.
        if sys.platform=="win32" and remembered_ok:
            from bleak.backends.device import BLEDevice
            synthetic=BLEDevice(
                remembered["address"],
                remembered.get("name") or "Apple Watch Ultra",
                None
            )
            progress("RUTA 1 · DIRECT WINRT + CACHE ON bootstrap + UNCACHED dirigido.")
            client=await connect_bootstrap(
                remembered,"DIRECT CACHE ON + TARGETED UNCACHED",synthetic,34,False
            )
            if client is not None:return client,attempt_no

        # Fresh advertisement can refresh Windows' device identity, then run the
        # same targeted physical proof.
        progress("RUTA 2 · buscando anuncio fresco hasta 15 s…")
        fresh=await fresh_watch(15.0)
        if fresh is not None:
            progress("AUTO-ID · "+fresh["name"]+" · "+fresh["address"]+
                     " · RSSI="+str(fresh.get("rssi"))+" · score="+str(watch_score(fresh)))
            dev=fresh.get("device")
            if dev is not None:
                client=await connect_bootstrap(
                    fresh,"FRESH DEVICE CACHE ON + TARGETED UNCACHED",dev,36,False
                )
                if client is not None:return client,attempt_no

                # Last recovery: same fresh identity, but pair explicitly while
                # the cached session is still open, then repeat UNCACHED probe.
                client=await connect_bootstrap(
                    fresh,"FRESH DEVICE + WINDOWS PAIR + TARGETED UNCACHED",dev,40,True
                )
                if client is not None:return client,attempt_no
        else:
            progress("RUTA 2 · el reloj no anunció durante la ventana.")

        self.connection_state.update({"connected":False,"phase":"failed"})
        msg=(
            "Windows puede recordar el árbol GATT del UtraWatch, pero el servicio que contiene B001/B002 "
            "no respondió a una consulta UNCACHED dirigida. V0.96 no acepta la caché como conexión real."
        )
        progress(msg)
        raise RuntimeError(msg)
'''
s=s[:conn_start]+new_conn+s[conn_end:]

s=s.replace(
    'V0.96 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.96; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. No acepta GATT cacheado: exige enlace físico WinRT antes de escribir.',
    'V0.96 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.96; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Verifica físicamente B001/B002 con consulta UNCACHED dirigida antes de escribir.'
)
s=s.replace(
    'V0.96 · ENLACE FÍSICO REAL · recupera BLEDevice real + CACHE OFF con timeout largo, valida requester/session/MTU y usa pairing correcto como último recurso.',
    'V0.96 · UNCACHED DIRIGIDO · usa CACHE ON sólo para localizar el árbol y exige SUCCESS UNCACHED del servicio B001/B002; pairing Windows se usa sólo como recuperación.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.96 aplicado")
