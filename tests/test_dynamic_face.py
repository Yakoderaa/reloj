import ast, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class DynamicMarketV133Tests(unittest.TestCase):
    def test_app_version_and_market_route(self):
        source=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.33.0"',source)
        self.assertIn("load_dynamic_market_v133",source)
        self.assertIn('transfer_slot(3,"DYNAMIC-MARKET-2D7F"',source)
        self.assertIn('"slot":"MARKET"',source)
        self.assertIn("dynamic_market_face_installed_and_selected",source)
        self.assertNotIn("build_live_customize_v130",source)

    def test_all_required_live_fields_are_declared(self):
        source=(ROOT/"prepare_v133_dynamic.py").read_text(encoding="utf-8")
        for field in ("0x8001","0x8002","0x8009","0x800E","0x8013"):
            self.assertIn(field,source)
        self.assertIn("kinds.count(0x0203)!=2",source)
        self.assertIn("kinds.count(0x0804)!=1",source)

    def test_app_syntax(self):
        ast.parse((ROOT/"app.py").read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()
