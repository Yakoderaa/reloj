import ast, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V142Tests(unittest.TestCase):
    def test_permanent_profile_mode(self):
        s=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.42.0"',s)
        self.assertIn("PREPARAR BLOQUEO PERMANENTE",s)
        self.assertIn("permanent-lock-profile.json",s)
        self.assertIn("face-lock.json",s)
        self.assertIn("standard_reads",s)
        self.assertIn("FIJAR ESFERA ACTUAL COMO ÚNICA",s)
        ast.parse(s)
if __name__=="__main__": unittest.main()
