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
    def test_v121_is_real_market_face_with_live_fields(self):
        raw=zlib.decompress(base64.b64decode((ROOT/'assets'/'target_face_v121.b64').read_text(encoding='ascii').strip()))
        self.assertEqual(int.from_bytes(raw[:4],'little'),len(raw)-16)
        self.assertEqual(raw[4:6].hex(),'4cc6')
        self.assertEqual(u16(raw,10),12)
        for field in (0x8001,0x8002,0x8009,0x800E,0x8013):
            self.assertIsNotNone(find_field(raw,field),hex(field))
        meta=json.loads((ROOT/'assets'/'target_face_v121.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['raw_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(meta['bin_id_hex'],'4cc6')
        self.assertTrue(meta['checks']['all_pass'])

    def test_approved_layout_fields_are_encoded(self):
        raw=zlib.decompress(base64.b64decode((ROOT/'assets'/'target_face_v121.b64').read_text(encoding='ascii').strip()))
        expected={0x8001:(18,24),0x8002:(54,16),0x8013:(178,24),0x8009:(10,255),0x800E:(160,255)}
        for field,xy in expected.items():
            off=find_field(raw,field)
            self.assertEqual((u16(raw,off+2),u16(raw,off+4)),xy)

    def test_app_uses_market_cmd3_and_market_selection(self):
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('APP_VERSION="1.21.0"',source)
        self.assertIn('transfer_slot(3,"DYNAMIC-MARKET"',source)
        self.assertIn('market_index=face_slots.get("market_index")',source)
        self.assertIn('expected_market_bin_id_hex',source)
        self.assertNotIn('transfer_slot(2,"DYNAMIC-CUSTOMIZE"',source)

if __name__=='__main__':
    unittest.main()
