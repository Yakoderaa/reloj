import base64, hashlib, json, zlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def u16(raw,o): return int.from_bytes(raw[o:o+2],'little')

def rec_len(raw,off):
    if u16(raw,off)!=0x0164: raise AssertionError(hex(off))
    kind=u16(raw,off+8)
    return 28 if kind==0x1202 else 18 if kind==0x0804 else 12

def chain(raw,count):
    off=0x10; starts=[]
    for _ in range(count):
        starts.append(off); off+=rec_len(raw,off)
    return starts,off

def find_field(raw,field):
    starts,_=chain(raw,u16(raw,10))
    for off in starts:
        if rec_len(raw,off)==28 and u16(raw,off+8)==0x1202 and u16(raw,off+10)==field:
            return off
    return None

class DynamicFaceTests(unittest.TestCase):
    def load(self):
        return zlib.decompress(base64.b64decode((ROOT/'assets'/'target_face_v123.b64').read_text(encoding='ascii').strip()))

    def test_v123_market_table_is_contiguous(self):
        raw=self.load()
        self.assertEqual(int.from_bytes(raw[:4],'little'),len(raw)-16)
        self.assertEqual(raw[4:6].hex(),'4cc6')
        self.assertEqual(u16(raw,10),12)
        starts,end=chain(raw,12)
        self.assertEqual(starts[:7],[0x10,0x1c,0x28,0x34,0x40,0x4c,0x5e])
        self.assertEqual(starts[7],0x6a)
        self.assertEqual(starts[7:],[0x6a,0x86,0xa2,0xbe,0xda])
        self.assertEqual(end,0xf6)
        self.assertNotEqual(raw[0x6a:0x6c],bytes(2))

    def test_v123_has_all_live_fields(self):
        raw=self.load()
        for field in (0x8001,0x8002,0x8009,0x800E,0x8013):
            self.assertIsNotNone(find_field(raw,field),hex(field))
        meta=json.loads((ROOT/'assets'/'target_face_v123.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['raw_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertTrue(meta['checks']['descriptor_chain_contiguous'])
        self.assertTrue(meta['checks']['no_alignment_gap'])

    def test_app_never_selects_market_before_registration(self):
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('APP_VERSION="1.23.0"',source)
        self.assertIn('transfer_slot(3,"DYNAMIC-MARKET"',source)
        guard='if not registration_ok:'
        select='_,sel_status,_=await tx83_wait(bytes([1,market_index&255]),3.0)'
        self.assertIn(guard,source); self.assertIn(select,source)
        self.assertLess(source.index(guard),source.index(select))
        self.assertIn('NO se selecciona ningún slot viejo',source)

if __name__=='__main__':
    unittest.main()
