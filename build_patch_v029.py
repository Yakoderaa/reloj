from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace("import urllib.request, tempfile, os, subprocess, time, hashlib, queue", "import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math", 1)

s = s.replace('APP_VERSION="0.28.0"', 'APP_VERSION="0.58.0"', 1)
s = s.replace('root.title("Reloj Lab V0.28")', 'root.title("Reloj Lab V0.58")', 1)
s = s.replace('V0.26 · enlace BLE persistente + OTA', 'V0.58 · modo esfera única · protocolo ApWatch/WTWD', 1)

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
        primary_test=ttk.Button(row,text="CONSTRUIR BLUEPRINT WF V0.58")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)'''
if old_button not in s:
    raise SystemExit("No se encontró el botón base V0.28")
s = s.replace(old_button,new_button,1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_ota = '''        def ota_lab():
            if self.ble_busy:
                append("EXTRACCIÓN V0.58 NO INICIADA · Bluetooth ocupado.")
                return
            append("V0.58 · BLUEPRINT WF · valida el formato ya descubierto, identifica reloj analógico + hora digital + widgets y genera el plano de nuestra esfera. NO escribe 0x83.")
            rep=self.base_report()
            rep["wf_resource_analysis"]={
                "phase":"identity",
                "protocol":"WTWD/ApWatch",
                "device_info":None,
                "firmware_signature":None,
                "catalog_watch_id":102,
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
                    "User-Agent":"RelojLab/0.58 Windows; WF resource research"
                })
                with urllib.request.urlopen(req,timeout=10) as r:
                    raw=r.read(2*1024*1024)
                return json.loads(raw.decode("utf-8","replace"))

            def download_bytes(url,max_bytes=32*1024*1024):
                req=urllib.request.Request(url,headers={"Accept":"*/*","User-Agent":"RelojLab/0.58 Windows"})
                with urllib.request.urlopen(req,timeout=18) as r:
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
                return "unknown"

            def parse_png_size(data):
                if len(data)>=24 and data.startswith(b"\\x89PNG\\r\\n\\x1a\\n") and data[12:16]==b"IHDR":
                    return [int.from_bytes(data[16:20],"big"),int.from_bytes(data[20:24],"big")]
                return None

            def parse_jpeg_size(data):
                if len(data)<4 or not data.startswith(b"\\xff\\xd8"): return None
                i=2
                while i+9<len(data):
                    if data[i]!=0xff:
                        i+=1; continue
                    marker=data[i+1]
                    i+=2
                    if marker in (0xd8,0xd9): continue
                    if i+2>len(data): break
                    seg=int.from_bytes(data[i:i+2],"big")
                    if seg<2 or i+seg>len(data): break
                    if marker in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf) and seg>=7:
                        return [int.from_bytes(data[i+5:i+7],"big"),int.from_bytes(data[i+3:i+5],"big")]
                    i+=seg
                return None

            def entropy(data):
                if not data:return 0.0
                try:
                    counts=[0]*256
                    for x in data:counts[x]+=1
                    n=len(data);e=0.0
                    for c in counts:
                        if c:
                            q=c/n;e-=q*math.log2(q)
                    return round(e,4)
                except Exception as ex:
                    return None

            def extract_embedded_images(data,folder,prefix):
                found=[]
                # PNG
                pos=0
                while True:
                    pos=data.find(b"\\x89PNG\\r\\n\\x1a\\n",pos)
                    if pos<0:break
                    end=data.find(b"IEND",pos+8)
                    if end>=0 and end+8<=len(data):
                        end=end+8
                        raw=data[pos:end]
                        path=os.path.join(folder,f"{prefix}-embedded-{len(found):02d}.png")
                        with open(path,"wb") as fh:fh.write(raw)
                        found.append({"offset":pos,"end":end,"length":len(raw),"type":"png","size":parse_png_size(raw),"path":path})
                        pos=end
                    else:
                        pos+=8
                # JPEG
                pos=0
                while True:
                    pos=data.find(b"\\xff\\xd8\\xff",pos)
                    if pos<0:break
                    end=data.find(b"\\xff\\xd9",pos+3)
                    if end>=0:
                        end+=2
                        raw=data[pos:end]
                        path=os.path.join(folder,f"{prefix}-embedded-{len(found):02d}.jpg")
                        with open(path,"wb") as fh:fh.write(raw)
                        found.append({"offset":pos,"end":end,"length":len(raw),"type":"jpeg","size":parse_jpeg_size(raw),"path":path})
                        pos=end
                    else:
                        pos+=3
                return found

            def role_hint(type_code,fields):
                # V0.58: roles supported by repeated geometry/frame-count evidence.
                if type_code==0x0501 and fields["x"]==120 and fields["y"]==148:
                    return "analog_hand_A"
                if type_code==0x0601 and fields["x"]==120 and fields["y"]==148:
                    return "analog_hand_B"
                if type_code==0x0701 and fields["x"]==120 and fields["y"]==148:
                    return "analog_hand_C"
                if type_code==0x0804 and fields["frame_count_like"]==10:
                    return "time_digit_1"
                if type_code==0x0904 and fields["frame_count_like"]==10:
                    return "time_digit_2"
                if type_code==0x0A04 and fields["frame_count_like"]==10:
                    return "time_digit_3"
                if type_code==0x0B04 and fields["frame_count_like"]==10:
                    return "time_digit_4"
                if type_code==0x1002:
                    return "time_separator_or_static_layer"
                if type_code==0x0105 and fields["width_like"] in range(16,81) and fields["height_like"] in range(16,81):
                    return "dynamic_widget_slot"
                if type_code==0x0304 and fields["frame_count_like"]==10:
                    return "upper_numeric_10_state"
                if type_code==0x0404 and fields["frame_count_like"]==7:
                    return "upper_categorical_7_state"
                if type_code==0x1102:
                    return "base_image_layer"
                return None

            def parse_wf(data,url,name,folder):
                info={
                    "name":name,"url":url,"size":len(data),
                    "sha256":hashlib.sha256(data).hexdigest(),
                    "magic":data[:2].decode("ascii","replace") if len(data)>=2 else "",
                    "version_le":u16(data,2),
                    "first_96_hex":data[:96].hex()
                }
                if len(data)<54 or data[:2]!=b"WF":
                    info["valid_wf"]=False
                    return info
                info["valid_wf"]=True

                # V0.55 proved the whole header map was shifted by two bytes.
                # Correct layout:
                # 0x2A width, 0x2C height, 0x2E element count,
                # 0x30 declared file size, 0x34 resource-table base stored relative to byte 2.
                width=u16(data,0x2a)
                height=u16(data,0x2c)
                count=u16(data,0x2e)
                declared=u32(data,0x30)
                resource_rel=u32(data,0x34)
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
                pointers=[]
                for i in range(count or 0):
                    off=desc_start+i*desc_size
                    raw=data[off:off+desc_size]
                    if len(raw)<desc_size:break
                    fields={
                        "mode":u16(raw,0),
                        "type_code":u16(raw,2),
                        "frame_count_like":u16(raw,4),
                        "x":u16(raw,6),
                        "y":u16(raw,8),
                        "width_like":u16(raw,10),
                        "height_like":u16(raw,12),
                        "arg2":u16(raw,14),
                        "arg3":u16(raw,16),
                        "resource_offset_stored":u16(raw,18)
                    }
                    ptr=fields["resource_offset_stored"]
                    abs_off=(ptr+2) if ptr is not None else None
                    fields["resource_offset_absolute"]=abs_off
                    fields["resource_in_file"]=bool(abs_off is not None and resource_abs is not None and resource_abs<=abs_off<len(data))
                    fields["role_hint"]=role_hint(fields["type_code"],fields)
                    d={"index":i,"offset":off,"raw_hex":raw.hex(),**fields}
                    descriptors.append(d)
                    if d["resource_in_file"]:pointers.append(abs_off)
                info["descriptors"]=descriptors

                unique=sorted(set(pointers))
                info["resource_pointer_count"]=len(unique)
                info["all_descriptor_pointers_valid"]=all(d["resource_in_file"] for d in descriptors)

                resources=[]
                dial_dir=os.path.join(folder,os.path.splitext(name)[0])
                os.makedirs(dial_dir,exist_ok=True)
                starts=unique
                for idx,off in enumerate(starts):
                    end=starts[idx+1] if idx+1<len(starts) else len(data)
                    if end<=off:continue
                    chunk=data[off:end]
                    rpath=os.path.join(dial_dir,f"resource-{idx:02d}-off-{off}.bin")
                    with open(rpath,"wb") as fh:fh.write(chunk)
                    nearby=data[max(0,off-16):min(len(data),off+80)]
                    resources.append({
                        "index":idx,"offset":off,"end":end,"length":len(chunk),
                        "signature":classify_signature(chunk),
                        "first_64_hex":chunk[:64].hex(),
                        "nearby_hex":nearby.hex(),
                        "entropy":entropy(chunk[:min(len(chunk),65536)]),
                        "png_size":parse_png_size(chunk),
                        "jpeg_size":parse_jpeg_size(chunk),
                        "png_inside":chunk.find(b"\\x89PNG\\r\\n\\x1a\\n"),
                        "jpeg_inside":chunk.find(b"\\xff\\xd8\\xff"),
                        "zlib_inside":min([x for x in [chunk.find(b"\\x78\\x01"),chunk.find(b"\\x78\\x9c"),chunk.find(b"\\x78\\xda")] if x>=0],default=-1),
                        "path":rpath,
                        "referenced_by":[d["index"] for d in descriptors if d["resource_offset_absolute"]==off],
                        "type_codes":[d["type_code"] for d in descriptors if d["resource_offset_absolute"]==off]
                    })
                info["resources"]=resources

                # Bytes between descriptor table and first pointed resource are also meaningful.
                first_ptr=unique[0] if unique else len(data)
                if resource_abs is not None and resource_abs<first_ptr:
                    prefix=data[resource_abs:first_ptr]
                    ppath=os.path.join(dial_dir,f"resource-prefix-{resource_abs}-{first_ptr}.bin")
                    with open(ppath,"wb") as fh:fh.write(prefix)
                    info["resource_prefix"]={
                        "offset":resource_abs,"end":first_ptr,"length":len(prefix),
                        "signature":classify_signature(prefix),
                        "entropy":entropy(prefix[:min(len(prefix),65536)]),
                        "first_64_hex":prefix[:64].hex(),
                        "path":ppath
                    }

                info["embedded_images"]=extract_embedded_images(data,dial_dir,"dial")
                info["file_signatures"]={
                    "png_count":data.count(b"\\x89PNG\\r\\n\\x1a\\n"),
                    "jpeg_count":data.count(b"\\xff\\xd8\\xff"),
                    "gzip_count":data.count(b"\\x1f\\x8b"),
                    "zlib_7801_count":data.count(b"\\x78\\x01"),
                    "zlib_789c_count":data.count(b"\\x78\\x9c"),
                    "zlib_78da_count":data.count(b"\\x78\\xda")
                }
                return info

            async def work():
                c=None;frames=[]
                try:
                    emit("1/10 · Confirmando identidad del reloj…")
                    c,n=await self.connect_retry(5,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"
                    def rx(sender,data):
                        b=bytes(data);frames.append(b);emit("B001 RX · "+b.hex())
                    await asyncio.wait_for(c.start_notify(b001,rx),timeout=6)
                    await asyncio.sleep(.3)
                    pkt=build_request(0,0x02)
                    emit("2/10 · TX DEVICE_INFO 0x02 · "+pkt.hex())
                    await asyncio.wait_for(c.write_gatt_char(b002,pkt,response=False),timeout=5)
                    await asyncio.sleep(4)
                    dev=parse_device_frames(frames)
                    if not dev:raise RuntimeError("DEVICE_INFO incompleto")
                    rep["wf_resource_analysis"]["device_info"]=dev
                    rep["wf_resource_analysis"]["firmware_signature"]=f"{dev['customer_id']}.{dev['hardware_id']:02d}.{dev['code_id']}.{dev['picture_id']}.{dev['font_id']}"
                    emit("IDENTIDAD · "+str(dev))
                    try:await c.stop_notify(b001)
                    except Exception:pass
                    await asyncio.wait_for(c.disconnect(),timeout=5);c=None

                    emit("3/10 · Descargando catálogo OEM 240×296…")
                    cat_url="https://wr.watchhealth.com.cn/app-halfwit/app-dial/getDialList?currentPage=1&pageSize=20&watchId=102"
                    catalog=await asyncio.to_thread(http_json,cat_url)
                    entries=catalog.get("data") if isinstance(catalog,dict) else None
                    if not isinstance(entries,list) or not entries:raise RuntimeError("catálogo OEM vacío")
                    chosen=[]
                    for e in entries:
                        if not isinstance(e,dict) or str(e.get("resolution",""))!="240*296":continue
                        url=e.get("dialFile")
                        if not isinstance(url,str) or not url.startswith("http"):continue
                        chosen.append({
                            "dialId":e.get("dialId"),"dialName":e.get("dialName"),"resolution":e.get("resolution"),
                            "watchIds":e.get("watchIds"),"dialFile":url,"previewImg":e.get("previewImg")
                        })
                        if len(chosen)>=6:break
                    if len(chosen)<3:raise RuntimeError("menos de 3 diales compatibles")
                    emit("CATÁLOGO · candidatos="+str(len(chosen)))

                    folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v058")
                    os.makedirs(folder,exist_ok=True)
                    rep["wf_resource_analysis"]["output_folder"]=folder

                    emit("4/10 · Descargando y extrayendo recursos de "+str(len(chosen))+" diales…")
                    for idx,e in enumerate(chosen,1):
                        emit(f"WF {idx}/{len(chosen)} · {e.get('dialId')} · descarga")
                        data=await asyncio.to_thread(download_bytes,e["dialFile"])
                        fname=e["dialFile"].split("?",1)[0].rstrip("/").split("/")[-1] or f"dial-{idx}.bin"
                        with open(os.path.join(folder,fname),"wb") as fh:fh.write(data)
                        info=parse_wf(data,e["dialFile"],fname,folder)
                        info["dial_id"]=e.get("dialId")
                        info["watch_ids"]=e.get("watchIds")

                        preview=e.get("previewImg")
                        if isinstance(preview,str) and preview.startswith("http"):
                            try:
                                pdata=await asyncio.to_thread(download_bytes,preview,8*1024*1024)
                                ppath=os.path.join(folder,os.path.splitext(fname)[0]+"-preview.png")
                                with open(ppath,"wb") as ph:ph.write(pdata)
                                info["preview"]={"path":ppath,"size":len(pdata),"png_size":parse_png_size(pdata),"sha256":hashlib.sha256(pdata).hexdigest()}
                            except Exception as ex:
                                info["preview_error"]=type(ex).__name__+": "+str(ex)

                        rep["wf_resource_analysis"]["files"].append(info)
                        emit("  -> "+str(info.get("width"))+"×"+str(info.get("height"))+
                             " · elems="+str(info.get("element_count"))+
                             " · size_ok="+str(info.get("declared_size_matches"))+
                             " · table_ok="+str(info.get("resource_base_matches_descriptor_end"))+
                             " · ptrs="+str(info.get("resource_pointer_count"))+
                             " · imágenes embebidas="+str(len(info.get("embedded_images",[]))))

                    emit("5/10 · Comparando tipos de elemento entre diales…")
                    files=rep["wf_resource_analysis"]["files"]
                    cross={
                        "all_valid_wf":all(x.get("valid_wf") for x in files),
                        "all_240x296":all(x.get("width")==240 and x.get("height")==296 for x in files),
                        "element_counts":[x.get("element_count") for x in files],
                        "all_declared_sizes_match":all(x.get("declared_size_matches") for x in files),
                        "all_resource_bases_match_descriptor_end":all(x.get("resource_base_matches_descriptor_end") for x in files),
                        "all_descriptor_pointers_valid":all(x.get("all_descriptor_pointers_valid") for x in files),
                        "type_map":{}
                    }
                    for f in files:
                        for d in f.get("descriptors",[]):
                            key=f"0x{d['type_code']:04X}"
                            row=cross["type_map"].setdefault(key,{
                                "count":0,"modes":set(),"frame_count_like":set(),"examples":[],
                                "role_hints":set(),"resource_lengths":[]
                            })
                            row["count"]+=1
                            row["modes"].add(d["mode"])
                            row["frame_count_like"].add(d["frame_count_like"])
                            if d.get("role_hint"):row["role_hints"].add(d["role_hint"])
                            if len(row["examples"])<8:
                                row["examples"].append({
                                    "dial":f.get("dial_id"),"x":d["x"],"y":d["y"],
                                    "width_like":d["width_like"],"height_like":d["height_like"],
                                    "arg2":d["arg2"],"arg3":d["arg3"],
                                    "resource_offset":d["resource_offset_absolute"]
                                })
                            for r in f.get("resources",[]):
                                if d["index"] in r.get("referenced_by",[]):
                                    row["resource_lengths"].append(r["length"])
                    for row in cross["type_map"].values():
                        row["modes"]=sorted(row["modes"])
                        row["frame_count_like"]=sorted(row["frame_count_like"])
                        row["role_hints"]=sorted(row["role_hints"])
                        row["resource_lengths"]=sorted(set(row["resource_lengths"]))
                    rep["wf_resource_analysis"]["cross_file"]=cross

                    # Build a non-destructive blueprint from the exact structures confirmed in V0.57.
                    analog_template=None
                    for f in files:
                        codes={d.get("type_code") for d in f.get("descriptors",[])}
                        if {0x0501,0x0601,0x0701}.issubset(codes):
                            analog_template=f
                            break

                    type_roles={
                        "0x0501":{"role":"analog_hand_A","confidence":"high","reason":"centered at 120,148 on analog OEM dial"},
                        "0x0601":{"role":"analog_hand_B","confidence":"high","reason":"centered at 120,148 on analog OEM dial"},
                        "0x0701":{"role":"analog_hand_C","confidence":"high","reason":"centered at 120,148 on analog OEM dial"},
                        "0x0804":{"role":"time_digit_1","confidence":"high","reason":"10-state glyph sequence in four-digit time row"},
                        "0x0904":{"role":"time_digit_2","confidence":"high","reason":"10-state glyph sequence in four-digit time row"},
                        "0x1002":{"role":"time_separator_or_static_layer","confidence":"medium","reason":"single-frame layer centered between hour/minute digit pairs"},
                        "0x0A04":{"role":"time_digit_3","confidence":"high","reason":"10-state glyph sequence in four-digit time row"},
                        "0x0B04":{"role":"time_digit_4","confidence":"high","reason":"10-state glyph sequence in four-digit time row"},
                        "0x0105":{"role":"dynamic_widget_slot","confidence":"high","reason":"50–56 px square slots with changing arg2 IDs"},
                        "0x0304":{"role":"upper_numeric_10_state","confidence":"medium","reason":"10-state field repeated on OEM dials"},
                        "0x0404":{"role":"upper_categorical_7_state","confidence":"medium","reason":"7-state field repeated on OEM dials"},
                        "0x1102":{"role":"base_image_layer","confidence":"high","reason":"single centered base layer present in every sampled dial"}
                    }
                    observed_widget_ids=sorted({
                        d.get("arg2") for f in files for d in f.get("descriptors",[])
                        if d.get("type_code")==0x0105
                    })
                    blueprint={
                        "schema":"relojlab-wf-blueprint-v1",
                        "app_version":"0.58.0",
                        "screen":{"width":240,"height":296,"center":[120,148]},
                        "target_design":{
                            "background":"black",
                            "analog_center":[120,148],
                            "digital_time":{"placement":"upper_left","curved_requested":True},
                            "battery":{"placement":"upper_right","dynamic":True},
                            "steps":{"placement":"lower_left","dynamic":True},
                            "heart_rate":{"placement":"lower_right","dynamic":True}
                        },
                        "format":{
                            "magic":"WF","version_le":1026,
                            "descriptor_start":54,"descriptor_size":20,
                            "header_fields":{"width":42,"height":44,"element_count":46,"file_size":48,"resource_base":52}
                        },
                        "type_roles":type_roles,
                        "observed_widget_arg2_ids":observed_widget_ids,
                        "widget_arg2_meanings_confirmed":False,
                        "analog_template":{
                            "dial_id":analog_template.get("dial_id") if analog_template else None,
                            "name":analog_template.get("name") if analog_template else None,
                            "sha256":analog_template.get("sha256") if analog_template else None,
                            "descriptors":[d for d in (analog_template.get("descriptors",[]) if analog_template else [])
                                           if d.get("type_code") in (0x0501,0x0601,0x0701,0x0105,0x1102)]
                        },
                        "par_encoder":{
                            "class":"com.bluetrum.abpartool.ParTool",
                            "native_api":"rawToPar(byte[], int width, int height, boolean, boolean, boolean)",
                            "bitmap_api":"bitmapToPar(Bitmap, boolean, boolean, boolean)",
                            "decode_api_found":False,
                            "status":"encoder identified; boolean flag meanings still need isolation"
                        },
                        "safe_to_transmit":False,
                        "blocking_unknowns":[
                            "map exact arg2 IDs for battery/steps/heart-rate",
                            "isolate ParTool boolean flags / exact PAR resource encoding",
                            "rebuild resources and verify file-size/pointers before any 0x83 write"
                        ]
                    }
                    rep["wf_resource_analysis"]["blueprint"]=blueprint
                    blueprint_path=os.path.join(folder,"wf-blueprint-v058.json")
                    with open(blueprint_path,"w",encoding="utf-8") as fh:
                        json.dump(blueprint,fh,ensure_ascii=False,indent=2)
                    rep["wf_resource_analysis"]["blueprint_file"]=blueprint_path

                    emit("6/10 · VALIDACIÓN CABECERA · 0x2A=ancho, 0x2C=alto, 0x2E=cantidad, 0x30=tamaño, 0x34=base recursos relativa a 'WF'.")
                    emit("7/10 · DESCRIPTOR · 20 bytes: mode/type/frame-like/x/y/width-like/height-like/arg2/arg3/puntero-u16.")
                    emit("8/10 · ROLES · hora digital=0x0804/0x0904/0x0A04/0x0B04 · separador=0x1002 · widget=0x0105")
                    analog=[k for k,v in cross["type_map"].items() if any(str(h).startswith("analog_hand_") for h in v.get("role_hints",[]))]
                    emit("9/10 · AGUJAS="+str(analog)+" · widget arg2 observados="+str(observed_widget_ids)+" · blueprint="+blueprint_path)

                    report_path=os.path.join(folder,"wf-analysis-v058.json")
                    with open(report_path,"w",encoding="utf-8") as fh:
                        json.dump(rep["wf_resource_analysis"],fh,ensure_ascii=False,indent=2)
                    rep["wf_resource_analysis"]["analysis_file"]=report_path
                    rep["wf_resource_analysis"]["phase"]="complete"
                    emit("10/10 · V0.58 FINALIZADA · blueprint estructural generado · 0x83 NO TOCADO.")
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["wf_resource_analysis"]["phase"]="error"
                    self.report=rep;self.show()
                    append("EXTRACCIÓN V0.58 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.58 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                x=result.get("wf_resource_analysis",{}).get("cross_file",{})
                if x.get("all_valid_wf") and x.get("all_240x296") and x.get("all_declared_sizes_match") and x.get("all_resource_bases_match_descriptor_end"):
                    append("BLUEPRINT WF GENERADO · agujas + cuatro dígitos de hora + separador + slots de widget ya están mapeados. Falta resolver los IDs exactos de batería/pasos/pulso y el encoder PAR antes de escribir 0x83.")
                else:
                    append("FORMATO WF AÚN TIENE DIFERENCIAS · revisar diagnóstico antes de generar una esfera.")
                self.status.set("V0.58 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=260),done)
'''

s = s[:start] + new_ota + s[end:]

old_ready='append("V0.28 LISTA · botón principal enlazado correctamente. Al pulsarlo debe aparecer actividad inmediatamente.")'
new_ready='append("V0.58 LISTA · 1º PREPARAR ESFERA ÚNICA V0.58; 2º COPIAR DIAGNÓSTICO. Mapea agujas, cuatro dígitos de hora, separador y slots de widgets; genera blueprint 240×296; 0x83 bloqueado.")'
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


# V0.58: do not depend on a second advertising cycle after the first GATT attempt.
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
print("build patch v0.58 aplicado")
