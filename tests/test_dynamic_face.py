import base64, hashlib, json, zlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OEM_SHA="ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a"

def load_asset(name):
    return zlib.decompress(base64.b64decode((ROOT/"assets"/name).read_text(encoding="ascii").strip()))

class MinimalPatchV129Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((ROOT/"assets"/"face_v128.json").read_text(encoding="utf-8"))
        cls.by_role={x["role"]:x for x in cls.meta["variants"]}

    def test_only_background_differs_from_oem(self):
        custom=load_asset(self.by_role["minimal_patch"]["file"])
        oem=load_asset(self.by_role["oem_recovery"]["file"])
        self.assertEqual(hashlib.sha256(oem).hexdigest(),OEM_SHA)
        self.assertEqual(custom[:0x1000],oem[:0x1000])
        self.assertEqual(custom[0x23B00:],oem[0x23B00:])
        self.assertNotEqual(custom[0x1000:0x23B00],oem[0x1000:0x23B00])
        self.assertEqual(custom[4:6],bytes.fromhex("2d7f"))

    def test_v129_recovers_broken_market_before_patch(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.29.0"',source)
        self.assertIn("OEM-BOOTSTRAP-2D7F",source)
        self.assertIn("bootstrap_oem_recovery",source)
        self.assertIn("OEM 2D7F RESTAURADA",source)
        self.assertIn("RELOJ-LAB-MINPATCH",source)
        self.assertIn("OEM-RECOVERY-2D7F",source)
        self.assertIn("after OEM bootstrap if needed, cmd3 must remain 2d7f",source)

    def test_control_active_toolbar_still_present(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('REPARAR VÍNCULO E INSTALAR V1.29',source)
        self.assertIn('COPIAR DIAGNÓSTICO',source)
        self.assertIn('ENVIAR HEX',source)

if __name__=="__main__":
    unittest.main()
