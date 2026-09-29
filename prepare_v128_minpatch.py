from pathlib import Path
import base64, hashlib, json, math, zlib
from PIL import Image, ImageDraw
import numpy as np

ASSETS=Path("assets")
DONOR=ASSETS/"donor_2D7F.bin"
OEM_SHA="ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a"
original=DONOR.read_bytes()
if hashlib.sha256(original).hexdigest()!=OEM_SHA:
    raise SystemExit("V1.28: 2D7F donor SHA changed")
if len(original)!=261170 or int.from_bytes(original[:4],"little")!=len(original)-16:
    raise SystemExit("V1.28: invalid 2D7F container")
if original[4:6].hex()!="2d7f":
    raise SystemExit("V1.28: unexpected BinID")

W,H=240,296
BG_OFF=0x1000
BG_END=0x23B00
BG_LEN=BG_END-BG_OFF
if BG_LEN!=W*H*2:
    raise SystemExit("V1.28: background geometry mismatch")

# IMPORTANT: V1.28 changes ONLY the first 240x296 background resource.
# Header, descriptor table, resource table and every dynamic resource remain
# byte-for-byte identical to the OEM 2D7F that the physical watch accepted.
S=4
img=Image.new("RGB",(W*S,H*S),(0,0,0))
d=ImageDraw.Draw(img)
cx,cy=120*S,148*S

# Minimal approved dial: black background, white ticks, restrained red accents.
for i in range(60):
    ang=math.radians(i*6-90)
    major=(i%5==0)
    ro=92*S
    ri=(76 if major else 86)*S
    x1=cx+math.cos(ang)*ri; y1=cy+math.sin(ang)*ri
    x2=cx+math.cos(ang)*ro; y2=cy+math.sin(ang)*ro
    d.line((x1,y1,x2,y2),fill=(255,255,255),width=(5 if major else 2)*S)

# Give the OEM live metric positions quiet labels without moving descriptors.
# 2D7F live values: x/y = steps 38/167, heart 163/125, battery 122/230.
def label_box(x,y,w,h):
    d.rounded_rectangle((x*S,y*S,(x+w)*S,(y+h)*S),radius=4*S,outline=(55,55,55),width=S)

label_box(18,156,70,32)   # steps region
label_box(148,114,70,32)  # heart region
label_box(103,219,72,32)  # battery region

# Small red center dot to match the approved visual language while preserving
# the OEM moving hour/minute/second hand resources.
d.ellipse(((cx-4*S),(cy-4*S),(cx+4*S),(cy+4*S)),fill=(220,0,0))

img=img.resize((W,H),Image.Resampling.LANCZOS)

# The accepted 2D7F background resource is a 16-bit full-screen layer.
# Keep a conservative opaque RGB565 representation; do not touch any metadata.
arr=np.array(img,dtype=np.uint8)
r=(arr[:,:,0].astype(np.uint16)>>3)
g=(arr[:,:,1].astype(np.uint16)>>2)
b=(arr[:,:,2].astype(np.uint16)>>3)
rgb565=((r<<11)|(g<<5)|b).astype("<u2")
background=rgb565.tobytes()
if len(background)!=BG_LEN:
    raise SystemExit("V1.28: background byte count mismatch")

custom=bytearray(original)
custom[BG_OFF:BG_END]=background
custom=bytes(custom)

# Hard regression guards: only the pixel payload may differ.
if custom[:BG_OFF]!=original[:BG_OFF]:
    raise SystemExit("V1.28: metadata before background changed")
if custom[BG_END:]!=original[BG_END:]:
    raise SystemExit("V1.28: dynamic/resource tail changed")
if custom[0x10:0x1000]!=original[0x10:0x1000]:
    raise SystemExit("V1.28: descriptor/resource table changed")
if custom[4:6]!=original[4:6]:
    raise SystemExit("V1.28: BinID changed")

ASSETS.mkdir(parents=True,exist_ok=True)
variants=[
    ("minimal_patch","2d7f",custom,True),
    ("oem_recovery","2d7f",original,False),
]
manifest={
    "version":"1.28.0",
    "strategy":"minimal pixel-only patch over proven OEM 2D7F",
    "design":"approved black analog Reloj Lab visual",
    "resolution":[W,H],
    "background_range":[BG_OFF,BG_END],
    "metadata_byte_exact":True,
    "descriptor_table_byte_exact":True,
    "resource_table_byte_exact":True,
    "dynamic_tail_byte_exact":True,
    "live_features_from_oem":[
        "analog hour hand","analog minute hand","analog second hand",
        "steps 0x8009","heart rate 0x800E","battery 0x8013"
    ],
    "note":"V1.28 intentionally does not move live descriptors; acceptance comes before layout changes.",
    "variants":[]
}
for role,binid,data,is_custom in variants:
    sha=hashlib.sha256(data).hexdigest()
    name=f"face_v128_{role}.b64"
    (ASSETS/name).write_text(base64.b64encode(zlib.compress(data,9)).decode("ascii"),encoding="ascii")
    manifest["variants"].append({
        "role":role,"bin_id_hex":binid,"file":name,
        "raw_size":len(data),"raw_sha256":sha,"custom":is_custom
    })

img.save(ASSETS/"face_v128_preview.png")
(ASSETS/"face_v128.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(manifest,ensure_ascii=False,indent=2))
