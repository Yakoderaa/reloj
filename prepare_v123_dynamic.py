from pathlib import Path
import hashlib, base64, zlib, json

def u16(b,o): return int.from_bytes(b[o:o+2],"little")
def p16(b,o,v): b[o:o+2]=int(v).to_bytes(2,"little")

def record_len(buf,off):
    if off+12>len(buf) or u16(buf,off)!=0x0164:
        raise RuntimeError(f"descriptor MARKET inválido en 0x{off:04X}")
    kind=u16(buf,off+8)
    if kind==0x1202:
        return 28
    if kind==0x0804:
        return 18
    return 12

def descriptor_chain(buf,count):
    off=0x10; starts=[]
    for _ in range(count):
        starts.append(off)
        off+=record_len(buf,off)
    return starts,off

def find_numeric(buf,field):
    count=u16(buf,10)
    starts,_=descriptor_chain(buf,count)
    for off in starts:
        if record_len(buf,off)==28 and u16(buf,off+8)==0x1202 and u16(buf,off+10)==field:
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
original_count=u16(base,10)
if original_count!=7: raise SystemExit("conteo 4CC6 inesperado")
orig_starts,append_off=descriptor_chain(base,original_count)
if append_off!=0x6A:
    raise SystemExit(f"fin de tabla 4CC6 inesperado: 0x{append_off:04X}")
if any(base[append_off:append_off+140]):
    raise SystemExit("el área contigua tras la tabla OEM no está libre")

HOUR,MINUTE,STEPS,HEART,BAT=0x8001,0x8002,0x8009,0x800E,0x8013
plans=[
    ("hour",time_donor,find_numeric(time_donor,HOUR),18,24,"%02d",2),
    ("minute",time_donor,find_numeric(time_donor,MINUTE),54,16,":%02d",2),
    ("battery",metric_donor,find_numeric(metric_donor,BAT),178,24,"%03d%%",1),
    ("steps",metric_donor,find_numeric(metric_donor,STEPS),10,255,"%05d",1),
    ("heart_rate",metric_donor,find_numeric(metric_donor,HEART),160,255,"%03d",1),
]
fields={}
for idx,(name,src,off,x,y,fmt,size) in enumerate(plans):
    rec=bytearray(src[off:off+28])
    if len(rec)!=28 or u16(rec,0)!=0x0164 or u16(rec,8)!=0x1202:
        raise SystemExit("descriptor numérico donante inválido: "+name)
    patch_numeric(rec,0,x,y,fmt,size)
    dst=append_off+idx*28
    base[dst:dst+28]=rec
    fields[name]={"field_id":f"0x{u16(rec,10):04X}","offset":dst,"x":x,"y":y,"format":fmt}

new_count=original_count+len(plans)
p16(base,10,new_count)
starts,end=descriptor_chain(base,new_count)
expected_starts=orig_starts+[append_off+i*28 for i in range(len(plans))]
if starts!=expected_starts:
    raise SystemExit("la tabla MARKET V1.23 no quedó contigua")
if end!=append_off+140:
    raise SystemExit("fin de tabla MARKET V1.23 inesperado")
if end>=0x800:
    raise SystemExit("tabla MARKET invade recursos")

candidate=bytes(base)
for field in (HOUR,MINUTE,STEPS,HEART,BAT):
    find_numeric(candidate,field)

assets.mkdir(parents=True,exist_ok=True)
(assets/"target_face_v123.b64").write_text(base64.b64encode(zlib.compress(candidate,9)).decode("ascii"),encoding="ascii")
meta={
 "version":"1.23.0",
 "format":"device-1180 MARKET real · descriptor table contiguous",
 "source_face":"4CC6",
 "source_visual":"black minimal analog, white hour/minute hands, red second hand",
 "time_donor":"04C2",
 "metric_donor":"2D7F",
 "bin_id_hex":candidate[4:6].hex(),
 "raw_size":len(candidate),
 "raw_sha256":hashlib.sha256(candidate).hexdigest(),
 "element_count":u16(candidate,10),
 "descriptor_starts":[f"0x{x:04X}" for x in starts],
 "descriptor_table_end":f"0x{end:04X}",
 "live_fields":fields,
 "analog_engine":{
   "source":"4CC6 real MARKET face",
   "hour_hand":"firmware dynamic preserved",
   "minute_hand":"firmware dynamic preserved",
   "second_hand":"firmware dynamic preserved"
 },
 "approved_layout":{
   "background":"black","analog":"center","digital_time":"upper-left",
   "battery":"upper-right","steps":"lower-left","heart_rate":"lower-right"
 },
 "checks":{
   "all_pass":True,"size_header":int.from_bytes(candidate[:4],"little")==len(candidate)-16,
   "real_market_bin_id":candidate[4:6].hex()=="4cc6",
   "descriptor_chain_contiguous":starts==expected_starts,
   "no_alignment_gap":starts[7]==0x6A
 }
}
(assets/"target_face_v123.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
print("V1.23 MARKET ready",meta["raw_size"],meta["raw_sha256"],meta["descriptor_starts"],fields)
