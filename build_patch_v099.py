from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
if 'APP_VERSION="0.98.0"' not in s: raise SystemExit("V0.99 requiere V0.98")
s=s.replace('APP_VERSION="0.98.0"','APP_VERSION="0.99.0"',1).replace('V0.98','V0.99')

start=s.index("    async def connect_retry(")
end=s.index("\n    def diagnose(",start)
new='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        self.connection_state={"connected":False,"attempts":0,"phase":"oem_exchange_gate","strategies":[],"physical_checks":[]}
        last=None; attempt_no=0
        b001="0000b001-0000-1000-8000-00805f9b34fb"; b002="0000b002-0000-1000-8000-00805f9b34fb"

        def score(x):
            sv={str(v).lower() for v in (x.get("service_uuids") or [])}; sd={str(k).lower() for k in (x.get("service_data") or {})}
            return (120 if "0000e91a-0000-1000-8000-00805f9b34fb" in sv else 0)+(110 if "00003802-0000-1000-8000-00805f9b34fb" in sv else 0)+(110 if any("3802" in k for k in sd) else 0)+(60 if (x.get("name") or "").lower()=="apple watch ultra" else 0)+(40 if str((x.get("manufacturer_data") or {}).get("255","")).lower()=="00a6" else 0)
        def row(d,a):
            return {"device":d,"name":a.local_name or d.name or "(sin nombre)","address":d.address,"rssi":a.rssi,"service_uuids":list(a.service_uuids or []),"manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},"service_data":{str(k):v.hex() for k,v in a.service_data.items()},"tx_power":a.tx_power}
        async def fresh(timeout=8):
            found=await BleakScanner.discover(timeout=timeout,return_adv=True); rows=[row(d,a) for _,(d,a) in found.items()]; rows=[x for x in rows if score(x)>0]; rows.sort(key=lambda x:(score(x),x.get("rssi") or -999),reverse=True)
            if rows:self.selected=rows[0];return rows[0]
            return None

        async def try_one(entry,label,target):
            nonlocal last,attempt_no
            attempt_no+=1; self.connection_state["attempts"]=attempt_no; self.connection_state["strategies"].append(label); progress(f"CONEXIÓN {attempt_no} · {label}")
            c=None;keep=False;events=[]
            try:
                kw={"timeout":20};
                if sys.platform=="win32":kw["winrt"]={"use_cached_services":True}
                c=BleakClient(target,**kw); await asyncio.wait_for(c.connect(),timeout=28)
                c1=c.services.get_characteristic(b001); c2=c.services.get_characteristic(b002)
                if not c.is_connected or c1 is None or c2 is None: raise RuntimeError("GATT cacheado incompleto")
                snap={"stage":label,"b001_handle":getattr(c1,"handle",None),"b002_handle":getattr(c2,"handle",None),"mtu":getattr(c,"mtu_size",None),"notify":False,"device_info_tx":False,"device_info_rx":[]}
                progress(label+" · B001="+str(snap["b001_handle"])+" · B002="+str(snap["b002_handle"])+" · MTU="+str(snap["mtu"]))
                def rx(sender,data):
                    b=bytes(data);events.append(b);progress("B001 GATE RX · "+b.hex())
                # V0.98 used an invalid one-byte payload (00). The OEM transport is 20-byte framed.
                # Reproduce the historically proven order: B001 notify first, then a valid DEVICE_INFO request.
                await asyncio.wait_for(c.start_notify(c1,rx),timeout=8); snap["notify"]=True
                await asyncio.sleep(.25)
                req=bytearray(20);req[0]=0;req[1]=0;req[2]=0;req[3]=0;req[4]=3;req[5]=0x02
                progress(label+" · OEM PHYSICAL GATE · DEVICE_INFO 0x02 · "+bytes(req).hex())
                await asyncio.wait_for(c.write_gatt_char(c2,bytes(req),response=False),timeout=6);snap["device_info_tx"]=True
                for _ in range(20):
                    if events:break
                    await asyncio.sleep(.1)
                snap["device_info_rx"]=[x.hex() for x in events];self.connection_state["physical_checks"].append(snap)
                if not events:raise RuntimeError("DEVICE_INFO fue escrito pero B001 no devolvió tráfico OEM")
                keep=True;self.selected=entry;self.connection_state.update({"connected":True,"phase":"physical_ready","strategy":label,"address":entry.get("address"),"name":entry.get("name"),"oem_exchange_verified":True})
                progress(label+" · ENLACE FÍSICO CONFIRMADO · TX/RX OEM REAL")
                # ota_lab installs its own callback; remove only this temporary gate subscription.
                try:await c.stop_notify(c1)
                except Exception:pass
                return c
            except Exception as ex:
                last=ex;self.connection_state["physical_checks"].append({"stage":label,"ready":False,"error":type(ex).__name__+": "+str(ex)});progress(label+" · FALLÓ · "+type(ex).__name__+": "+str(ex));return None
            finally:
                if c is not None and not keep:
                    try:
                        if c.is_connected:await asyncio.wait_for(c.disconnect(),timeout=5)
                    except Exception:pass

        # Fresh BLEDevice first. Historical V0.64-V0.68 sessions used the scan-derived object and
        # then B001 notify -> valid 20-byte OEM request; V0.99 restores that exact transport shape.
        progress("RUTA 1 · ANUNCIO FRESCO + CACHE ON + B001 NOTIFY + DEVICE_INFO OEM.")
        for n in range(3):
            e=await fresh(8)
            if e and e.get("device") is not None:
                progress("AUTO-ID · "+e["name"]+" · "+e["address"]+" · RSSI="+str(e.get("rssi"))+" · score="+str(score(e)))
                c=await try_one(e,"FRESH OEM EXCHANGE "+str(n+1),e["device"])
                if c is not None:return c,attempt_no
            await asyncio.sleep(1.5)
        self.connection_state.update({"connected":False,"phase":"failed"})
        raise RuntimeError("El reloj anuncia, pero Windows no completó un intercambio OEM DEVICE_INFO real (B001 notify + B002 frame 0x02). Último error: "+str(last))
'''
s=s[:start]+new+s[end:]
s=s.replace('V0.99 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.99; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Recupera DIRECT CACHE ON y exige tráfico ATT real en B002.','V0.99 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V0.99; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Valida enlace con B001 notify + DEVICE_INFO OEM real.')
s=s.replace('V0.99 · ATT PHYSICAL GATE · V0.97 confirmó que UNCACHED dirigido se atasca; vuelve a la ruta CACHE ON que sí abrió GATT históricamente, pero sólo acepta conexión después de una escritura ATT real en B002.','V0.99 · OEM EXCHANGE GATE · corrige V0.98: elimina el payload inválido de 1 byte y restaura la secuencia histórica B001 notify → frame OEM DEVICE_INFO 0x02 de 20 bytes → respuesta B001.')
p.write_text(s,encoding="utf-8")
print("overlay V0.99 aplicado")
