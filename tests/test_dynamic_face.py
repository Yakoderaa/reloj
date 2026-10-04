import ast, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V143Tests(unittest.TestCase):
    def test_reconnect_guard(self):
        s=(ROOT/"app.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION="1.43.0"',s)
        self.assertIn("start_saved_face_guard_if_available",s)
        self.assertIn("saved_face_guard_loop",s)
        self.assertIn("face_guard_enabled",s)
        self.assertIn("esperando que el reloj vuelva a encender",s)
        self.assertIn("face-lock.json",s)
        ast.parse(s)
if __name__=="__main__": unittest.main()
