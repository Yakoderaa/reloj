from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.48.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.48")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.48 · adquisición de firmware oficial', 1)

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
        primary_test=ttk.Button(row,text="BUSCAR FIRMWARE OFICIAL V0.48")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("BÚSQUEDA V0.48 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.48 · 1º identifica hardware/ROM por GATT; 2º consulta OTA oficial QWatch Pro; 3º descarga y valida el BIN. No escribe al reloj.")
            rep=self.base_report()
            rep["firmware_discovery"]={"stage":"identity","writes_performed":0,"identity":{},"queries":[],"candidate":None}
            t0=time.monotonic()
            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))
            async def read_identity():
                c=None
                identity={"address":(self.selected or {}).get("address")}
                try:
                    emit("1/4 · Conectando para leer identidad oficial del dispositivo…")
                    c,n=await self.connect_retry(4,emit)
                    identity["connection_attempts"]=n
                    fields={
                        "manufacturer":"00002a29-0000-1000-8000-00805f9b34fb",
                        "model":"00002a24-0000-1000-8000-00805f9b34fb",
                        "serial":"00002a25-0000-1000-8000-00805f9b34fb",
                        "hardware":"00002a27-0000-1000-8000-00805f9b34fb",
                        "firmware":"00002a26-0000-1000-8000-00805f9b34fb",
                        "software":"00002a28-0000-1000-8000-00805f9b34fb",
                    }
                    for key,uuid in fields.items():
                        ch=c.services.get_characteristic(uuid)
                        if not ch or "read" not in ch.properties:
                            identity[key]=None
                            emit(key+" · no disponible")
                            continue
                        data=bytes(await asyncio.wait_for(c.read_gatt_char(ch),timeout=4))
                        text=data.decode("utf-8","replace").strip("\\x00").strip()
                        identity[key]=text
                        identity[key+"_hex"]=data.hex()
                        emit(key+"="+repr(text))
                    ffc1=c.services.get_characteristic("f000ffc1-0451-4000-b000-000000000000")
                    ffc2=c.services.get_characteristic("f000ffc2-0451-4000-b000-000000000000")
                    identity["ota_channel"]={
                        "ffc1":list(ffc1.properties) if ffc1 else None,
                        "ffc2":list(ffc2.properties) if ffc2 else None,
                    }
                    emit("2/4 · Identidad leída · hardware="+repr(identity.get("hardware"))+" · firmware="+repr(identity.get("firmware")))
                    return identity
                finally:
                    if c:
                        try: await asyncio.wait_for(c.disconnect(),timeout=4)
                        except Exception as ex: emit("Cierre GATT: "+repr(ex))
            def after_identity(identity,error):
                if error:
                    rep["errors"].append(repr(error))
                    rep["firmware_discovery"]["stage"]="identity_error"
                    self.report=rep; self.show()
                    append("BÚSQUEDA V0.48 INTERRUMPIDA · "+repr(error))
                    return
                rep["firmware_discovery"]["identity"]=identity
                hw=(identity.get("hardware") or "").strip()
                fw=(identity.get("firmware") or "").strip()
                if not hw or not fw:
                    rep["errors"].append("No se pudieron leer hardware 2A27 y firmware 2A26.")
                    rep["firmware_discovery"]["stage"]="identity_incomplete"
                    self.report=rep; self.show()
                    append("No puedo consultar el OTA oficial sin 2A27/2A26. Copiá el diagnóstico.")
                    return
                rep["firmware_discovery"]["stage"]="server_lookup"
                emit("3/4 · Consultando servidores oficiales QWatch Pro con HW="+hw+" ROM="+fw+"…")
                def lookup():
                    hardcoded_token="15ef6eb5403406c1da0dc4a4defa2ea1"
                    servers=[
                        ("global","https://api1.qcwxkjvip.com/qcwx/","app-update/last-ota"),
                        ("backup","https://china.qcwxwire.com/qcwx/","app-update/last-ota/china"),
                    ]
                    queries=[]; errors=[]; candidate=None
                    mac=(identity.get("address") or "AA:BB:CC:DD:EE:FF")
                    for server_name,base,endpoint in servers:
                        token=hardcoded_token
                        try:
                            req=urllib.request.Request(base+"token/getToken?key=qcwx_android",headers={"token":hardcoded_token,"User-Agent":"QWatchPro"})
                            with urllib.request.urlopen(req,timeout=12) as response:
                                token_reply=json.loads(response.read().decode("utf-8","replace"))
                            fresh=token_reply.get("data") or token_reply.get("token")
                            if isinstance(fresh,str) and fresh.strip(): token=fresh.strip()
                        except Exception as ex:
                            errors.append(server_name+" token: "+repr(ex))
                        for mode,rom in [("current",fw),("latest","0.0.0")]:
                            payload={"appId":1,"uid":1,"hardwareVersion":hw,"romVersion":rom,"os":1,"mac":mac,"country":"AR","dev":2}
                            body=json.dumps(payload,separators=(",",":")).encode("utf-8")
                            req=urllib.request.Request(base+endpoint,data=body,headers={"Content-Type":"application/json","token":token,"User-Agent":"QWatchPro"},method="POST")
                            result=None
                            try:
                                with urllib.request.urlopen(req,timeout=18) as response:
                                    raw=response.read().decode("utf-8","replace")
                                result=json.loads(raw)
                            except Exception as ex:
                                raw=None
                                reader=getattr(ex,"read",None)
                                if callable(reader):
                                    try:
                                        raw=reader().decode("utf-8","replace")
                                        result=json.loads(raw)
                                    except Exception: pass
                                errors.append(server_name+" "+mode+": "+repr(ex))
                            safe_result=result if isinstance(result,dict) else {"raw":raw}
                            queries.append({"server":server_name,"mode":mode,"request":payload,"response":safe_result})
                            data=(result or {}).get("data") if isinstance(result,dict) else None
                            if isinstance(data,dict) and data.get("downloadUrl"):
                                candidate={"server":server_name,"mode":mode,"request":payload,"response":data}
                                break
                        if candidate: break
                    if not candidate:
                        return {"queries":queries,"errors":errors,"candidate":None}
                    data=candidate["response"]
                    url=str(data.get("downloadUrl") or "").strip()
                    if not url.lower().startswith(("http://","https://")):
                        raise RuntimeError("El servidor devolvió una URL de firmware inválida: "+url)
                    request=urllib.request.Request(url,headers={"User-Agent":"QWatchPro"})
                    firmware=bytearray()
                    with urllib.request.urlopen(request,timeout=90) as response:
                        declared=response.headers.get("Content-Length")
                        while True:
                            chunk=response.read(65536)
                            if not chunk: break
                            firmware.extend(chunk)
                            if len(firmware)>64*1024*1024:
                                raise RuntimeError("El firmware supera el límite de 64 MiB.")
                    blob=bytes(firmware)
                    if len(blob)<4096:
                        raise RuntimeError("La descarga es demasiado pequeña para ser firmware: "+str(len(blob))+" bytes")
                    lead=blob[:64].lstrip()
                    if lead.startswith(b"<") or lead.startswith(b"{") or lead.startswith(b"["):
                        raise RuntimeError("La descarga parece HTML/JSON, no un BIN.")
                    digest=hashlib.sha256(blob).hexdigest()
                    returned_hw=str(data.get("hardwareVersion") or "")
                    if returned_hw and returned_hw!=hw:
                        raise RuntimeError("El servidor devolvió firmware para otro hardware: "+returned_hw+" != "+hw)
                    def clean(value):
                        value=str(value or "unknown")
                        return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)[:80] or "unknown"
                    version=clean(data.get("version") or "unknown")
                    folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware")
                    os.makedirs(folder,exist_ok=True)
                    target=os.path.join(folder,"QWatch-"+clean(hw)+"-"+version+"-"+digest[:12]+".bin")
                    with open(target,"wb") as output: output.write(blob)
                    header_ascii="".join(chr(b) if 32<=b<127 else "." for b in blob[:160])
                    result={
                        "queries":queries,
                        "errors":errors,
                        "candidate":candidate,
                        "download":{"path":target,"size":len(blob),"sha256":digest,"first64_hex":blob[:64].hex(),"first160_ascii":header_ascii,"declared_content_length":declared},
                    }
                    with open(target+".json","w",encoding="utf-8") as meta:
                        json.dump(result,meta,ensure_ascii=False,indent=2)
                    return result
                def after_lookup(result,error):
                    if error:
                        rep["errors"].append(repr(error))
                        rep["firmware_discovery"]["stage"]="download_error"
                        self.report=rep; self.show()
                        append("BÚSQUEDA V0.48 FALLÓ · "+repr(error))
                        return
                    rep["firmware_discovery"]["queries"]=result.get("queries",[])
                    rep["firmware_discovery"]["network_errors"]=result.get("errors",[])
                    rep["firmware_discovery"]["candidate"]=result.get("candidate")
                    if result.get("candidate"):
                        rep["firmware_discovery"]["download"]=result.get("download")
                        rep["firmware_discovery"]["stage"]="firmware_saved"
                        d=result["download"]
                        append("FIRMWARE OFICIAL ENCONTRADO Y GUARDADO")
                        append("ARCHIVO: "+d["path"])
                        append("TAMAÑO: "+str(d["size"])+" bytes")
                        append("SHA-256: "+d["sha256"])
                        append("SIGUIENTE PASO: analizar su formato y recién después habilitar el flasheo.")
                        self.status.set("Firmware oficial guardado. Copiá el diagnóstico.")
                    else:
                        rep["firmware_discovery"]["stage"]="not_found"
                        append("NO APARECIÓ UN BIN PARA HW="+hw+" ROM="+fw+" en los endpoints consultados.")
                        append("Copiá el diagnóstico: las respuestas del servidor quedaron registradas para ajustar la búsqueda.")
                        self.status.set("Consulta OTA terminada sin BIN. Copiá el diagnóstico.")
                    self.report=rep; self.show()
                    append("4/4 · BÚSQUEDA V0.48 FINALIZADA · cero escrituras BLE.")
                self.run_thread(lookup,after_lookup)
            self.run_async(read_identity(),after_identity)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.48 LISTA · 1º BUSCAR FIRMWARE OFICIAL; 2º COPIAR DIAGNÓSTICO. Lee 2A27/2A26 y consulta el OTA de QWatch Pro sin escribir al reloj.")'
