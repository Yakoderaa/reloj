import base64, hashlib, zlib, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APPROVED_BASE_SHA="61b86e4f5f998a436c88785e14436b00d797a705dcea6879e96a7828c4cb62a2"

def approved_raw():
    packed=(ROOT/"assets"/"target_face_v086.b64").read_text(encoding="ascii").strip()
    return zlib.decompress(base64.b64decode(packed))

class ExactCustomizeV130Tests(unittest.TestCase):
    def test_approved_asset_is_exact_known_reference(self):
        raw=approved_raw()
        self.assertEqual(len(raw),142090)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),APPROVED_BASE_SHA)
        self.assertEqual(raw[5],2)
        self.assertEqual(int.from_bytes(raw[6:8],"little"),240)
        self.assertEqual(int.from_bytes(raw[8:10],"little"),296)

    def test_app_uses_proven_customize_cmd2_route(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.31.0"',source)
        self.assertIn("build_exact_customize_v130",source)
        self.assertIn("build_live_customize_v130",source)
        self.assertIn('transfer_slot(2,"EXACT-CUSTOMIZE"',source)
        self.assertIn('custom_index=face_slots.get("custom_index")',source)
        self.assertIn("expected_cmd2_hex",source)
        self.assertIn("exact_approved_reference_installed_and_selected",source)

    def test_market_is_not_used_for_custom_artwork(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertNotIn("RELOJ-LAB-MINPATCH",source)
        self.assertIn('"attempted":False',source)
        self.assertIn("ruta CUSTOMIZE cmd=2 físicamente validada",source)

    def test_live_customize_header_matches_proven_metadata(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn("raw[0]=0",source)
        self.assertIn("raw[1]=8",source)
        self.assertIn("raw[2]=4",source)
        self.assertIn('expected_cmd2=raw[:6].hex()',source)
        self.assertIn('raw[3]=0xFF',source)
        self.assertIn('raw[4]=0xFF',source)
        self.assertIn('customize_layout_limit',source)

    def test_control_active_toolbar_still_present(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('REPARAR VÍNCULO E INSTALAR V1.31',source)
        self.assertIn('COPIAR DIAGNÓSTICO',source)
        self.assertIn('ENVIAR HEX',source)

if __name__=="__main__":
    unittest.main()
