from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.55.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.55")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.55 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="ANALIZAR FORMATO WF V0.55")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("ANÁLISIS V0.55 NO INICIADO · Bluetooth ocupado.")
                return
            append("V0.55 · FORMATO WF · confirma DEVICE_INFO, descarga varios diales OEM 240×296 y desarma su cabecera, tabla de elementos de 20 bytes y offsets de recursos. NO escribe 0x83.")
            rep=self.base_report()
            rep["wf_format_analysis"]={
                "phase":"identity",
                "protocol":"WTWD/ApWatch",
                "device_info":None,
                "firmware_signature":None,
                "catalog_watch_id":102,
                "catalog_entries":[],
                "files":[],
                "cross_file":{},
                "dial_sync_0x83_writes":0,
                "destructive_actions":0
            }
            t0=time.monotonic()

            def emit(message):
                line=f"+{time.monotonic()-t0:06.2f}s · {message}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def u16(data,off):
                return int.from_bytes(data[off:off+2],"little") if off+2<=len(data) else None

            def u32(data,off):
                return int.from_bytes(data[off:off+4],"little") if off+4<=len(data) else None

            def build_request(pid,opcode):
                pkt=bytearray(20)
                pkt[0]=0; pkt[1]=pid&0xff; pkt[2]=0; pkt[3]=0; pkt[4]=3; pkt[5]=opcode&0xff
                return bytes(pkt)

            def parse_device_frames(frames):
                for idx,b in enumerate(frames):
                    if len(b)>=20 and b[0]==0 and b[5]==0x02:
                        plen=b[8] | (b[9]<<8)
                        if plen<6: continue
                        payload=bytearray(b[10:20])
                        remaining=max(0,plen-len(payload))
                        j=idx+1
                        while remaining>0 and j<len(frames):
                            c=frames[j]
                            if not c or c[0]==0: break
                            take=min(19,remaining,len(c)-1)
                            payload.extend(c[1:1+take]); remaining-=take; j+=1
                        q=bytes(payload[:plen])
                        if len(q)>=6:
                            result={"id_total":q[0],"customer_id":q[1],"hardware_id":q[2],"code_id":q[3],"picture_id":q[4],"font_id":q[5],"payload_hex":q.hex()}
                            if len(q)>=12:
                                result["mac_from_payload"]=":".join(f"{x:02X}" for x in reversed(q[6:12]))
                            return result
                return None

            def http_json(url):
                req=urllib.request.Request(url,headers={
                    "Accept":"application/json,text/plain,*/*",
                    "User-Agent":"RelojLab/0.55 Windows; WF format research"
                })
                with urllib.request.urlopen(req,timeout=10) as r:
                    raw=r.read(2*1024*1024)
                return json.loads(raw.decode("utf-8","replace"))

            def download_bytes(url,max_bytes=32*1024*1024):
                req=urllib.request.Request(url,headers={"Accept":"*/*","User-Agent":"RelojLab/0.55 Windows"})
                with urllib.request.urlopen(req,timeout=15) as r:
                    data=r.read(max_bytes+1)
                if len(data)>max_bytes:
                    raise RuntimeError("archivo supera límite seguro")
                return data

            def classify_signature(chunk):
                if chunk.startswith(b"\\x89PNG\\r\\n\\x1a\\n"): return "png"
                if chunk.startswith(b"\\xff\\xd8\\xff"): return "jpeg"
                if chunk.startswith(b"GIF87a") or chunk.startswith(b"GIF89a"): return "gif"
                if chunk.startswith(b"BM"): return "bmp"
                if chunk.startswith(b"RIFF"): return "riff"
                if chunk.startswith(b"\\x1f\\x8b"): return "gzip"
                if len(chunk)>=2 and chunk[0]==0x78 and chunk[1] in (0x01,0x5e,0x9c,0xda): return "zlib"
                if chunk.startswith(b"WF"): return "wf"
                return "unknown"

            def ascii_runs(data,min_len=5,max_items=30):
                out=[]; start=None
                for i,bv in enumerate(data):
                    printable=32<=bv<=126
                    if printable and start is None:start=i
                    if (not printable or i==len(data)-1) and start is not None:
                        end=i if not printable else i+1
                        if end-start>=min_len:
                            s=data[start:end].decode("ascii","replace")
                            out.append({"offset":start,"text":s[:120]})
                            if len(out)>=max_items:return out
                        start=None
                return out

            def parse_png_size(data):
                if len(data)>=24 and data.startswith(b"\\x89PNG\\r\\n\\x1a\\n") and data[12:16]==b"IHDR":
                    return [int.from_bytes(data[16:20],"big"),int.from_bytes(data[20:24],"big")]
                return None

            def parse_wf(data,url,name):
                info={
                    "name":name,"url":url,"size":len(data),
                    "sha256":hashlib.sha256(data).hexdigest(),
                    "magic":data[:2].decode("ascii","replace") if len(data)>=2 else "",
                    "version_le":u16(data,2),
                    "first_128_hex":data[:128].hex()
                }
                if len(data)<54 or data[:2]!=b"WF":
                    info["valid_wf"]=False
                    return info
                info["valid_wf"]=True
                width=u16(data,0x28); height=u16(data,0x2a); count=u16(data,0x2c)
                declared=u32(data,0x2e); resource_rel=u32(data,0x32)
                desc_start=0x36
                desc_size=20
                desc_end=desc_start+(count or 0)*desc_size
                resource_abs=(resource_rel+2) if resource_rel is not None else None
                info.update({
                    "width":width,"height":height,"element_count":count,
                    "declared_size":declared,
                    "declared_size_matches":declared==len(data),
                    "resource_base_stored":resource_rel,
                    "resource_base_absolute":resource_abs,
                    "descriptor_start":desc_start,
                    "descriptor_size":desc_size,
                    "descriptor_end":desc_end,
                    "resource_base_matches_descriptor_end":resource_abs==desc_end
                })
                descriptors=[]
                for i in range(count or 0):
                    off=desc_start+i*desc_size
                    raw=data[off:off+desc_size]
                    if len(raw)<desc_size:break
                    stored=u32(raw,16)
                    abs_off=(stored+2) if stored is not None and stored>0 else None
                    descriptors.append({
                        "index":i,"offset":off,"raw_hex":raw.hex(),
                        "kind":raw[0],"subtype":raw[1],
                        "value":u16(raw,2),"x":u16(raw,4),"y":u16(raw,6),
                        "field8":u16(raw,8),"field10":u16(raw,10),
                        "field12":u16(raw,12),"field14":u16(raw,14),
                        "resource_offset_stored":stored,
                        "resource_offset_absolute":abs_off,
                        "resource_in_file":bool(abs_off is not None and 0<=abs_off<len(data))
                    })
                info["descriptors"]=descriptors
                valid_offsets=sorted(set(
                    d["resource_offset_absolute"] for d in descriptors
                    if d.get("resource_offset_absolute") is not None and
                       resource_abs is not None and
                       resource_abs<=d["resource_offset_absolute"]<len(data)
                ))
                resources=[]
                for idx,off in enumerate(valid_offsets):
                    end=valid_offsets[idx+1] if idx+1<len(valid_offsets) else len(data)
                    if end<off:continue
                    chunk=data[off:end]
                    resources.append({
                        "offset":off,"length":len(chunk),
                        "signature":classify_signature(chunk),
                        "first_64_hex":chunk[:64].hex(),
                        "png_size":parse_png_size(chunk),
                        "png_inside":chunk.find(b"\\x89PNG\\r\\n\\x1a\\n"),
                        "jpeg_inside":chunk.find(b"\\xff\\xd8\\xff"),
                        "zlib_header_inside":min([x for x in [chunk.find(b"\\x78\\x01"),chunk.find(b"\\x78\\x9c"),chunk.find(b"\\x78\\xda")] if x>=0],default=-1)
                    })
                info["resources"]=resources
                info["resource_count_unique"]=len(resources)
                info["file_signatures"]={
                    "png_count":data.count(b"\\x89PNG\\r\\n\\x1a\\n"),
                    "jpeg_count":data.count(b"\\xff\\xd8\\xff"),
                    "gzip_count":data.count(b"\\x1f\\x8b"),
                    "zlib_7801_count":data.count(b"\\x78\\x01"),
                    "zlib_789c_count":data.count(b"\\x78\\x9c"),
                    "zlib_78da_count":data.count(b"\\x78\\xda")
                }
                info["ascii_runs"]=ascii_runs(data[:min(len(data),4096)])
                info["kind_counts"]={}
                info["kind_subtype_counts"]={}
                for d in descriptors:
                    k=str(d["kind"]); ks=f"{d['kind']:02X}:{d['subtype']:02X}"
                    info["kind_counts"][k]=info["kind_counts"].get(k,0)+1
                    info["kind_subtype_counts"][ks]=info["kind_subtype_counts"].get(ks,0)+1
                return info

            async def work():
                c=None; frames=[]
                try:
                    emit("1/9 · Confirmando identidad del reloj…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"
                    def rx(sender,data):
                        b=bytes(data);frames.append(b);emit("B001 RX · "+b.hex())
                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.3)
                    pkt=build_request(0,0x02)
                    emit("2/9 · TX DEVICE_INFO 0x02 · "+pkt.hex())
                    await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5)
                    await asyncio.sleep(4)
                    dev=parse_device_frames(frames)
                    if not dev:raise RuntimeError("DEVICE_INFO incompleto")
                    rep["wf_format_analysis"]["device_info"]=dev
                    rep["wf_format_analysis"]["firmware_signature"]=f"{dev['customer_id']}.{dev['hardware_id']:02d}.{dev['code_id']}.{dev['picture_id']}.{dev['font_id']}"
                    emit("IDENTIDAD · "+str(dev))
                    try:await c.stop_notify(b001)
                    except Exception:pass
                    await asyncio.wait_for(c.disconnect(),timeout=5);c=None

                    emit("3/9 · Descargando catálogo OEM público watchId=102…")
                    cat_url="https://wr.watchhealth.com.cn/app-halfwit/app-dial/getDialList?currentPage=1&pageSize=20&watchId=102"
                    catalog=await asyncio.to_thread(http_json,cat_url)
                    entries=catalog.get("data") if isinstance(catalog,dict) else None
                    if not isinstance(entries,list) or not entries:
                        raise RuntimeError("catálogo OEM no devolvió diales")
                    chosen=[]
                    for e in entries:
                        if not isinstance(e,dict):continue
                        if str(e.get("resolution",""))!="240*296":continue
                        url=e.get("dialFile")
                        if not isinstance(url,str) or not url.lower().startswith("http"):continue
                        chosen.append({
                            "id":e.get("id"),"dialId":e.get("dialId"),"dialName":e.get("dialName"),
                            "resolution":e.get("resolution"),"watchIds":e.get("watchIds"),
                            "dialFile":url,"previewImg":e.get("previewImg")
                        })
                        if len(chosen)>=6:break
                    rep["wf_format_analysis"]["catalog_entries"]=chosen
                    emit("CATÁLOGO · diales 240×296 seleccionados="+str(len(chosen)))
                    if len(chosen)<3:raise RuntimeError("menos de 3 diales WF candidatos")

                    folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v055")
                    os.makedirs(folder,exist_ok=True)
                    rep["wf_format_analysis"]["output_folder"]=folder
                    emit("4/9 · Descargando y parseando "+str(len(chosen))+" archivos WF…")

                    for idx,e in enumerate(chosen,1):
                        emit(f"WF {idx}/{len(chosen)} · {e.get('dialId')} · descargando .bin")
                        data=await asyncio.to_thread(download_bytes,e["dialFile"])
                        fname=e["dialFile"].split("?",1)[0].rstrip("/").split("/")[-1]
                        if not fname:fname="dial-"+str(idx)+".bin"
                        path=os.path.join(folder,fname)
                        with open(path,"wb") as fh:fh.write(data)
                        info=parse_wf(data,e["dialFile"],fname)
                        info["dial_id"]=e.get("dialId")
                        info["watch_ids"]=e.get("watchIds")
                        info["local_path"]=path

                        preview=e.get("previewImg")
                        if isinstance(preview,str) and preview.startswith("http"):
                            try:
                                pdata=await asyncio.to_thread(download_bytes,preview,8*1024*1024)
                                pext=".png" if pdata.startswith(b"\\x89PNG") else ".img"
                                ppath=os.path.join(folder,os.path.splitext(fname)[0]+"-preview"+pext)
                                with open(ppath,"wb") as ph:ph.write(pdata)
                                info["preview"]={
                                    "url":preview,"path":ppath,"size":len(pdata),
                                    "sha256":hashlib.sha256(pdata).hexdigest(),
                                    "signature":classify_signature(pdata),
                                    "png_size":parse_png_size(pdata)
                                }
                            except Exception as ex:
                                info["preview_error"]=type(ex).__name__+": "+str(ex)

                        rep["wf_format_analysis"]["files"].append(info)
                        emit("  -> magic="+str(info.get("magic"))+" ver="+hex(info.get("version_le") or 0)+" res="+str(info.get("width"))+"×"+str(info.get("height"))+" elems="+str(info.get("element_count"))+" size_ok="+str(info.get("declared_size_matches"))+" table_ok="+str(info.get("resource_base_matches_descriptor_end")))

                    emit("5/9 · Comparando estructura entre archivos…")
                    files=rep["wf_format_analysis"]["files"]
                    cross={}
                    cross["all_valid_wf"]=all(x.get("valid_wf") for x in files)
                    cross["versions"]=sorted(set(x.get("version_le") for x in files if x.get("version_le") is not None))
                    cross["resolutions"]=sorted(set(f"{x.get('width')}x{x.get('height')}" for x in files))
                    cross["element_counts"]=[x.get("element_count") for x in files]
                    cross["all_declared_sizes_match"]=all(x.get("declared_size_matches") for x in files)
                    cross["all_resource_bases_match_descriptor_end"]=all(x.get("resource_base_matches_descriptor_end") for x in files)
                    all_pairs={}
                    all_kinds={}
                    for x in files:
                        for k,v in x.get("kind_subtype_counts",{}).items():all_pairs[k]=all_pairs.get(k,0)+v
                        for k,v in x.get("kind_counts",{}).items():all_kinds[k]=all_kinds.get(k,0)+v
                    cross["kind_subtype_totals"]=dict(sorted(all_pairs.items()))
                    cross["kind_totals"]=dict(sorted(all_kinds.items()))
                    # Coordinates/components present in every file are strong engine primitives.
                    sig_sets=[]
                    for x in files:
                        sig_sets.append(set((d["kind"],d["subtype"],d["value"]) for d in x.get("descriptors",[])))
                    common=set.intersection(*sig_sets) if sig_sets else set()
                    cross["common_element_signatures"]=[{"kind":a,"subtype":b,"value":c} for a,b,c in sorted(common)]
                    rep["wf_format_analysis"]["cross_file"]=cross
                    emit("  versiones="+str(cross["versions"])+" · resoluciones="+str(cross["resolutions"])+" · elementos="+str(cross["element_counts"]))
                    emit("  tabla descriptor→recursos consistente="+str(cross["all_resource_bases_match_descriptor_end"]))

                    emit("6/9 · Guardando informe estructural local…")
                    report_path=os.path.join(folder,"wf-analysis-v055.json")
                    with open(report_path,"w",encoding="utf-8") as fh:
                        json.dump(rep["wf_format_analysis"],fh,ensure_ascii=False,indent=2)
                    rep["wf_format_analysis"]["analysis_file"]=report_path

                    emit("7/9 · HALLAZGO · cabecera WF: magic(2)+version(2); resolución @0x28/0x2A; cantidad @0x2C; tamaño @0x2E; base recursos almacenada @0x32.")
                    emit("8/9 · HALLAZGO · descriptores desde 0x36, 20 bytes por elemento; offset recurso en bytes 16–19. La base/offset almacenado se valida como relativo a los 2 bytes 'WF'.")
                    rep["wf_format_analysis"]["phase"]="complete"
                    emit("9/9 · V0.55 FINALIZADA · sólo lectura BLE + descarga/análisis OEM · 0x83 NO TOCADO.")
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["wf_format_analysis"]["phase"]="error"
                    self.report=rep;self.show()
                    append("ANÁLISIS V0.55 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.55 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                wf=result.get("wf_format_analysis",{})
                cross=wf.get("cross_file",{})
                if cross.get("all_valid_wf") and cross.get("all_declared_sizes_match") and cross.get("all_resource_bases_match_descriptor_end"):
                    append("FORMATO WF ESTRUCTURALMENTE VALIDADO · siguiente versión puede mapear cada tipo/subtipo a sus widgets y recursos antes de construir nuestra esfera.")
                else:
                    append("FORMATO WF PARCIAL · revisar diferencias del diagnóstico antes de empaquetar.")
                self.status.set("V0.55 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=240),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.55 LISTA · 1º PREPARAR ESFERA ÚNICA V0.55; 2º COPIAR DIAGNÓSTICO. Desarma varios .bin WF oficiales 240×296: cabecera, elementos y recursos; 0x83 bloqueado.")'
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


# V0.55: do not depend on a second advertising cycle after the first GATT attempt.
# Reuse the BLEDevice captured by "Buscar relojes" first; fresh scanning is recovery only.
_conn_start=s.index("    async def connect_retry(")
_conn_end=s.index("\n    def diagnose(",_conn_start)
_new_connect_retry='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        selected=self.selected or {}
        address=selected.get("address") or getattr(selected.get("device"),"address",None)
        device=selected.get("device")
        if not address:raise RuntimeError("Seleccioná un reloj en Buscar relojes.")

        self.connection_state={"connected":False,"attempts":0,"phase":"starting","strategies":[]}
        last=None
        attempt_no=0

        async def try_target(label,target,use_cache):
            nonlocal last,attempt_no
            attempt_no+=1
            client=None
            keep=False
            self.connection_state["attempts"]=attempt_no
            self.connection_state["strategies"].append(label)
            progress(f"CONEXIÓN {attempt_no} · {label}")
            try:
                kwargs={"timeout":30}
                if sys.platform=="win32":
                    kwargs["winrt"]={"use_cached_services":bool(use_cache)}
                client=BleakClient(target,**kwargs)
                try:
                    await asyncio.wait_for(client.connect(),timeout=32)
                except asyncio.TimeoutError:
                    if not client.is_connected:
                        raise
                    progress(label+" · connect() agotó espera pero Windows informa enlace conectado; validando GATT…")
                if not client.is_connected:
                    raise RuntimeError("Windows no confirmó is_connected")
                try:
                    services=list(client.services)
                except Exception as ex:
                    raise RuntimeError("enlace abierto pero servicios GATT no disponibles: "+repr(ex))
                if not services:
                    raise RuntimeError("servicios GATT vacíos")
                keep=True
                self.selected["device"]=target if not isinstance(target,str) else self.selected.get("device")
                self.connection_state.update({"connected":True,"phase":"gatt_ready","strategy":label})
                progress(label+f" · GATT OK · servicios={len(services)} · MTU={getattr(client,'mtu_size','?')}")
                return client
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
                            await asyncio.wait_for(client.disconnect(),timeout=5)
                    except Exception:
                        pass

        # The scan result already contains a WinRT BLEDevice path. This is the most
        # reliable route when the watch stops advertising after a connection attempt.
        direct=[]
        if device is not None:
            direct.extend([
                ("DEVICE + CACHE OFF",device,False),
                ("DEVICE + CACHE ON",device,True),
            ])
        direct.extend([
            ("ADDRESS + CACHE OFF",address,False),
            ("ADDRESS + CACHE ON",address,True),
        ])

        for label,target,use_cache in direct:
            client=await try_target(label,target,use_cache)
            if client is not None:return client,attempt_no
            await asyncio.sleep(2.5)

        # Only now request a fresh advertisement. Failure here does not discard the
        # direct attempts above.
        progress("RECUPERACIÓN · buscando un anuncio fresco hasta 15 s…")
        fresh=None
        try:
            fresh=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=15),timeout=17)
        except Exception as ex:
            last=ex
            progress("RECUPERACIÓN SCAN · "+type(ex).__name__+": "+str(ex))
        if fresh is not None:
            self.selected["device"]=fresh
            for label,use_cache in [("FRESH DEVICE + CACHE OFF",False),("FRESH DEVICE + CACHE ON",True)]:
                client=await try_target(label,fresh,use_cache)
                if client is not None:return client,attempt_no
                await asyncio.sleep(3)

        self.connection_state.update({"connected":False,"phase":"failed"})
        raise RuntimeError("GATT NO DISPONIBLE tras rutas DEVICE/ADDRESS y recuperación: "+str(last))
'''
s=s[:_conn_start]+_new_connect_retry+s[_conn_end:]

p.write_text(s,encoding="utf-8")
print("build patch v0.55 aplicado")
