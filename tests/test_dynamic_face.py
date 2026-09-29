import base64, hashlib, json, zlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def u16(b,o): return int.from_bytes(b[o:o+2],"little")

def load_asset(name):
    return zlib.decompress(base64.b64decode((ROOT/"assets"/name).read_text(encoding="ascii").strip()))

def parse_descs(raw):
    count=u16(raw,10);off=0x10;rows=[]
    for _ in range(count):
        kind=u16(raw,off+8)
        n=28 if kind==0x1202 else 18 if kind==0x0804 else 12
        row={"off":off,"kind":kind,"x":u16(raw,off+2),"y":u16(raw,off+4),"size":u16(raw,off+6)}
        if kind==0x1202:
            row["field"]=u16(raw,off+10)
            row["fmt"]=raw[off+12:off+20].split(bytes([0]),1)[0].decode("ascii")
        elif kind==0x0203:
            row["field"]=u16(raw,off+10)
        rows.append(row);off+=n
    return rows,off

class ApprovedFaceV127Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((ROOT/"assets"/"face_v126.json").read_text(encoding="utf-8"))
        cls.by_role={x["role"]:x for x in cls.meta["variants"]}

    def test_manifest_and_three_paths(self):
        self.assertEqual(self.meta["version"],"1.26.0")
        self.assertEqual(self.meta["design"],"approved Reloj Lab black analog face")
        self.assertEqual(set(self.by_role),{"custom_verified","custom_same_id","oem_recovery"})
        self.assertEqual(self.by_role["custom_verified"]["bin_id_hex"],"4cc6")
        self.assertEqual(self.by_role["custom_same_id"]["bin_id_hex"],"2d7f")

    def test_custom_payload_preserves_dynamic_engine_and_has_all_live_data(self):
        spec=self.by_role["custom_same_id"]
        raw=load_asset(spec["file"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),spec["raw_sha256"])
        self.assertEqual(raw[4:6].hex(),"2d7f")
        self.assertEqual(int.from_bytes(raw[:4],"little"),len(raw)-16)
        self.assertEqual(u16(raw,10),11)
        rows,end=parse_descs(raw)
        self.assertEqual(end,0xEA)
        numeric={r["field"]:r for r in rows if r["kind"]==0x1202}
        self.assertEqual((numeric[0x8001]["x"],numeric[0x8001]["y"]),(12,16))
        self.assertEqual((numeric[0x8002]["x"],numeric[0x8002]["y"]),(58,16))
        self.assertEqual((numeric[0x8013]["x"],numeric[0x8013]["y"]),(178,16))
        self.assertEqual((numeric[0x8009]["x"],numeric[0x8009]["y"]),(10,258))
        self.assertEqual((numeric[0x800E]["x"],numeric[0x800E]["y"]),(166,258))
        analog=[r for r in rows if r["kind"]==0x0203]
        self.assertEqual([r["field"] for r in analog],[0x8001,0x8002])
        self.assertEqual(sum(1 for r in rows if r["kind"]==0x0804),1)

    def test_background_is_custom_black_monochrome_layer(self):
        raw=load_asset(self.by_role["custom_same_id"]["file"])
        bg=raw[0x1000:0x23B00]
        self.assertEqual(len(bg),240*296*2)
        vals=[int.from_bytes(bg[i:i+2],"little") for i in range(0,len(bg),2)]
        self.assertIn(0,vals)
        self.assertIn(0xFFFF,vals)
        # Every nonzero pixel is white in RGB nibbles; alpha may vary for antialiasing.
        for v in vals[::97]:
            if v:
                self.assertEqual(v & 0x0FFF,0x0FFF)

    def test_verified_variant_only_changes_identity_from_same_id_variant(self):
        a=bytearray(load_asset(self.by_role["custom_verified"]["file"]))
        b=bytearray(load_asset(self.by_role["custom_same_id"]["file"]))
        self.assertEqual(a[4:6].hex(),"4cc6")
        self.assertEqual(b[4:6].hex(),"2d7f")
        a[4:6]=b[4:6]
        self.assertEqual(a,b)

    def test_oem_recovery_is_exact_2d7f(self):
        spec=self.by_role["oem_recovery"]
        raw=load_asset(spec["file"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a")

    def test_app_uses_custom_face_and_visual_check_fallback(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.27.0"',source)
        self.assertIn("build_custom_market_v127",source)
        self.assertIn("NUESTRA esfera aprobada V1.27",source)
        self.assertIn("custom_verified",source)
        self.assertIn("custom_same_id",source)
        self.assertIn("same_id_overwrite_requires_visual_confirmation",source)
        self.assertIn("approved_face_verified_and_selected",source)

if __name__=="__main__":
    unittest.main()


class ControlActiveV127Tests(unittest.TestCase):
    def test_control_active_toolbar_restored(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('def open_control(self):',source)
        self.assertIn('def capture():',source)
        self.assertIn('def ota_lab(pair=False):',source)
        self.assertIn('REPARAR VÍNCULO E INSTALAR V1.27',source)
        self.assertIn('COPIAR DIAGNÓSTICO',source)
        self.assertIn('ENVIAR HEX',source)
        self.assertIn('MAPEO DIFERENCIAL',source)
        self.assertIn('SONDEO PROFUNDO',source)
        self.assertIn('INSTALAR SIN REPARAR',source)

    def test_capture_is_not_replaced_by_installer(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        capture_start=source.index('        def capture():')
        ota_start=source.index('        def ota_lab(pair=False):')
        capture_block=source[capture_start:ota_start]
        self.assertIn('CAPTURA 90 s',capture_block)
        self.assertIn('await asyncio.sleep(1)',capture_block)
        self.assertNotIn('build_custom_market_v127',capture_block)
        self.assertNotIn('single_face_install',capture_block)
