from pathlib import Path
import hashlib, base64, zlib, json

def u16(b,o): return int.from_bytes(b[o:o+2],"little")
def p16(b,o,v): b[o:o+2]=int(v).to_bytes(2,"little")

def find_numeric(buf,field):
    for off in range(0x10,0x800-28):
        if u16(buf,off)==0x0164 and u16(buf,off+8)==0x1202 and u16(buf,off+10)==field:
            return off
    raise RuntimeError(f"falta campo MARKET 0x{field:04X}")

def patch_numeric(buf,off,x,y,fmt=None,size=None):
    p16(buf,off+2,x); p16(buf,off+4,y)
    if size is not None: p16(buf,off+6,size)
    if fmt is not None:
        raw=fmt.encode("ascii")+bytes([0])
        if len(raw)>8: raise RuntimeError("formato MARKET demasiado largo")
        buf[off+12:off+20]=raw.ljust(8,bytes([0]))

assets=Path("assets")
base=bytearray((assets/"donor_4CC6.bin").read_bytes())
time_donor=(assets/"donor_04C2.bin").read_bytes()
metric_donor=(assets/"donor_2D7F.bin").read_bytes()
expected={
 "4CC6":"52f9a9857929fc64791551010eb0eaf2ad03f5e280f9e9d36701f1fdc07d1b2b",
 "04C2":"b2466ece5b918c29f86855157f3e42e91511c600a352c1bbdae8280b8b6a3179",
 "2D7F":"ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a"}
for name,data in (("4CC6",bytes(base)),("04C2",time_donor),("2D7F",metric_donor)):
    got=hashlib.sha256(data).hexdigest()
    if got!=expected[name]: raise SystemExit(f"donante {name} cambió: {got}")
if int.from_bytes(base[:4],"little")!=len(base)-16: raise SystemExit("cabecera MARKET 4CC6 inválida")
if base[4:6].hex().upper()!="4CC6": raise SystemExit("BinID MARKET inesperado")
if u16(base,10)!=7: raise SystemExit("conteo 4CC6 inesperado")

HOUR,MINUTE,STEPS,HEART,BAT=0x8001,0x8002,0x8009,0x800E,0x8013
plans=[
    ("hour",time_donor,find_numeric(time_donor,HOUR),18,24,"%02d",2),
    ("minute",time_donor,find_numeric(time_donor,MINUTE),54,16,":%02d",2),
    ("battery",metric_donor,find_numeric(metric_donor,BAT),178,24,"%03d%%",1),
    ("steps",metric_donor,find_numeric(metric_donor,STEPS),10,255,"%05d",1),
    ("heart_rate",metric_donor,find_numeric(metric_donor,HEART),160,255,"%03d",1),
]
last=max(i for i,v in enumerate(base[:0x800]) if v)
append_off=(last+4)&~3
if append_off+28*len(plans)>0x800 or any(base[append_off:append_off+28*len(plans)]):
    raise SystemExit("sin espacio seguro en bloque de configuración MARKET 4CC6")

fields={}
for idx,(name,src,off,x,y,fmt,size) in enumerate(plans):
    rec=bytearray(src[off:off+28])
    patch_numeric(rec,0,x,y,fmt,size)
    dst=append_off+idx*28
    base[dst:dst+28]=rec
    fields[name]={"field_id":f"0x{u16(rec,10):04X}","offset":dst,"x":x,"y":y,"format":fmt}

p16(base,10,7+len(plans))
candidate=bytes(base)
if int.from_bytes(candidate[:4],"little")!=len(candidate)-16: raise SystemExit("tamaño MARKET dejó de coincidir")
for field in (HOUR,MINUTE,STEPS,HEART,BAT):
    if find_numeric(candidate,field) is None: raise SystemExit(f"campo vivo ausente {field:04X}")

assets.mkdir(parents=True,exist_ok=True)
(assets/"target_face_v121.b64").write_text(base64.b64encode(zlib.compress(candidate,9)).decode("ascii"),encoding="ascii")
meta={
 "version":"1.22.0",
 "format":"device-1180 MARKET real",
 "source_face":"4CC6",
 "source_visual":"black minimal analog, white hour/minute hands, red second hand",
 "time_donor":"04C2",
 "metric_donor":"2D7F",
 "bin_id_hex":candidate[4:6].hex(),
 "raw_size":len(candidate),
 "raw_sha256":hashlib.sha256(candidate).hexdigest(),
 "element_count":u16(candidate,10),
 "config_append_offset":append_off,
 "live_fields":fields,
 "analog_engine":{
   "source":"4CC6 real MARKET face",
   "hour_hand":"firmware dynamic preserved",
   "minute_hand":"firmware dynamic preserved",
   "second_hand":"firmware dynamic preserved"
 },
 "approved_layout":{
   "background":"black",
   "analog":"center",
   "digital_time":"upper-left",
   "battery":"upper-right",
   "steps":"lower-left",
   "heart_rate":"lower-right"
 },
 "checks":{"all_pass":True,"size_header":True,"real_market_bin_id":candidate[4:6].hex()=="4cc6"}
}
(assets/"target_face_v121.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
print("V1.21 MARKET ready",meta["raw_size"],meta["raw_sha256"],meta["bin_id_hex"],fields)
