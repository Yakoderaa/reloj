from pathlib import Path
import urllib.request, json, hashlib, base64, zlib

# Build the dynamic 240x296 target WF at release-build time from the exact OEM
# resources previously mapped for this watch. This avoids runtime donor downloads.
def _get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"RelojLab/0.84-build","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read().decode("utf-8","replace"))

def _get_bin(url):
    req=urllib.request.Request(url,headers={"User-Agent":"RelojLab/0.84-build","Accept":"*/*"})
    with urllib.request.urlopen(req,timeout=25) as r:
        return r.read(4*1024*1024)

def _u16(b,o): return int.from_bytes(b[o:o+2],"little")
def _u32(b,o): return int.from_bytes(b[o:o+4],"little")
def _p16(b,o,v): b[o:o+2]=int(v).to_bytes(2,"little")
def _p32(b,o,v): b[o:o+4]=int(v).to_bytes(4,"little")

def _parse(data):
    if len(data)<54 or data[:2]!=b"WF":
        raise RuntimeError("donante WF inválido")
    n=_u16(data,0x2e)
    ds=[]
    for i in range(n):
        off=54+i*20
        raw=bytes(data[off:off+20])
        if len(raw)!=20: raise RuntimeError("descriptor truncado")
        ds.append({
            "index":i,"raw":raw,"type":_u16(raw,2),"frames":_u16(raw,4),
            "x":_u16(raw,6),"y":_u16(raw,8),"ptr":_u16(raw,18),"abs":_u16(raw,18)+2
        })
    return {
        "version":_u16(data,2),"width":_u16(data,0x2a),"height":_u16(data,0x2c),
        "count":n,"declared":_u32(data,0x30),"resource_base":_u32(data,0x34)+2,
        "descriptors":ds
    }

def _find(wf,typ,occ=0):
    xs=[d for d in wf["descriptors"] if d["type"]==typ]
    if occ>=len(xs): raise RuntimeError(f"falta 0x{typ:04X}")
    return xs[occ]

def _segment(data,wf,desc):
    starts=sorted(set(d["abs"] for d in wf["descriptors"] if 0<=d["abs"]<len(data)))
    s=desc["abs"]
    nxt=[x for x in starts if x>s]
    e=nxt[0] if nxt else len(data)
    if e<=s: raise RuntimeError("segmento OEM inválido")
    return bytes(data[s:e])

def _patch_desc(raw,x,y,ptr):
    b=bytearray(raw)
    _p16(b,6,x);_p16(b,8,y);_p16(b,18,ptr)
    return bytes(b)

wanted={"2011092","2029002","2011017"}
found={}
api="https://wr.watchhealth.com.cn/app-halfwit/app-dial/getDialList"
for page in range(1,10):
    obj=_get_json(f"{api}?currentPage={page}&pageSize=20&watchId=102")
    rows=obj.get("data") if isinstance(obj,dict) else []
    for e in rows or []:
        did=str(e.get("dialId") or "")
        if did in wanted and isinstance(e.get("dialFile"),str):
            found[did]=e["dialFile"]
    if len(found)==len(wanted): break
if set(found)!=wanted:
    raise SystemExit("V0.84 build: no se encontraron los tres donantes OEM")

bins={k:_get_bin(v) for k,v in found.items()}
expected_sha={
    "2011092":"f470d7981c697e3ce791aca329fe231fca1530722f033be30890d96af9279a5f",
    "2029002":"b0f0ae50777fc222cfec1de65c537bbfa6266301b5d643a5fabbbcf6a2984c44",
    "2011017":"2ada22a0dfd3f2cdce4a1b459971843305d163cfddb62aff8d1b44cd647a1f75",
}
for k,data in bins.items():
    got=hashlib.sha256(data).hexdigest()
    if got!=expected_sha[k]:
        raise SystemExit(f"V0.84 build: donante {k} cambió: {got}")

wfs={k:_parse(v) for k,v in bins.items()}
for k,wf in wfs.items():
    if (wf["width"],wf["height"])!=(240,296):
        raise SystemExit(f"V0.84 build: resolución inesperada en {k}")

