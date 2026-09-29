import base64, hashlib, json, zlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class NativeMarketTests(unittest.TestCase):
    EXPECTED={
        "4cc6":"52f9a9857929fc64791551010eb0eaf2ad03f5e280f9e9d36701f1fdc07d1b2b",
        "2d7f":"ad27959066b73c522dba4dedb0aa78a0c01681cddafc32a3d461d51a72b4c13a",
    }

    def load(self,binid):
        p=ROOT/'assets'/f'market_native_{binid}_v124.b64'
        return zlib.decompress(base64.b64decode(p.read_text(encoding='ascii').strip()))

    def test_embedded_candidates_are_byte_exact_native_files(self):
        for binid,sha in self.EXPECTED.items():
            raw=self.load(binid)
            self.assertEqual(raw[4:6].hex(),binid)
            self.assertEqual(int.from_bytes(raw[:4],'little'),len(raw)-16)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),sha)

    def test_manifest_marks_both_candidates_byte_for_byte(self):
        meta=json.loads((ROOT/'assets'/'market_native_v124.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['version'],'1.24.0')
        self.assertEqual([x['bin_id_hex'] for x in meta['candidates']],['4cc6','2d7f'])
        self.assertTrue(all(x['byte_for_byte'] for x in meta['candidates']))

    def test_app_tries_native_market_and_never_selects_before_registration(self):
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('APP_VERSION="1.24.0"',source)
        self.assertIn('build_native_market_v124',source)
        self.assertIn('OEM-MARKET-',source)
        self.assertIn('"byte_for_byte":True',source)
        self.assertIn('if not registration_ok:',source)
        self.assertIn('Ningún MARKET OEM fue registrado; NO se selecciona ninguna esfera vieja.',source)
        self.assertIn('market_id_ok(selected_info,market_bin_id)',source)

    def test_v124_does_not_embed_synthesized_target_market(self):
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertNotIn('target_face_v123.b64',source)
        self.assertNotIn('approved-market-v123.bin',source)
        self.assertNotIn('descriptor_chain_contiguous',source)

if __name__=='__main__':
    unittest.main()
