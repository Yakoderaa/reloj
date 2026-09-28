from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.96.0"' not in s:
    raise SystemExit("V0.97 requiere la base V0.96 aplicada")
s=s.replace('APP_VERSION="0.96.0"','APP_VERSION="0.97.0"',1)
s=s.replace('V0.96','V0.97')

conn_start=s.index("    async def connect_retry(")
conn_end=s.index("\n    def diagnose(",conn_start)
new_conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={
            "connected":False,"attempts":0,"phase":"target_service_connect",
            "strategies":[],"physical_checks":[],"pairing_checks":[]
        }
        last=None
        attempt_no=0
        control_service="0000e91a-0000-1000-8000-00805f9b34fb"
        b001="0000b001-0000-1000-8000-00805f9b34fb"
        b002="0000b002-0000-1000-8000-00805f9b34fb"

        def watch_score(x):
            services={str(v).lower() for v in (x.get("service_uuids") or [])}
            service_data={str(k).lower():v for k,v in (x.get("service_data") or {}).items()}
            name=(x.get("name") or "").strip().lower()
            manufacturer=x.get("manufacturer_data") or {}
            score=0
            if control_service in services:score+=120
            if "00003802-0000-1000-8000-00805f9b34fb" in services:score+=110
            if any("3802" in k for k in service_data):score+=110
            if name=="apple watch ultra":score+=60
            if str(manufacturer.get("255","")).lower()=="00a6":score+=40
            return score

        def adv_row(d,a):
            return {
                "device":d,"name":a.local_name or d.name or "(sin nombre)",
                "address":d.address,"rssi":a.rssi,
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
            best=rows[0]; self.selected=best
            return best

        def enum_name(v):
            if v is None:return None
            n=getattr(v,"name",None)
            if n is not None:return str(n).lower()
            return str(v).split(".")[-1].strip().lower()

        async def connect_target(entry,label,target,use_cache=False,timeout=78):
            nonlocal last,attempt_no
            attempt_no+=1
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            client=None;keep=False
            try:
                # Critical V0.97 change: Bleak itself now requests ONLY E91A.
                # V0.96 timed out inside BleakClient.connect() before our later
                # targeted probe could run, because connect() was still resolving
                # the complete GATT tree. services={E91A} makes WinRT call
                # GetGattServicesForUuidAsync and enumerate only this service.
                kwargs={
                    "timeout":timeout,
                    "services":{control_service},
                }
                if sys.platform=="win32":
                    kwargs["winrt"]={"use_cached_services":bool(use_cache)}
                client=BleakClient(target,**kwargs)
                await client.connect()
                if not client.is_connected:
                    raise RuntimeError("sesión GATT no quedó ACTIVE")

                c1=client.services.get_characteristic(b001)
                c2=client.services.get_characteristic(b002)
                backend=getattr(client,"_backend",None)
                requester=getattr(backend,"_requester",None)
                session=getattr(backend,"_session",None)
                snap={
                    "stage":label,
                    "ready":bool(c1 is not None and c2 is not None),
                    "requested_service":control_service,
                    "use_cached_services":bool(use_cache),
                    "b001_handle":getattr(c1,"handle",None),
                    "b002_handle":getattr(c2,"handle",None),
                    "requester_connection_status":enum_name(getattr(requester,"connection_status",None)),
                    "session_status":enum_name(getattr(session,"session_status",None)),
                    "mtu":getattr(client,"mtu_size",None),
                }
                self.connection_state["physical_checks"].append(snap)
                if c1 is None or c2 is None:
                    raise RuntimeError("E91A respondió pero no expuso B001/B002")

                # With use_cached_services=False, successful Bleak connect means
                # WinRT completed UNCACHED service/characteristic/descriptor I/O
                # against E91A and the GATT session reached ACTIVE.
                if not use_cache:
                    progress(label+" · TARGET E91A UNCACHED SUCCESS · B001="+str(snap["b001_handle"])+
                             " · B002="+str(snap["b002_handle"])+" · MTU="+str(snap["mtu"]))
                else:
                    progress(label+" · TARGET E91A CACHE RECOVERY · B001/B002 visibles · MTU="+str(snap["mtu"]))

                keep=True
                self.selected=entry
                self.connection_state.update({
                    "connected":True,"phase":"physical_ready","strategy":label,
                    "address":entry.get("address"),"name":entry.get("name"),
                    "requested_service":control_service,
                    "targeted_connect":True,
                    "uncached_verified":not use_cache,
                })
                return client
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                last=ex
                self.connection_state["physical_checks"].append({
                    "stage":label,"ready":False,"error":type(ex).__name__+": "+str(ex)
                })
                progress(label+" · FALLÓ · "+type(ex).__name__+": "+str(ex))
                return None
            finally:
                if client is not None and not keep:
                    try:
                        if client.is_connected: await client.disconnect()
                    except Exception:pass

        # First get a current BLEDevice. This refreshes the Windows device cache
        # without touching GATT and avoids guessing address_type.
        progress("RUTA 1 · anuncio fresco + conexión UNCACHED limitada a E91A.")
        fresh=await fresh_watch(12.0)
        if fresh is not None:
            progress("AUTO-ID · "+fresh["name"]+" · "+fresh["address"]+
                     " · RSSI="+str(fresh.get("rssi"))+" · score="+str(watch_score(fresh)))
            dev=fresh.get("device")
            if dev is not None:
                client=await connect_target(fresh,"FRESH TARGET E91A UNCACHED",dev,False,78)
                if client is not None:return client,attempt_no

                # One clean retry after a fresh advertisement. No nested wait_for:
                # WinRT GATT operations cannot really be cancelled and premature
                # cancellation can leave requests queued in the Windows stack.
                progress("RUTA 2 · refrescando anuncio antes del segundo intento físico…")
                await asyncio.sleep(2.0)
                fresh2=await fresh_watch(8.0)
                if fresh2 is not None and fresh2.get("device") is not None:
                    client=await connect_target(fresh2,"RETRY TARGET E91A UNCACHED",fresh2["device"],False,90)
                    if client is not None:return client,attempt_no
        else:
            progress("RUTA 1 · el reloj no anunció durante la ventana.")

        self.connection_state.update({"connected":False,"phase":"failed"})
        msg=(
            "El reloj anuncia, pero Windows no logró abrir físicamente el servicio E91A solicitado de forma dirigida. "
            "V0.97 ya no enumera el árbol GATT completo antes de esta prueba."
        )
        progress(msg)
        raise RuntimeError(msg+((" Último error: "+str(last)) if last else ""))
'''
s=s[:conn_start]+new_conn+s[conn_end:]

s=s.replace(
    'V0.97 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.97; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Verifica físicamente B001/B002 con consulta UNCACHED dirigida antes de escribir.',
    'V0.97 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.97; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Bleak abre únicamente E91A UNCACHED antes del handshake.'
)
s=s.replace(
    'V0.97 · UNCACHED DIRIGIDO · usa CACHE ON sólo para localizar el árbol y exige SUCCESS UNCACHED del servicio B001/B002; pairing Windows se usa sólo como recuperación.',
    'V0.97 · TARGET SERVICE CONNECT · corrige V0.96: la consulta dirigida ocurre dentro de Bleak connect usando services={E91A}, sin enumerar todo GATT ni cancelar WinRT prematuramente.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.97 aplicado")