# Base descriptor table: 2029002 (11 descriptors). Keep its dynamic individual
# time digit resources, then transplant:
# - steps + heart-rate digits from 2011017
# - white hour/minute + red seconds from 2011092
# - analog black base from 2011092
base_data=bins["2029002"]; base_wf=wfs["2029002"]
if base_wf["count"]!=11: raise SystemExit("V0.84 build: base 2029002 ya no tiene 11 elementos")
resource_base=base_wf["resource_base"]
out=bytearray(base_data[:resource_base])

d_time=[
    _find(base_wf,0x0804),_find(base_wf,0x0904),_find(base_wf,0x1002,1),
    _find(base_wf,0x0A04),_find(base_wf,0x0B04)
]
d_steps=_find(wfs["2011017"],0x4104)
d_heart=_find(wfs["2011017"],0x4204)
d_hour=_find(wfs["2011092"],0x0501)
d_min=_find(wfs["2011092"],0x0601)
d_sec=_find(wfs["2011092"],0x0701)
d_base=_find(wfs["2011092"],0x1102)

# Resource order is intentionally small->large with the huge analog background
# last, so every u16 start pointer remains representable.
resources=[
    ("time_shared","2029002",d_time[0]),
    ("time_hour_units","2029002",d_time[1]),
    ("time_minute_units","2029002",d_time[4]),
    ("metrics_shared","2011017",d_steps),
    ("hour_hand","2011092",d_hour),
    ("minute_hand","2011092",d_min),
    ("second_hand","2011092",d_sec),
    ("analog_base","2011092",d_base),
]
ptrs={}
resource_manifest={}
for name,src,d in resources:
    key=(src,d["abs"])
    if key in ptrs: continue
    blob=_segment(bins[src],wfs[src],d)
    ptr=len(out)-2
    if ptr>65535:
        raise SystemExit(f"V0.84 build: puntero u16 excedido antes de {name}: {ptr}")
    ptrs[key]=ptr
    resource_manifest[name]={"source":src,"length":len(blob),"ptr":ptr,"sha256":hashlib.sha256(blob).hexdigest()}
    out.extend(blob)

def _ptr(src,d):
    return ptrs[(src,d["abs"])]

# Exact layout recovered from the user's earlier target specification.
plans=[
    # index, donor source, descriptor, x, y
    (0,"2011017",d_steps,56,245),
    (1,"2029002",d_time[0],36,54),
    (2,"2029002",d_time[1],54,45),
    (3,"2029002",d_time[2],69,49),
    (4,"2029002",d_time[3],84,45),
    (5,"2029002",d_time[4],102,54),
    (6,"2011017",d_heart,186,245),
    (7,"2011092",d_hour,120,148),
    (8,"2011092",d_min,120,148),
    (9,"2011092",d_sec,120,148),
    (10,"2011092",d_base,120,148),
]
for idx,src,d,x,y in plans:
    raw=_patch_desc(d["raw"],x,y,_ptr(src,d))
    off=54+idx*20
    out[off:off+20]=raw

_p32(out,0x30,len(out))
candidate=bytes(out)
cw=_parse(candidate)
types=[f"0x{d['type']:04X}" for d in cw["descriptors"]]
expected_types=["0x4104","0x0804","0x0904","0x1002","0x0A04","0x0B04",
                "0x4204","0x0501","0x0601","0x0701","0x1102"]
checks={
    "magic":candidate[:2]==b"WF",
    "version":cw["version"]==1026,
    "resolution":(cw["width"],cw["height"])==(240,296),
    "count":cw["count"]==11,
    "declared_size":cw["declared"]==len(candidate),
    "resource_base_unchanged":cw["resource_base"]==resource_base,
    "type_sequence":types==expected_types,
    "all_pointers_in_file":all(0<=d["abs"]<len(candidate) for d in cw["descriptors"]),
    "all_pointers_u16":all(d["ptr"]<=65535 for d in cw["descriptors"]),
}
checks["all_pass"]=all(checks.values())
if not checks["all_pass"]:
    raise SystemExit("V0.84 build: candidato objetivo no validó: "+repr(checks))

packed=base64.b64encode(zlib.compress(candidate,9)).decode("ascii")
candidate_sha=hashlib.sha256(candidate).hexdigest()

