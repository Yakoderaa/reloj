import base64, hashlib, json, zlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def u16(raw,o): return int.from_bytes(raw[o:o+2],'little')

def find_field(raw,field):
    for off in range(0x10,0x800-28):
        if u16(raw,off)==0x0164 and u16(raw,off+8)==0x1202 and u16(raw,off+10)==field:
            return off
    return None

class DynamicFaceTests(unittest.TestCase):
    def test_v120_market_asset_contains_live_fields(self):
        raw=zlib.decompress(base64.b64decode((ROOT/'assets'/'target_face_v120.b64').read_text(encoding='ascii').strip()))
        self.assertEqual(int.from_bytes(raw[:4],'little'),len(raw)-16)
        self.assertEqual(u16(raw,10),13)
        for field in (0x8001,0x8002,0x8009,0x800E,0x8013):
            self.assertIsNotNone(find_field(raw,field),hex(field))
        meta=json.loads((ROOT/'assets'/'target_face_v120.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['raw_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertTrue(meta['checks']['all_pass'])

    def test_approved_positions_are_encoded(self):
        raw=zlib.decompress(base64.b64decode((ROOT/'assets'/'target_face_v120.b64').read_text(encoding='ascii').strip()))
        expected={0x8001:(12,24),0x8002:(42,24),0x8013:(178,28),0x8009:(10,260),0x800E:(158,260)}
        for field,xy in expected.items():
            off=find_field(raw,field)
            self.assertEqual((u16(raw,off+2),u16(raw,off+4)),xy)

    def test_app_uses_dynamic_market_custom_slot(self):
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('APP_VERSION="1.20.0"',source)
        self.assertIn('DYNAMIC-CUSTOMIZE',source)
        self.assertIn('MARKET field 0x8013',source)
        self.assertNotIn('build_live_customize',source)

if __name__=='__main__':
    unittest.main()
