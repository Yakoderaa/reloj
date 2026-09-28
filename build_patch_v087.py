from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.86.0"' not in s:
    raise SystemExit("V0.87 requiere la base V0.86 aplicada")
s=s.replace('APP_VERSION="0.86.0"','APP_VERSION="0.87.0"',1)
s=s.replace('V0.86','V0.87')

scan_start=s.index("    def scan(self):")
scan_end=s.index("    def pick(self,_=None):",scan_start)
new_scan='''    def scan(self):
        if self.ble_busy:
            self.status.set("Esperá a que termine la operación Bluetooth actual."); return
        self.selected=None
        for button in (self.diag,self.listen,self.explore):button.config(state="disabled")
        self.status.set("Buscando el reloj UtraWatch durante 10 segundos…")
        self.tree.delete(*self.tree.get_children()); self.devices=[]

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

        async def work():
            found=await BleakScanner.discover(timeout=10,return_adv=True); out=[]
            for _,(d,a) in found.items():
                row={"device":d,"name":a.local_name or d.name or "(sin nombre)","address":d.address,"rssi":a.rssi,
                     "service_uuids":list(a.service_uuids or []),
                     "manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},
                     "service_data":{str(k):v.hex() for k,v in a.service_data.items()},
                     "tx_power":a.tx_power}
                row["_watch_score"]=watch_score(row)
                out.append(row)
            return sorted(out,key=lambda x:(x.get("_watch_score",0),x["rssi"] if x["rssi"] is not None else -999),reverse=True)

        def done(r,e):
            if e:
                self.status.set("Error de escaneo: "+repr(e)); messagebox.showerror("Bluetooth",repr(e)); return
            self.devices=r
            for i,x in enumerate(r):
                label=x["name"]
                if x.get("_watch_score",0)>0:label="✓ RELOJ · "+label
                self.tree.insert("","end",iid=str(i),values=(label,x["address"],x["rssi"]))
            candidates=[(i,x) for i,x in enumerate(r) if x.get("_watch_score",0)>0]
            if candidates:
                i,x=candidates[0]
                self.selected=x
                self.tree.selection_set(str(i)); self.tree.focus(str(i)); self.tree.see(str(i))
                for button in (self.diag,self.listen,self.explore):button.config(state="normal")
                self.status.set("Reloj UtraWatch identificado automáticamente: "+x["name"]+" · "+x["address"])
            else:
                self.status.set(str(len(r))+" BLE encontrados, pero ninguno coincide con la firma UtraWatch.")
        self.run_async(work(),done)
'''
s=s[:scan_start]+new_scan+s[scan_end:]