if old_ready not in s:
    raise SystemExit("No se encontró mensaje V0.28")
s=s.replace(old_ready,new_ready,1)

s=s.replace("    def open_control(self):", '    async def inspect_gatt_snapshot(self,emit):\n        address=(self.selected or {}).get("address")\n        if not address: raise RuntimeError("Seleccioná el reloj primero.")\n        client=None\n        snapshot={"services":[],"errors":[],"connected":False}\n        try:\n            target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=8),timeout=10)\n            if target is None: raise RuntimeError("El reloj seleccionado no está visible.")\n            client=BleakClient(target,timeout=15,winrt={"use_cached_services":False})\n            await asyncio.wait_for(client.connect(),timeout=18)\n            if not client.is_connected: raise RuntimeError("GATT no conectado")\n            snapshot["connected"]=True\n            present=set()\n            for svc in client.services:\n                entry={"uuid":svc.uuid,"characteristics":[]}\n                emit("SERVICIO "+svc.uuid)\n                for ch in svc.characteristics:\n                    present.add(ch.uuid.lower())\n                    row={"uuid":ch.uuid,"handle":ch.handle,"properties":list(ch.properties)}\n                    entry["characteristics"].append(row)\n                    emit("  CARACTERÍSTICA "+str(row))\n                snapshot["services"].append(entry)\n            expected={"B001":"0000b001-0000-1000-8000-00805f9b34fb","B002":"0000b002-0000-1000-8000-00805f9b34fb","FFC1":"f000ffc1-0451-4000-b000-000000000000","FFC2":"f000ffc2-0451-4000-b000-000000000000"}\n            snapshot["present"]={name:uuid in present for name,uuid in expected.items()}\n            emit("PRESENCIA "+str(snapshot["present"]))\n            if not snapshot["present"]["B001"]:\n                emit("B001 AUSENTE en esta enumeración. Causa pendiente; no confirma modo OTA.")\n        except asyncio.CancelledError: raise\n        except Exception as ex:\n            snapshot["errors"].append(type(ex).__name__+": "+str(ex))\n            emit("ERROR DE INSPECCIÓN · "+snapshot["errors"][-1])\n        finally:\n            if client is not None:\n                try: await asyncio.wait_for(client.disconnect(),timeout=4)\n                except Exception as ex:\n                    snapshot["errors"].append("Cierre: "+repr(ex))\n                    emit("ERROR DE CIERRE · "+repr(ex))\n        return snapshot\n' + "\n    def open_control(self):",1)
p.write_text(s,encoding="utf-8")
print("build patch v0.48 aplicado")
