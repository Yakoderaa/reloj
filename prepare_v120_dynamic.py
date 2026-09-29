from pathlib import Path
import urllib.request, json, hashlib, base64, zlib

OUT=Path("assets/target_face_v120.b64")
META=Path("assets/target_face_v120.json")

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"RelojLab/1.20-build","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=25) as r:
        return json.loads(r.read().decode("utf-8","replace"))

def get_bin(url):
    req=urllib.request.Request(url,headers={"User-Agent":"RelojLab/1.20-build","Accept":"*/*"})
    with urllib.request.urlopen(req,timeout=35) as r:
        return r.read(4*1024*1024)

def u16(b,o): return int.from_bytes(b[o:o+2],"little")
def u32(b,o): return int.from_bytes(b[o:o+4],"little")
def p16(b,o,v): b[o:o+2]=int(v).to_bytes(2,"little")
def p32(b,o,v): b[o:o+4]=int(v).to_bytes(4,"little")

def parse(data):
    if len(data)<54 or data[:2]!=b"WF":
        raise RuntimeError("donante WF inválido")
    n=u16(data,0x2e)
    ds=[]
    for i in range(n):
        off=54+i*20
        raw=bytes(data[off:off+20])
        if len(raw)!=20: raise RuntimeError("descriptor truncado")
        ds.append({
            "index":i,"raw":raw,"type":u16(raw,2),"frames":u16(raw,4),
            "x":u16(raw,6),"y":u16(raw,8),"ptr":u16(raw,18),"abs":u16(raw,18)+2
        })
    return {
        "version":u16(data,2),"width":u16(data,0x2a),"height":u16(data,0x2c),
        "count":n,"declared":u32(data,0x30),"resource_base":u32(data,0x34)+2,
        "descriptors":ds
    }

def find(wf,typ,occ=0):
    xs=[d for d in wf["descriptors"] if d["type"]==typ]
    if occ>=len(xs): raise RuntimeError(f"falta descriptor 0x{typ:04X}")
    return xs[occ]

def segment(data,wf,desc):
    starts=sorted(set(d["abs"] for d in wf["descriptors"] if 0<=d["abs"]<len(data)))
    s=desc["abs"]; nxt=[x for x in starts if x>s]; e=nxt[0] if nxt else len(data)
    if e<=s: raise RuntimeError("segmento OEM inválido")
    return bytes(data[s:e])

def patch_desc(raw,x,y,ptr):
    b=bytearray(raw);p16(b,6,x);p16(b,8,y);p16(b,18,ptr);return bytes(b)

wanted={"2011092","2029002","2011017"}
found={}
api="https://wr.watchhealth.com.cn/app-halfwit/app-dial/getDialList"
for page in range(1,12):
    obj=get_json(f"{api}?currentPage={page}&pageSize=20&watchId=102")
    rows=obj.get("data") if isinstance(obj,dict) else []
    for e in rows or []:
        did=str(e.get("dialId") or "")
        if did in wanted and isinstance(e.get("dialFile"),str):
            found[did]=e["dialFile"]
    if len(found)==len(wanted):break
if set(found)!=wanted:
    raise SystemExit("V1.20 build: no se encontraron los tres donantes OEM: "+repr(found))

bins={k:get_bin(v) for k,v in found.items()}
expected_sha={
    "2011092":"f470d7981c697e3ce791aca329fe231fca1530722f033be30890d96af9279a5f",
    "2029002":"b0f0ae50777fc222cfec1de65c537bbfa6266301b5d643a5fabbbcf6a2984c44",
    "2011017":"2ada22a0dfd3f2cdce4a1b459971843305d163cfddb62aff8d1b44cd647a1f75",
}
for k,data in bins.items():
    got=hashlib.sha256(data).hexdigest()
    if got!=expected_sha[k]:
        raise SystemExit(f"V1.20 build: donante {k} cambió: {got}")

wfs={k:parse(v) for k,v in bins.items()}
for k,wf in wfs.items():
    if (wf["width"],wf["height"])!=(240,296):
        raise SystemExit(f"V1.20 build: resolución inesperada en {k}")

print("V1.20 donor descriptor types:")
for k,wf in wfs.items():
    print(k,[f"0x{d['type']:04X}" for d in wf["descriptors"]])