conn_start=s.index("    async def connect_retry(")
conn_end=s.index("\n    def diagnose(",conn_start)
new_conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={"connected":False,"attempts":0,"phase":"starting","strategies":[]}
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
            return {"device":d,"name":a.local_name or d.name or "(sin nombre)","address":d.address,"rssi":a.rssi,
                    "service_uuids":list(a.service_uuids or []),
                    "manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},
                    "service_data":{str(k):v.hex() for k,v in a.service_data.items()},
                    "tx_power":a.tx_power}

        async def discover_watch(timeout=12):
            progress("AUTO-ID · buscando firma UtraWatch E91A/3802…")
            found=await BleakScanner.discover(timeout=timeout,return_adv=True)
            rows=[adv_row(d,a) for _,(d,a) in found.items()]
            rows=[x for x in rows if watch_score(x)>0]
            rows.sort(key=lambda x:(watch_score(x),x["rssi"] if x["rssi"] is not None else -999),reverse=True)
            if not rows:return None
            best=rows[0]
            progress("AUTO-ID · reloj encontrado · "+best["name"]+" · "+best["address"]+" · score="+str(watch_score(best)))
            self.selected=best
            return best

        async def try_target(label,target,use_cache,entry=None):
            nonlocal last,attempt_no
            attempt_no+=1
            client=None;keep=False
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            try:
                kwargs={"timeout":24}
                if sys.platform=="win32":kwargs["winrt"]={"use_cached_services":bool(use_cache)}
                client=BleakClient(target,**kwargs)
                try:
                    await asyncio.wait_for(client.connect(),timeout=27)
                except asyncio.TimeoutError:
                    if not client.is_connected:raise
                    progress(label+" · connect() agotó espera pero Windows informa conectado; validando GATT…")
                if not client.is_connected:raise RuntimeError("Windows no confirmó is_connected")
                services=list(client.services)
                if not services:raise RuntimeError("servicios GATT vacíos")
                service_ids={str(svc.uuid).lower() for svc in services}
                char_ids=set()
                for svc in services:
                    for ch in svc.characteristics:char_ids.add(str(ch.uuid).lower())
                b001="0000b001-0000-1000-8000-00805f9b34fb"
                b002="0000b002-0000-1000-8000-00805f9b34fb"
                if b001 not in char_ids or b002 not in char_ids:
                    raise RuntimeError("dispositivo BLE descartado: no expone B001+B002 de UtraWatch")
                keep=True
                if entry is not None:self.selected=entry
                elif not isinstance(target,str) and self.selected is not None:self.selected["device"]=target
                self.connection_state.update({"connected":True,"phase":"gatt_ready","strategy":label,
                                              "service_ids":sorted(service_ids)})
                progress(label+f" · UTRAWATCH GATT OK · servicios={len(services)} · MTU={getattr(client,'mtu_size','?')}")
                return client
            except asyncio.CancelledError:raise
            except Exception as ex:
                last=ex;progress(label+" · FALLÓ · "+type(ex).__name__+": "+str(ex));return None
            finally:
                if client is not None and not keep:
                    try:
                        if client.is_connected:await asyncio.wait_for(client.disconnect(),timeout=5)
                    except Exception:pass

        selected=self.selected or {}
        selected_score=watch_score(selected) if selected else 0

        # Never spend a minute trying to connect to a random BLE peripheral.
        if selected_score<=0:
            if selected:
                progress("AUTO-ID · selección actual NO es el reloj ("+
                         str(selected.get("name"))+" · "+str(selected.get("address"))+"); se ignora.")
            selected=await discover_watch(12)
            if selected is None:
                raise RuntimeError("No apareció ningún dispositivo con firma UtraWatch E91A/3802. Encendé la pantalla del reloj y reintentá.")
        else:
            progress("AUTO-ID · selección compatible con UtraWatch · score="+str(selected_score))

        address=selected.get("address") or getattr(selected.get("device"),"address",None)
        device=selected.get("device")
        if not address:raise RuntimeError("El reloj identificado no tiene dirección BLE utilizable.")

        # Fast path: current BLEDevice from the fresh scan.
        direct=[]
        if device is not None:
            direct.extend([("RELOJ DEVICE + CACHE OFF",device,False),
                           ("RELOJ DEVICE + CACHE ON",device,True)])
        direct.append(("RELOJ ADDRESS + CACHE OFF",address,False))

        for label,target,use_cache in direct:
            client=await try_target(label,target,use_cache,selected)
            if client is not None:return client,attempt_no
            await asyncio.sleep(1.5)

        # Address may rotate after pairing with the phone. Re-identify by protocol
        # signature instead of retrying the stale address.
        progress("RECUPERACIÓN · la dirección previa no respondió; reidentificando el reloj por firma BLE…")
        try:
            fresh=await discover_watch(15)
        except Exception as ex:
            last=ex;fresh=None
            progress("RECUPERACIÓN SCAN · "+type(ex).__name__+": "+str(ex))
        if fresh is not None:
            for label,use_cache in [("FRESH UTRAWATCH + CACHE OFF",False),
                                    ("FRESH UTRAWATCH + CACHE ON",True)]:
                client=await try_target(label,fresh.get("device") or fresh["address"],use_cache,fresh)
                if client is not None:return client,attempt_no
                await asyncio.sleep(2)

        self.connection_state.update({"connected":False,"phase":"failed"})
        raise RuntimeError("GATT UTRAWATCH NO DISPONIBLE tras auto-identificación: "+str(last))
'''
s=s[:conn_start]+new_conn+s[conn_end:]

needle='''                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
'''
replace='''                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    rep["advertisement"]={k:v for k,v in (self.selected or {}).items() if k not in ("device","_watch_score")}
                    rep["single_face_install"]["auto_watch_identity"]={
                        "name":(self.selected or {}).get("name"),
                        "address":(self.selected or {}).get("address"),
                        "service_uuids":(self.selected or {}).get("service_uuids"),
                        "service_data":(self.selected or {}).get("service_data")
                    }
'''
if needle not in s:
    raise SystemExit("V0.87: punto de conexión de ota_lab no encontrado")
s=s.replace(needle,replace,1)

s=s.replace(
    'V0.87 LISTA · 1º INSTALAR ESFERA EXACTA V0.87; 2º REVISAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Usa el protocolo OEM real de UtraWatch.',
    'V0.87 LISTA · 1º INSTALAR ESFERA EXACTA V0.87; 2º REVISAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Auto-identifica el reloj por E91A/3802 y conserva la referencia exacta.'
)
s=s.replace(
    'V0.87 · REFERENCIA EXACTA · usa la imagen aprobada como raster 240×296 en CUSTOMIZE; sin fondo OEM sustituto ni slot MARKET.',
    'V0.87 · REFERENCIA EXACTA + AUTO-ID · ignora BLE ajenos, encuentra UtraWatch por firma E91A/3802 y luego instala el raster aprobado 240×296 en CUSTOMIZE.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.87 aplicado")