p=Path("app.py")
s=p.read_text(encoding="utf-8")
if 'APP_VERSION="0.83.0"' not in s:
    raise SystemExit("V0.84 requiere la base V0.83 aplicada")
s=s.replace('APP_VERSION="0.83.0"','APP_VERSION="0.84.0"',1)
s=s.replace('V0.83','V0.84')

fn_start=s.index("            def build_customize_candidate():")
fn_end=s.index("            def build(dev_type",fn_start)
new_fn=f'''            def build_target_market_candidate():
                import base64,zlib
                packed={packed!r}
                raw=zlib.decompress(base64.b64decode(packed))
                expected={candidate_sha!r}
                if hashlib.sha256(raw).hexdigest()!=expected:
                    raise RuntimeError("Candidato V0.84 embebido corrupto")
                if len(raw)<54 or raw[:2]!=b"WF":
                    raise RuntimeError("Candidato V0.84 no es WF")
                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v084")
                os.makedirs(folder,exist_ok=True)
                path=os.path.join(folder,"target-photo-dynamic-v084.bin")
                with open(path,"wb") as fh:fh.write(raw)
                return path,raw,240,296
'''
s=s[:fn_start]+new_fn+s[fn_end:]

old_prepare='''                emit("1/9 · Generando CUSTOMIZE real 240×240 + paquete OEM…")
                path,raw,custom_w,custom_h=await asyncio.to_thread(build_customize_candidate)
                oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                rep["single_face_install"]["candidate"]={
                    "path":path,"format":"UtraWatch CUSTOMIZE cBinFile","width":custom_w,"height":custom_h,
                    "picture_mode":2,"raw_size":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "raw_header_hex":raw[:10].hex(),
                    "oem_stream_size":len(oem_stream),"deflate_size":len(deflated),
                    "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                    "oem_crc16":f"0x{crc16_8005(deflated):04X}",
                    "oem_header_hex":oem_stream[:20].hex()
                }
'''
new_prepare=f'''                emit("1/9 · Cargando esfera objetivo dinámica 240×296 + paquete OEM…")
                path,raw,target_w,target_h=await asyncio.to_thread(build_target_market_candidate)
                oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                rep["single_face_install"]["candidate"]={{
                    "path":path,"format":"WF MARKET dinámico","width":target_w,"height":target_h,
                    "raw_size":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "descriptor_types":{expected_types!r},
                    "layout":{{
                        "background":"analog black OEM 2011092",
                        "analog":"white hour/minute + red second · center 120,148",
                        "digital_time":"curved upper-left · 2029002 individual digits",
                        "steps":"lower-left · dynamic 0x4104",
                        "heart_rate":"lower-right · dynamic 0x4204",
                        "battery":"upper-right reserved; no verified dynamic WF binding"
                    }},
                    "build_checks":{checks!r},
                    "resource_manifest":{resource_manifest!r},
                    "oem_stream_size":len(oem_stream),"deflate_size":len(deflated),
                    "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                    "oem_crc16":f"0x{{crc16_8005(deflated):04X}}",
                    "oem_header_hex":oem_stream[:20].hex()
                }}
'''
if old_prepare not in s:
    raise SystemExit("V0.84: preparación V0.83 no encontrada")
s=s.replace(old_prepare,new_prepare,1)

s=s.replace(
    'emit("5/9 · Instalando nuestra esfera en CUSTOMIZE cmd=2 · "+str(len(chunks))+" bloques…")',
    'emit("5/9 · Instalando la esfera de la foto como MARKET cmd=3 · "+str(len(chunks))+" bloques…")',
    1
)
s=s.replace(
    'custom_transfer=await transfer_slot(2,"CUSTOMIZE",file_bytes,chunks)\\n                    rep["single_face_install"]["custom_transfer"]=custom_transfer',
    'target_transfer=await transfer_slot(3,"TARGET-MARKET",file_bytes,chunks)\\n                    rep["single_face_install"]["target_market_transfer"]=target_transfer',
    1
)
s=s.replace(
    'emit("6/9 · CUSTOMIZE completo; esperando aplicación…")',
    'emit("6/9 · MARKET objetivo completo; esperando aplicación…")',
    1
)

