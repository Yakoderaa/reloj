import ast, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V140Tests(unittest.TestCase):
    def test_version_and_lock_mode(self):
        s=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.40.0"',s)
        self.assertIn("FIJAR ESFERA ACTUAL COMO ÚNICA",s)
        self.assertIn("face-lock.json",s)
        self.assertIn("matches_target",s)
        self.assertIn("DETENER BLOQUEO",s)
        self.assertIn("corrections",s)
        ast.parse(s)
if __name__=="__main__": unittest.main()
