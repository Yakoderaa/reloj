from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.49.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.49")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.49 · modo esfera única · protocolo ApWatch/WTWD', 1)

old_button = '''primary_test=ttk.Button(row,text="PRUEBA V0.28 - CONEXION LIMPIA + HUELLA OAD")
        primary_test.pack(side="left",padx=4)'''
new_button = '''def copy_control_diagnostic():
            text=log.get("1.0","end-1c")
            if not text.strip():
                self.status.set("No hay diagnóstico para copiar todavía.")
                return
            try:
                w.clipboard_clear()
                w.clipboard_append(text)
                w.update_idletasks()
                self.status.set("Diagnóstico copiado al portapapeles.")
            except Exception as ex:
                messagebox.showerror("Copiar diagnóstico",repr(ex))
        primary_test=ttk.Button(row,text="PREPARAR ESFERA ÚNICA V0.49")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("PREPARACIÓN V0.49 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.49 · ESFERA ÚNICA · identifica el reloj y consulta la esfera activa con el protocolo E91A/B002→B001. Esta fase NO borra ni instala: primero obtiene los IDs exactos para no escribir un dial incompatible.")
            rep=self.base_report()
            rep["unique_face"]={
                "phase":"identity_and_dial_inventory",
                "target_design":"analógico negro; hora digital curva arriba-izquierda; batería arriba-derecha; pasos abajo-izquierda; frecuencia cardíaca abajo-derecha",
                "protocol":"WTWD/ApWatch family over E91A B002/B001",
                "requests_sent":[],
                "decoded_responses":[],
                "raw_frames":[],
                "factory_faces_deleted":False,
                "custom_face_installed":False,
                "destructive_actions":0,
            }
            t0=time.monotonic()
            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def build_request(pid,opcode,payload=b""):
                payload=bytes(payload)
                if len(payload)>10:
                    raise RuntimeError("V0.49 sólo usa consultas cortas; payload demasiado grande.")
                pkt=bytearray(20)
                pkt[0]=0x00
                pkt[1]=pid & 0xff
                pkt[2]=0x00
                pkt[3]=0x00
                pkt[4]=0x03
                pkt[5]=opcode & 0xff
                pkt[8]=len(payload) & 0xff
                pkt[9]=(len(payload)>>8) & 0xff
                pkt[10:10+len(payload)]=payload
                return bytes(pkt)

            def decode_frame(data):
                b=bytes(data)
                row={"hex":b.hex(),"length":len(b)}
                if len(b)>=10 and b[0]==0:
                    plen=b[8] | (b[9]<<8)
                    row.update({
                        "kind":"header",
                        "pid":b[1],
                        "continuations":b[2],
                        "cmd_type":b[3],
                        "send_type":b[4],
                        "opcode":b[5],
                        "payload_length":plen,
                        "payload_first_hex":b[10:10+min(plen,10)].hex(),
                    })
                    if b[5]==0x02 and plen>=6:
                        pl=b[10:16]
                        row["device_info"]={
                            "id_total":pl[0],"customer_id":pl[1],"hardware_id":pl[2],
                            "code_id":pl[3],"picture_id":pl[4],"font_id":pl[5],
                        }
                    elif b[5]==0x84:
                        row["dial_info_payload_first_hex"]=b[10:10+min(plen,10)].hex()
                elif b:
                    row.update({"kind":"continuation","index":b[0],"payload_hex":b[1:].hex()})
                return row

            async def work():
                c=None
                rx=[]
                try:
                    emit("1/7 · Conectando al reloj con sesión GATT limpia…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    expected={
                        "E91A":"0000e91a-0000-1000-8000-00805f9b34fb",
                        "B001":"0000b001-0000-1000-8000-00805f9b34fb",
                        "B002":"0000b002-0000-1000-8000-00805f9b34fb",
                        "FFC1":"f000ffc1-0451-4000-b000-000000000000",
                        "FFC2":"f000ffc2-0451-4000-b000-000000000000",
                    }
                    service_uuids={str(svc.uuid).lower() for svc in c.services}
                    char_uuids={str(ch.uuid).lower() for svc in c.services for ch in svc.characteristics}
                    present={"E91A":expected["E91A"] in service_uuids}
                    for name in ("B001","B002","FFC1","FFC2"):
                        present[name]=expected[name] in char_uuids
                    rep["unique_face"]["channels_present"]=present
                    emit("2/7 · CANALES · "+str(present))
                    if not (present["E91A"] and present["B001"] and present["B002"]):
                        raise RuntimeError("No aparece el canal E91A+B001+B002 esperado para administrar esferas.")

                    emit("3/7 · Leyendo identidad estándar 2A29/2A24/2A27/2A26/2A28…")
                    fields={
                        "manufacturer":"00002a29-0000-1000-8000-00805f9b34fb",
                        "model":"00002a24-0000-1000-8000-00805f9b34fb",
                        "hardware":"00002a27-0000-1000-8000-00805f9b34fb",
                        "firmware":"00002a26-0000-1000-8000-00805f9b34fb",
                        "software":"00002a28-0000-1000-8000-00805f9b34fb",
                    }
                    ident={}
                    for key,uuid in fields.items():
                        ch=c.services.get_characteristic(uuid)
                        if not ch or "read" not in ch.properties:
                            ident[key]=None
                            continue
                        try:
                            raw=bytes(await asyncio.wait_for(c.read_gatt_char(ch),timeout=4))
                            ident[key]={"text":raw.decode("utf-8","replace").strip("\\x00").strip(),"hex":raw.hex()}
                            emit(key+"="+repr(ident[key]["text"]))
                        except Exception as ex:
                            ident[key]={"error":repr(ex)}
                    rep["unique_face"]["identity"]=ident

                    def on_b001(sender,data):
                        row=decode_frame(data)
                        row["t"]=round(time.monotonic()-t0,3)
                        rx.append(row)
                        rep["unique_face"]["raw_frames"].append(row)
                        summary="B001 RX · "+row["hex"]
                        if row.get("opcode") is not None:
                            summary+=f" · opcode=0x{row['opcode']:02X} · send={row.get('send_type')} · len={row.get('payload_length')}"
                        if row.get("device_info"):
                            summary+=" · DEVICE_INFO="+str(row["device_info"])
                        emit(summary)

                    emit("4/7 · Suscribiendo B001…")
                    await asyncio.wait_for(c.start_notify(expected["B001"],on_b001),timeout=6)
                    await asyncio.sleep(.35)

                    requests=[("DEVICE_INFO 0x02",0x02), ("DIAL_INFO 0x84",0x84)]
                    pid=0
                    for label,opcode in requests:
                        pkt=build_request(pid,opcode)
                        rep["unique_face"]["requests_sent"].append({"label":label,"opcode":opcode,"hex":pkt.hex()})
                        emit("5/7 · TX "+label+" · "+pkt.hex())
                        await asyncio.wait_for(c.write_gatt_char(expected["B002"],pkt,response=False),timeout=5)
                        pid=(pid+1)&0xff
                        await asyncio.sleep(2.2)

                    emit("6/7 · Esperando respuestas/fragmentos finales…")
                    await asyncio.sleep(3.5)
                    try: await c.stop_notify(expected["B001"])
                    except Exception: pass

                    dev=None; dial_rows=[]
                    for row in rx:
                        if row.get("device_info"): dev=row["device_info"]
                        if row.get("opcode")==0x84: dial_rows.append(row)
                    rep["unique_face"]["device_info"]=dev
                    rep["unique_face"]["dial_info_frames"]=dial_rows
                    rep["unique_face"]["ready_for_packaging"]=bool(dev and dial_rows)
                    if dev:
                        emit("DEVICE IDs · customer="+str(dev["customer_id"])+" hardware="+str(dev["hardware_id"])+" code="+str(dev["code_id"])+" picture="+str(dev["picture_id"])+" font="+str(dev["font_id"]))
                    else:
                        emit("DEVICE_INFO 0x02 no devolvió los 6 IDs esperados.")
                    if dial_rows:
                        emit("DIAL_INFO 0x84 respondió · "+str(len(dial_rows))+" frame(s).")
                    else:
                        emit("DIAL_INFO 0x84 no respondió en esta sesión; necesito este dato antes de empaquetar/escribir una esfera.")
                    emit("7/7 · PREPARACIÓN V0.49 FINALIZADA · no se borró ni instaló ninguna esfera en esta fase.")
                    return rep
                finally:
                    if c:
                        try: await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex: rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["unique_face"]["phase"]="error"
                    self.report=rep
                    self.show()
                    append("PREPARACIÓN V0.49 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.49 terminó con error. Copiá el diagnóstico.")
                    return
                self.report=result
                self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                if result.get("unique_face",{}).get("ready_for_packaging"):
                    append("LISTO PARA SIGUIENTE PASO · ya tengo IDs de hardware + respuesta DIAL_INFO para construir el paquete de tu esfera sin adivinar.")
                else:
                    append("FALTA UNA RESPUESTA · copiá este diagnóstico tal cual para ajustar la consulta en la siguiente versión.")
                self.status.set("V0.49 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=180),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.49 LISTA · 1º PREPARAR ESFERA ÚNICA V0.49; 2º COPIAR DIAGNÓSTICO. Consulta DEVICE_INFO 0x02 y DIAL_INFO 0x84 por E91A/B002→B001 sin borrar ni instalar todavía.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)


s=s.replace("    def open_control(self):", '''    async def inspect_gatt_snapshot(self,emit):
        address=(self.selected or {}).get("address")
        if not address: raise RuntimeError("Seleccioná el reloj primero.")
        client=None
        snapshot={"services":[],"errors":[],"connected":False}
        try:
            target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=8),timeout=10)
            if target is None: raise RuntimeError("El reloj seleccionado no está visible.")
            client=BleakClient(target,timeout=15,winrt={"use_cached_services":False})
            await asyncio.wait_for(client.connect(),timeout=18)
            if not client.is_connected: raise RuntimeError("GATT no conectado")
            snapshot["connected"]=True
            present=set()
            for svc in client.services:
                entry={"uuid":svc.uuid,"characteristics":[]}
                emit("SERVICIO "+svc.uuid)
                for ch in svc.characteristics:
                    present.add(ch.uuid.lower())
                    row={"uuid":ch.uuid,"handle":ch.handle,"properties":list(ch.properties)}
                    entry["characteristics"].append(row)
                    emit("  CARACTERÍSTICA "+str(row))
                snapshot["services"].append(entry)
            expected={"B001":"0000b001-0000-1000-8000-00805f9b34fb","B002":"0000b002-0000-1000-8000-00805f9b34fb","FFC1":"f000ffc1-0451-4000-b000-000000000000","FFC2":"f000ffc2-0451-4000-b000-000000000000"}
            snapshot["present"]={name:uuid in present for name,uuid in expected.items()}
            emit("PRESENCIA "+str(snapshot["present"]))
            if not snapshot["present"]["B001"]:
                emit("B001 AUSENTE en esta enumeración. Causa pendiente; no confirma modo OTA.")
        except asyncio.CancelledError: raise
        except Exception as ex:
            snapshot["errors"].append(type(ex).__name__+": "+str(ex))
            emit("ERROR DE INSPECCIÓN · "+snapshot["errors"][-1])
        finally:
            if client is not None:
                try: await asyncio.wait_for(client.disconnect(),timeout=4)
                except Exception as ex:
                    snapshot["errors"].append("Cierre: "+repr(ex))
                    emit("ERROR DE CIERRE · "+repr(ex))
        return snapshot

    def open_control(self):''',1)

p.write_text(s,encoding="utf-8")
print("build patch v0.49 aplicado")
