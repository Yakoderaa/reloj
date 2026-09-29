import base64, hashlib, json, zlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OEM_SHA="ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a"

def load_asset(name):
    return zlib.decompress(base64.b64decode((ROOT/"assets"/name).read_text(encoding="ascii").strip()))

class MinimalPatchV128Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((ROOT/"assets"/"face_v128.json").read_text(encoding="utf-8"))
        cls.by_role={x["role"]:x for x in cls.meta["variants"]}

    def test_manifest_strategy(self):
        self.assertEqual(self.meta["version"],"1.28.0")
        self.assertEqual(self.meta["strategy"],"minimal pixel-only patch over proven OEM 2D7F")
        self.assertTrue(self.meta["metadata_byte_exact"])
        self.assertTrue(self.meta["descriptor_table_byte_exact"])
        self.assertTrue(self.meta["resource_table_byte_exact"])
        self.assertTrue(self.meta["dynamic_tail_byte_exact"])

    def test_only_background_differs_from_oem(self):
        custom=load_asset(self.by_role["minimal_patch"]["file"])
        oem=load_asset(self.by_role["oem_recovery"]["file"])
        self.assertEqual(hashlib.sha256(oem).hexdigest(),OEM_SHA)
        self.assertEqual(custom[4:6],bytes.fromhex("2d7f"))
        self.assertEqual(oem[4:6],bytes.fromhex("2d7f"))
        self.assertEqual(custom[:0x1000],oem[:0x1000])
        self.assertEqual(custom[0x23B00:],oem[0x23B00:])
        self.assertNotEqual(custom[0x1000:0x23B00],oem[0x1000:0x23B00])
        self.assertEqual(len(custom),len(oem))
        self.assertEqual(int.from_bytes(custom[:4],"little"),len(custom)-16)

    def test_descriptor_and_resource_tables_are_byte_exact(self):
        custom=load_asset(self.by_role["minimal_patch"]["file"])
        oem=load_asset(self.by_role["oem_recovery"]["file"])
        self.assertEqual(custom[0x10:0x800],oem[0x10:0x800])
        self.assertEqual(custom[0x800:0x1000],oem[0x800:0x1000])

    def test_app_uses_one_minimal_patch_then_oem_recovery(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.28.0"',source)
        self.assertIn("build_minpatch_market_v128",source)
        self.assertIn("RELOJ-LAB-MINPATCH",source)
        self.assertIn("OEM-RECOVERY-2D7F",source)
        self.assertIn("acceptance_rule",source)
        self.assertIn("cmd3 must remain 2d7f",source)
        self.assertIn("minimal_patch_accepted_and_selected",source)

    def test_control_active_toolbar_is_still_present(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('def open_control(self):',source)
        self.assertIn('def capture():',source)
        self.assertIn('def ota_lab(pair=False):',source)
        self.assertIn('REPARAR VÍNCULO E INSTALAR V1.28',source)
        self.assertIn('COPIAR DIAGNÓSTICO',source)
        self.assertIn('ENVIAR HEX',source)

if __name__=="__main__":
    unittest.main()
