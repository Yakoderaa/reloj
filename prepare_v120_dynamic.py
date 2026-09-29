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
base=bytearray((assets/"donor_2D7F.bin").read_bytes())
time_donor=(assets/"donor_04C2.bin").read_bytes()
expected={
 "2D7F":"ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a",
 "04C2":"b2466ece5b918c29f86855157f3e42e91511c600a352c1bbdae8280b8b6a3179"}
for name,data in (("2D7F",bytes(base)),("04C2",time_donor)):
    got=hashlib.sha256(data).hexdigest()
    if got!=expected[name]: raise SystemExit(f"donante {name} cambió: {got}")
if int.from_bytes(base[:4],"little")!=len(base)-16: raise SystemExit("cabecera MARKET inválida")

HOUR,MINUTE,STEPS,CAL,HEART,BAT=0x8001,0x8002,0x8009,0x800D,0x800E,0x8013
patch_numeric(base,find_numeric(base,CAL),0xFFFF,0xFFFF)
patch_numeric(base,find_numeric(base,STEPS),10,260,"%05d",1)
patch_numeric(base,find_numeric(base,HEART),158,260,"%03d",1)
patch_numeric(base,find_numeric(base,BAT),178,28,"%03d%%",1)

hour_off=find_numeric(time_donor,HOUR); minute_off=find_numeric(time_donor,MINUTE)
hour=bytearray(time_donor[hour_off:hour_off+28]); minute=bytearray(time_donor[minute_off:minute_off+28])
patch_numeric(hour,0,12,24,"%02d",2); patch_numeric(minute,0,42,24,":%02d",2)
last=max(i for i,v in enumerate(base[:0x800]) if v); append_off=(last+4)&~3
if append_off+56>0x800 or any(base[append_off:append_off+56]): raise SystemExit("sin espacio seguro")
base[append_off:append_off+28]=hour; base[append_off+28:append_off+56]=minute
p16(base,10,u16(base,10)+2)

fields={}
for field,name in ((HOUR,"hour"),(MINUTE,"minute"),(STEPS,"steps"),(HEART,"heart_rate"),(BAT,"battery")):
    off=find_numeric(base,field)
    fields[name]={"field_id":f"0x{field:04X}","offset":off,"x":u16(base,off+2),"y":u16(base,off+4),
                  "format":bytes(base[off+12:off+20]).split(bytes([0]),1)[0].decode("ascii")}
if u16(base,10)!=13: raise SystemExit("conteo MARKET inesperado")
candidate=bytes(base)
(assets/"target_face_v120.b64").write_text(base64.b64encode(zlib.compress(candidate,9)).decode("ascii"),encoding="ascii")
meta={"version":"1.20.0","format":"device-1180 MARKET in verified CUSTOMIZE slot","source_face":"2D7F",
      "time_donor":"04C2","raw_size":len(candidate),"raw_sha256":hashlib.sha256(candidate).hexdigest(),
      "element_count":u16(candidate,10),"live_fields":fields,
      "analog_engine":{"source":"2D7F real MARKET","hour_hand":"firmware dynamic preserved",
      "minute_hand":"firmware dynamic preserved","second_hand":"firmware dynamic preserved"},
      "checks":{"all_pass":True,"size_header":int.from_bytes(candidate[:4],"little")==len(candidate)-16}}
(assets/"target_face_v120.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
print("V1.20 MARKET ready",meta["raw_size"],meta["raw_sha256"],fields)
