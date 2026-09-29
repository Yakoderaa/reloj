from pathlib import Path
import base64, hashlib, json, zlib

ASSETS=Path("assets")
DONORS={
    "2D7F":{
        "file":"donor_2D7F.bin",
        "sha256":"ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a",
        "profile":"analog carrier with moving hands, steps, heart rate and battery",
        "live":"analog hour/minute/second + steps + heart rate + battery"
    },
    "4CC6":{
        "file":"donor_4CC6.bin",
        "sha256":"52f9a9857929fc64791551010eb0eaf2ad03f5e280f9e9d36701f1fdc07d1b2b",
        "profile":"fallback black minimal analog",
        "live":"analog hour/minute/second"
    }
}

manifest={"version":"1.25.0","strategy":"byte-for-byte native MARKET bootstrap","candidates":[]}
for binid,spec in DONORS.items():
    raw=(ASSETS/spec["file"]).read_bytes()
    got=hashlib.sha256(raw).hexdigest()
    if got!=spec["sha256"]:
        raise SystemExit(f"{binid}: SHA inesperado {got}")
    if len(raw)<0x800:
        raise SystemExit(f"{binid}: archivo demasiado corto")
    if int.from_bytes(raw[:4],"little")!=len(raw)-16:
        raise SystemExit(f"{binid}: cabecera de tamaño inválida")
    if raw[4:6].hex().upper()!=binid:
        raise SystemExit(f"{binid}: BinID interno {raw[4:6].hex()}")
    out=ASSETS/f"market_native_{binid.lower()}_v124.b64"
    out.write_text(base64.b64encode(zlib.compress(raw,9)).decode("ascii"),encoding="ascii")
    manifest["candidates"].append({
        "bin_id_hex":binid.lower(),
        "source_file":spec["file"],
        "raw_size":len(raw),
        "raw_sha256":got,
        "profile":spec["profile"],
        "live":spec["live"],
        "byte_for_byte":True
    })

(ASSETS/"market_native_v124.json").write_text(
    json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(manifest,ensure_ascii=False,indent=2))