base_data=bins["2029002"];base_wf=wfs["2029002"]
d_time=[
    find(base_wf,0x0804),find(base_wf,0x0904),find(base_wf,0x1002,1),
    find(base_wf,0x0A04),find(base_wf,0x0B04)
]
d_steps=find(wfs["2011017"],0x4104)
d_heart=find(wfs["2011017"],0x4204)
d_hour=find(wfs["2011092"],0x0501)
d_min=find(wfs["2011092"],0x0601)
d_sec=find(wfs["2011092"],0x0701)
d_base=find(wfs["2011092"],0x1102)

# 0x4304 is the next OEM live metric descriptor in this watch family.
battery_source=None;d_battery=None
for src,wf in wfs.items():
    matches=[d for d in wf["descriptors"] if d["type"]==0x4304]
    if matches:
        battery_source=src;d_battery=matches[0];break
if d_battery is None:
    inventory={k:[f"0x{d['type']:04X}" for d in wf["descriptors"]] for k,wf in wfs.items()}
    raise SystemExit("V1.20 build: no se encontró descriptor live 0x4304 para batería. Inventario="+repr(inventory))

plans=[
    ("steps","2011017",d_steps,34,244),
    ("time_tens","2029002",d_time[0],24,42),
    ("time_hour_units","2029002",d_time[1],42,38),
    ("time_separator","2029002",d_time[2],58,42),
    ("time_min_tens","2029002",d_time[3],74,38),
    ("time_min_units","2029002",d_time[4],92,42),
    ("battery",battery_source,d_battery,186,28),
    ("heart","2011017",d_heart,174,244),
    ("hour_hand","2011092",d_hour,120,148),
    ("minute_hand","2011092",d_min,120,148),
    ("second_hand","2011092",d_sec,120,148),
    ("analog_base","2011092",d_base,120,148),
]

count=len(plans)
resource_base=54+20*count
out=bytearray(base_data[:54]+bytes(20*count))
p16(out,0x2e,count)
p32(out,0x34,resource_base-2)

ptrs={};manifest={}
for name,src,d,_,_ in plans:
    key=(src,d["abs"])
    if key in ptrs:continue
    blob=segment(bins[src],wfs[src],d)
    ptr=len(out)-2
    if ptr>65535: raise SystemExit(f"V1.20 build: puntero u16 excedido antes de {name}: {ptr}")
    ptrs[key]=ptr
    manifest[name]={"source":src,"type":f"0x{d['type']:04X}","length":len(blob),
                    "ptr":ptr,"sha256":hashlib.sha256(blob).hexdigest()}
    out.extend(blob)

for idx,(name,src,d,x,y) in enumerate(plans):
    raw=patch_desc(d["raw"],x,y,ptrs[(src,d["abs"])])
    off=54+idx*20
    out[off:off+20]=raw

p32(out,0x30,len(out))
candidate=bytes(out);cw=parse(candidate)
types=[f"0x{d['type']:04X}" for d in cw["descriptors"]]
required={"0x0501","0x0601","0x0701","0x0804","0x0904","0x0A04","0x0B04",
          "0x4104","0x4204","0x4304","0x1102"}
checks={
    "magic":candidate[:2]==b"WF",
    "version":cw["version"]==1026,
    "resolution":(cw["width"],cw["height"])==(240,296),
    "count":cw["count"]==count,
    "declared_size":cw["declared"]==len(candidate),
    "resource_base":cw["resource_base"]==resource_base,
    "required_dynamic_types":required.issubset(set(types)),
    "all_pointers_in_file":all(0<=d["abs"]<len(candidate) for d in cw["descriptors"]),
    "all_pointers_u16":all(d["ptr"]<=65535 for d in cw["descriptors"]),
}
checks["all_pass"]=all(checks.values())
if not checks["all_pass"]:
    raise SystemExit("V1.20 build: WF dinámico no validó: "+repr(checks))

packed=base64.b64encode(zlib.compress(candidate,9)).decode("ascii")
OUT.write_text(packed,encoding="ascii")
meta={
    "version":"1.20.0","format":"WF_DYNAMIC","width":240,"height":296,
    "raw_size":len(candidate),"raw_sha256":hashlib.sha256(candidate).hexdigest(),
    "types":types,"required_types":sorted(required),"checks":checks,
    "resource_manifest":manifest,
    "layout":{
        "analog_center":[120,148],"time":"upper-left","battery":"upper-right",
        "steps":"lower-left","heart_rate":"lower-right"
    }
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
print("V1.20 dynamic WF ready",meta["raw_size"],meta["raw_sha256"],types)
