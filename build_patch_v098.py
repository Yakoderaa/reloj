from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.97.0"' not in s:
    raise SystemExit("V0.98 requiere la base V0.97 aplicada")
s=s.replace('APP_VERSION="0.97.0"','APP_VERSION="0.98.0"',1)
s=s.replace('V0.97','V0.98')

conn_start=s.index("    async def connect_retry(")
conn_end=s.index("\n    def diagnose(",conn_start)
new_conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={
            "connected":False,"attempts":0,"phase":"cached_att_gate",
            "strategies":[],"physical_checks":[]
        }
        last=None
        attempt_no=0
        b001="0000b001-0000-1000-8000-00805f9b34fb"
        b002="0000b002-0000-1000-8000-00805f9b34fb"

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
            return {"device":d,"name":a.local_name or d.name or "(sin nombre)",
                    "address":d.address,"rssi":a.rssi,"service_uuids":list(a.service_uuids or []),
                    "manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},
                    "service_data":{str(k):v.hex() for k,v in a.service_data.items()},"tx_power":a.tx_power}

        async def fresh_watch(timeout=8.0):
            found=await BleakScanner.discover(timeout=timeout,return_adv=True)
            rows=[adv_row(d,a) for _,(d,a) in found.items()]
            rows=[x for x in rows if watch_score(x)>0]
            rows.sort(key=lambda x:(watch_score(x),x["rssi"] if x["rssi"] is not None else -999),reverse=True)
            if not rows:return None
            self.selected=rows[0]
            return rows[0]

        async def cached_connect(entry,label,target,timeout_s=28):
            nonlocal last,attempt_no
            attempt_no+=1
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            client=None;keep=False
            try:
                kwargs={"timeout":20}
                if sys.platform=="win32":kwargs["winrt"]={"use_cached_services":True}
                client=BleakClient(target,**kwargs)
                await asyncio.wait_for(client.connect(),timeout=timeout_s)
                if not client.is_connected:raise RuntimeError("Windows no confirmó is_connected")
                c1=client.services.get_characteristic(b001)
                c2=client.services.get_characteristic(b002)
                if c1 is None or c2 is None:raise RuntimeError("caché GATT sin B001/B002")
                snap={"stage":label,"b001_handle":getattr(c1,"handle",None),"b002_handle":getattr(c2,"handle",None),
                      "mtu":getattr(client,"mtu_size",None),"att_write":False}
                progress(label+" · GATT CACHE OK · B001="+str(snap["b001_handle"])+" · B002="+str(snap["b002_handle"])+" · MTU="+str(snap["mtu"]))

                # V0.95 proved requester/session/MTU are not enough. Validate the link
                # with actual ATT traffic on B002. Try both legal write modes; only a
                # successful ATT write is accepted as physical readiness.
                write_errors=[]
                for response in (False,True):
                    try:
                        progress(label+" · PHYSICAL ATT GATE · B002 write "+("WITH" if response else "WITHOUT")+" response")
                        await asyncio.wait_for(client.write_gatt_char(c2,b"\\x00",response=response),timeout=8)
                        snap["att_write"]=True;snap["att_write_response"]=response
                        break
                    except Exception as ex:
                        write_errors.append(type(ex).__name__+": "+str(ex))
                snap["att_errors"]=write_errors
                self.connection_state["physical_checks"].append(snap)
                if not snap["att_write"]:
                    raise RuntimeError("B002 no aceptó tráfico ATT real: "+" | ".join(write_errors))

                keep=True;self.selected=entry
                self.connection_state.update({"connected":True,"phase":"physical_ready","strategy":label,
                    "address":entry.get("address"),"name":entry.get("name"),"att_gate":True})
                progress(label+" · ENLACE FÍSICO CONFIRMADO POR B002 ATT")
                return client
            except asyncio.TimeoutError as ex:
                last=ex;progress(label+" · TIMEOUT")
                return None
            except asyncio.CancelledError:raise
            except Exception as ex:
                last=ex;progress(label+" · FALLÓ · "+type(ex).__name__+": "+str(ex))
                return None
            finally:
                if client is not None and not keep:
                    try:
                        if client.is_connected:await asyncio.wait_for(client.disconnect(),timeout=5)
                    except Exception:pass

        # V0.97 established that forcing UNCACHED service discovery can stall for
        # 78-90 s even while the watch advertises. Return to the route that V0.91
        # physically opened on this machine: DIRECT WINRT + CACHE ON, but never
        # confuse the cached tree with readiness; B002 ATT is the gate.
        remembered=self.selected or {}
        if sys.platform=="win32" and remembered.get("address"):
            from bleak.backends.device import BLEDevice
            synthetic=BLEDevice(remembered["address"],remembered.get("name") or "Apple Watch Ultra",None)
            progress("RUTA 1 · DIRECT WINRT + CACHE ON; B002 ATT decide si el enlace es físico.")
            c=await cached_connect(remembered,"DIRECT WINRT CACHE ON + ATT GATE",synthetic,30)
            if c is not None:return c,attempt_no

        progress("RUTA 2 · anuncio fresco + CACHE ON + ATT GATE.")
        for n in range(2):
            fresh=await fresh_watch(8.0)
            if fresh is None:
                progress("AUTO-ID · ronda "+str(n+1)+" sin anuncio UtraWatch")
                continue
            progress("AUTO-ID · "+fresh["name"]+" · "+fresh["address"]+" · RSSI="+str(fresh.get("rssi"))+" · score="+str(watch_score(fresh)))
            if fresh.get("device") is not None:
                c=await cached_connect(fresh,"FRESH DEVICE CACHE ON + ATT GATE",fresh["device"],30)
                if c is not None:return c,attempt_no
            await asyncio.sleep(2)

        self.connection_state.update({"connected":False,"phase":"failed"})
        msg="El reloj anuncia y Windows conoce B001/B002, pero B002 todavía no acepta tráfico ATT real. V0.98 ya no espera UNCACHED durante 90 s ni considera la caché una conexión física."
        progress(msg)
        raise RuntimeError(msg+((" Último error: "+str(last)) if last else ""))
'''
s=s[:conn_start]+new_conn+s[conn_end:]

s=s.replace(
    'V0.98 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.98; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Bleak abre únicamente E91A UNCACHED antes del handshake.',
    'V0.98 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.98; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Recupera DIRECT CACHE ON y exige tráfico ATT real en B002.'
)
s=s.replace(
    'V0.98 · TARGET SERVICE CONNECT · corrige V0.96: la consulta dirigida ocurre dentro de Bleak connect usando services={E91A}, sin enumerar todo GATT ni cancelar WinRT prematuramente.',
    'V0.98 · ATT PHYSICAL GATE · V0.97 confirmó que UNCACHED dirigido se atasca; vuelve a la ruta CACHE ON que sí abrió GATT históricamente, pero sólo acepta conexión después de una escritura ATT real en B002.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.98 aplicado")
