import base64, hashlib, json, zlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class DynamicFaceTests(unittest.TestCase):
    def test_v120_dynamic_asset_contains_all_live_bindings(self):
        raw=zlib.decompress(base64.b64decode((ROOT/'assets'/'target_face_v120.b64').read_text(encoding='ascii').strip()))
        self.assertEqual(raw[:2],b'WF')
        self.assertEqual(int.from_bytes(raw[0x2a:0x2c],'little'),240)
        self.assertEqual(int.from_bytes(raw[0x2c:0x2e],'little'),296)
        count=int.from_bytes(raw[0x2e:0x30],'little')
        types=[]
        for i in range(count):
            off=54+i*20
            types.append(int.from_bytes(raw[off+2:off+4],'little'))
        required={0x0501,0x0601,0x0701,0x0804,0x0904,0x0A04,0x0B04,
                  0x4104,0x4204,0x4304,0x1102}
        self.assertTrue(required.issubset(set(types)),sorted(hex(x) for x in types))
        meta=json.loads((ROOT/'assets'/'target_face_v120.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['raw_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertTrue(meta['checks']['all_pass'])

    def test_app_uses_dynamic_custom_slot_not_static_raster(self):
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('APP_VERSION="1.20.0"',source)
        self.assertIn('DYNAMIC-CUSTOMIZE',source)
        self.assertIn('WF descriptor 0x0501',source)
        self.assertIn('WF descriptor 0x0601',source)
        self.assertIn('WF descriptor 0x0701',source)
        self.assertNotIn('build_live_customize',source)

if __name__=='__main__':
    unittest.main()
