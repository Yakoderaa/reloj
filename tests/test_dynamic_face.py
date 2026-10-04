import ast, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V141Tests(unittest.TestCase):
    def test_lock_migration_complete(self):
        s=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.41.0"',s)
        self.assertNotIn("single_face_install",s)
        self.assertIn('rep["single_face_lock"]["notify_recovery"]',s)
        self.assertIn("FIJAR ESFERA ACTUAL COMO ÚNICA",s)
        self.assertIn("face-lock.json",s)
        self.assertIn("matches_target",s)
        self.assertIn("DETENER BLOQUEO",s)
        ast.parse(s)
if __name__=="__main__": unittest.main()
