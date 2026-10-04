import ast, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V137Tests(unittest.TestCase):
    def test_version_and_market_bootstrap(self):
        s=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.37.0"',s)
        self.assertIn("oem_bootstrap_2d7f",s)
        self.assertIn("market_show_order",s)
        self.assertIn("OEM-BOOTSTRAP-2D7F",s)
        self.assertIn("dynamic_market_oem_bootstrap_then_custom_",s)
        ast.parse(s)
    def test_dynamic_generator(self):
        s=(ROOT/"prepare_v133_dynamic.py").read_text(encoding="utf-8")
        for field in ("0x8001","0x8002","0x8009","0x800E","0x8013"):
            self.assertIn(field,s)
if __name__=="__main__": unittest.main()