old_select='''                    custom_index=int(face_slots["custom_index"])
                    _,sel_status,_=await tx83_wait(bytes([1,custom_index&255]),3.0)
                    if sel_status!=1:raise RuntimeError("El reloj rechazó la selección del slot CUSTOMIZE "+str(custom_index))
                    await asyncio.sleep(1.2)
                    verify_mark=len(messages)
                    await tx(0x84,b"",3,0)
                    selected_payload=await wait_data(0x84,verify_mark,5.0)
                    selected_info=dial_info(selected_payload)
                    selection_verified=bool(selected_info and selected_info.get("index")==custom_index)
                    selection={"index":custom_index,"show_order":face_slots.get("custom_show_order"),
                               "status":sel_status,"verified":selection_verified,"dial_info":selected_info}
                    rep["single_face_install"]["selection_lock"]=selection
'''
new_select='''                    target_index=face_slots.get("market_index")
                    if target_index is None:
                        raise RuntimeError("UtraWatch no resolvió el índice MARKET de este reloj")
                    target_index=int(target_index)
                    _,sel_status,_=await tx83_wait(bytes([1,target_index&255]),3.0)
                    if sel_status!=1:raise RuntimeError("El reloj rechazó la selección del slot MARKET "+str(target_index))
                    await asyncio.sleep(1.2)
                    verify_mark=len(messages)
                    await tx(0x84,b"",3,0)
                    selected_payload=await wait_data(0x84,verify_mark,5.0)
                    selected_info=dial_info(selected_payload)
                    selection_verified=bool(selected_info and selected_info.get("index")==target_index)
                    selection={"index":target_index,"show_order":face_slots.get("market_show_order"),
                               "status":sel_status,"verified":selection_verified,"dial_info":selected_info}
                    rep["single_face_install"]["selection_lock"]=selection
'''
if old_select not in s:
    raise SystemExit("V0.84: selección CUSTOMIZE V0.83 no encontrada")
s=s.replace(old_select,new_select,1)

old_mirror='''                    # Keep this physical test minimal: first prove CUSTOMIZE is actually
                    # committed/renderable. MARKET mirroring is deferred until visual confirmation.
                    market_mirror={"attempted":False,"ok":False,
                                   "reason":"deferred until CUSTOMIZE is visibly confirmed"}
                    rep["single_face_install"]["market_mirror"]=market_mirror
'''
new_mirror='''                    rep["single_face_install"]["customize_mirror"]={
                        "attempted":False,
                        "reason":"V0.84 mantiene V0.83 en CUSTOMIZE y dedica MARKET a la esfera dinámica de la foto"
                    }
'''
if old_mirror not in s:
    raise SystemExit("V0.84: bloque mirror V0.83 no encontrado")
s=s.replace(old_mirror,new_mirror,1)

s=s.replace(
    'all_ok=bool(custom_transfer.get("ok") and sel_status==1 and selection_verified and connected)',
    'all_ok=bool(target_transfer.get("ok") and sel_status==1 and selection_verified and connected)',
    1
)
s=s.replace(
    '"custom_face_protocol_committed_and_selected" if all_ok else',
    '"target_photo_dynamic_face_installed_and_selected" if all_ok else',
    1
)

s=s.replace(
    'V0.84 LISTA · 1º INSTALAR ESFERA RELOJ LAB V0.84; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Genera el CUSTOMIZE real 240×240 y usa la cabecera CEProtocolB exacta.',
    'V0.84 LISTA · 1º INSTALAR ESFERA DE LA FOTO V0.84; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Instala un WF MARKET 240×296 con analógico, hora curvada, pasos y pulso dinámicos.'
)
s=s.replace('INSTALAR ESFERA RELOJ LAB V0.84','INSTALAR ESFERA DE LA FOTO V0.84')
s=s.replace(
    'V0.84 · CUSTOMIZE REAL · genera el mismo formato cBinFile de UtraWatch, corrige device_type/N en CEProtocolB y selecciona el slot editable.',
    'V0.84 · ESFERA OBJETIVO · reconstruye el diseño de la foto con recursos OEM dinámicos: analógico central, hora curvada arriba izquierda, pasos y pulso abajo.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.84 aplicado")
print("candidate",len(candidate),candidate_sha,checks)
