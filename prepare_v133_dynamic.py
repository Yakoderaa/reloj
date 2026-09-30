from pathlib import Path
import base64, hashlib, json, math, zlib
from PIL import Image, ImageDraw
import numpy as np

ASSETS=Path("assets")
DONOR=ASSETS/"donor_2D7F.bin"
raw=bytearray(DONOR.read_bytes())
OEM_SHA="ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a"
if hashlib.sha256(raw).hexdigest()!=OEM_SHA:
    raise SystemExit("V1.33: 2D7F donor SHA changed")
if len(raw)!=261170 or int.from_bytes(raw[:4],"little")!=len(raw)-16:
    raise SystemExit("V1.33: invalid 2D7F container")
if raw[4:6].hex()!="2d7f" or int.from_bytes(raw[10:12],"little")!=11:
    raise SystemExit("V1.33: unexpected 2D7F header")

W,H=240,296
BG_OFF=0x1000
BG_LEN=W*H*2
if BG_OFF+BG_LEN!=0x23B00:
    raise SystemExit("V1.33: background geometry invariant failed")

# Approved Reloj Lab layout:
# black face, white analog ticks, live digital time upper-left,
# live battery upper-right, live steps lower-left, live heart rate lower-right.
S=4
mask=Image.new("L",(W*S,H*S),0)
d=ImageDraw.Draw(mask)
cx,cy=120*S,148*S
for i in range(60):
    ang=math.radians(i*6-90)
    major=(i%5==0)
    ro=91*S
    ri=(75 if major else 85)*S
    d.line((cx+math.cos(ang)*ri,cy+math.sin(ang)*ri,
            cx+math.cos(ang)*ro,cy+math.sin(ang)*ro),
           fill=255,width=(5 if major else 2)*S)

FONT={
 "A":["01110","10001","10001","11111","10001","10001","10001"],
 "L":["10000","10000","10000","10000","10000","10000","11111"],
 "M":["10001","11011","10101","10101","10001","10001","10001"],
 "O":["01110","10001","10001","10001","10001","10001","01110"],
 "P":["11110","10001","10001","11110","10000","10000","10000"],
 "S":["01111","10000","10000","01110","00001","00001","11110"],
 ":":["0","1","0","0","1","0","0"],
 "%":["10001","00010","00100","01000","10000","00000","10001"],
}
def draw_text(text,x,y,scale=1,fill=255):
    xx=x*S
    for ch in text:
        pat=FONT.get(ch)
        if pat is None:
            xx+=4*scale*S
            continue
        pw=max(len(r) for r in pat)
        for ry,row in enumerate(pat):
            for rx,v in enumerate(row):
                if v=="1":
                    d.rectangle((xx+rx*scale*S,y*S+ry*scale*S,
                                 xx+(rx+1)*scale*S-1,y*S+(ry+1)*scale*S-1),fill=fill)
        xx+=(pw+1)*scale*S

draw_text(":",48,15,2,255)
draw_text("%",220,18,1,255)
draw_text("PASOS",10,282,1,255)
draw_text("LPM",176,282,1,255)

mask=mask.resize((W,H),Image.Resampling.LANCZOS)
m=np.array(mask,dtype=np.uint8)
a=((m.astype(np.uint16)*15+127)//255)
# MARKET background pixels are 16-bit ABGR4444. Keep black as 0x0000;
# white graphics use full RGB with alpha from the antialias mask.
pix=np.where(a>0,(a<<12)|0x0FFF,0).astype("<u2")
background=pix.tobytes()
if len(background)!=BG_LEN:
    raise SystemExit("V1.33: background byte count mismatch")

original=bytes(raw)
raw[BG_OFF:BG_OFF+BG_LEN]=background

def u16(buf,o): return int.from_bytes(buf[o:o+2],"little")
def p16(buf,o,v): buf[o:o+2]=int(v).to_bytes(2,"little")

# Parse the original 11 descriptor chain.
descs=[]
off=0x10
for i in range(11):
    kind=u16(original,off+8)
    n=28 if kind==0x1202 else 18 if kind==0x0804 else 12
    descs.append(bytearray(original[off:off+n]))
    off+=n
if off!=0xDA:
    raise SystemExit("V1.33: unexpected original descriptor end")

def numeric(field,x,y,size,fmt):
    r=bytearray(28)
    p16(r,0,0x0164);p16(r,2,x);p16(r,4,y);p16(r,6,size)
    p16(r,8,0x1202);p16(r,10,field)
    txt=(fmt.encode("ascii")+bytes([0]))[:8]
    r[12:20]=txt.ljust(8,bytes([0]))
    return r

# No extra element count is needed: the obsolete battery icon descriptor is
# replaced by the missing live minute field. Dynamic hands remain untouched.
new_descs=[
    descs[0],                              # background 0x0200
    numeric(0x8001,14,18,2,"%02d"),       # live hour
    numeric(0x8002,56,18,2,"%02d"),       # live minute
    numeric(0x8013,178,20,1,"%03d"),      # live battery
    numeric(0x8009,10,255,1,"%05d"),      # live steps
    numeric(0x800E,166,255,1,"%03d"),     # live heart rate
    descs[6],                              # hour hand, live 0x8001
    descs[7],                              # minute hand, live 0x8002
    descs[8],                              # center graphic
    descs[9],                              # live second hand
    descs[10],                             # center cap
]
if len(new_descs)!=11:
    raise SystemExit("V1.33: descriptor count changed")

raw[0x10:0x800]=bytes(0x800-0x10)
pos=0x10
for rec in new_descs:
    raw[pos:pos+len(rec)]=rec
    pos+=len(rec)
if pos!=0xEA:
    raise SystemExit("V1.33: custom descriptor end mismatch")

# Restore fixed header and resource table invariants.
raw[:0x10]=original[:0x10]
if raw[0x800:0x1000]!=original[0x800:0x1000]:
    raise SystemExit("V1.33: resource table changed unexpectedly")
if raw[0x23B00:]!=original[0x23B00:]:
    raise SystemExit("V1.33: dynamic resource payload changed unexpectedly")

def ids_from_candidate(buf):
    ids=[];kinds=[];off=0x10
    for _ in range(u16(buf,10)):
        kind=u16(buf,off+8);n=28 if kind==0x1202 else 18 if kind==0x0804 else 12
        kinds.append(kind)
        if kind==0x1202: ids.append(u16(buf,off+10))
        off+=n
    return ids,kinds,off

ids,kinds,end=ids_from_candidate(raw)
for field in (0x8001,0x8002,0x8009,0x800E,0x8013):
    if field not in ids:
        raise SystemExit("V1.33: missing live field "+hex(field))
if kinds.count(0x0203)!=2 or kinds.count(0x0804)!=1:
    raise SystemExit("V1.33: analog live engine was not preserved")

# Variant A changes only the market identity so WATCH_FACE_INFO can prove that
# the custom payload was accepted. Variant B keeps the proven 2D7F identity as
# a fallback overwrite path if this firmware validates the known ID.
verified=bytearray(raw); verified[4:6]=bytes.fromhex("4cc6")
same_id=bytearray(raw); same_id[4:6]=bytes.fromhex("2d7f")
fallback=bytes(original)

variants=[
    ("custom_verified","4cc6",bytes(verified)),
    ("custom_same_id","2d7f",bytes(same_id)),
    ("oem_recovery","2d7f",fallback),
]
manifest={
 "version":"1.33.0",
 "design":"approved Reloj Lab black analog face",
 "resolution":[240,296],
 "background_format":"ABGR4444",
 "background_range":[BG_OFF,BG_OFF+BG_LEN],
 "descriptor_end":end,
 "live_fields":{
   "digital_hour":"0x8001 upper-left",
   "digital_minute":"0x8002 upper-left",
   "battery":"0x8013 upper-right",
   "steps":"0x8009 lower-left",
   "heart_rate":"0x800E lower-right",
   "analog_hour":"0x0203 / 0x8001",
   "analog_minute":"0x0203 / 0x8002",
   "analog_second":"0x0804"
 },
 "variants":[]
}
ASSETS.mkdir(parents=True,exist_ok=True)
for role,binid,data in variants:
    sha=hashlib.sha256(data).hexdigest()
    name=f"face_v133_{role}.b64"
    (ASSETS/name).write_text(base64.b64encode(zlib.compress(data,9)).decode("ascii"),encoding="ascii")
    manifest["variants"].append({
      "role":role,"bin_id_hex":binid,"file":name,
      "raw_size":len(data),"raw_sha256":sha,
      "custom":role!="oem_recovery"
    })
# preview for CI/debug only
mask.convert("RGB").save(ASSETS/"face_v133_background_preview.png")
(ASSETS/"face_v133.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(manifest,ensure_ascii=False,indent=2))
