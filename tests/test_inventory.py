"""Exercise the release's actual read-only inspection method with BLE doubles."""
import ast
import asyncio
import runpy
import tempfile
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as folder:
    old=os.getcwd()
    try:
        os.chdir(folder)
        Path('app.py').write_text((ROOT/'app.py').read_text(encoding='utf-8'),encoding='utf-8')
        runpy.run_path(str(ROOT/'build_patch_v029.py'))
        source=ast.parse(Path('app.py').read_text(encoding='utf-8'))
    finally:
        os.chdir(old)
cls=next(n for n in source.body if isinstance(n,ast.ClassDef))
method=next(n for n in cls.body if n.name=='inspect_gatt_snapshot')
namespace={'asyncio':asyncio}
exec(compile(ast.Module(body=[method],type_ignores=[]),'inspection','exec'),namespace)

class InventoryTests(unittest.IsolatedAsyncioTestCase):
    async def inspect(self,services=(),failure=False):
        closed=[]
        class Scanner:
            @staticmethod
            async def find_device_by_address(address,**kw):
                self.assertEqual(address,'selected')
                return SimpleNamespace(address=address)
        class Client:
            def __init__(self,target,**kw):
                self.services=services
                self.is_connected=True
            async def connect(self):
                if failure: raise RuntimeError('connect failure')
            async def disconnect(self): closed.append(True)
            async def write_gatt_char(self,*a,**kw): raise AssertionError('unexpected write')
            async def start_notify(self,*a,**kw): raise AssertionError('unexpected subscription')
        namespace.update(BleakScanner=Scanner,BleakClient=Client)
        result=await namespace['inspect_gatt_snapshot'](SimpleNamespace(selected={'address':'selected'}),lambda line:None)
        self.assertEqual(closed,[True])
        return result

    async def test_missing_b001_is_reported_without_subscription(self):
        result=await self.inspect()
        self.assertFalse(result['present']['B001'])
        self.assertEqual(result['errors'],[])

    async def test_present_b001_is_recorded(self):
        char=SimpleNamespace(uuid='0000b001-0000-1000-8000-00805f9b34fb',handle=3,properties=['notify'])
        result=await self.inspect([SimpleNamespace(uuid='service',characteristics=[char])])
        self.assertTrue(result['present']['B001'])
        self.assertEqual(result['services'][0]['characteristics'][0]['handle'],3)

    async def test_connection_error_still_closes_client(self):
        result=await self.inspect(failure=True)
        self.assertIn('connect failure',result['errors'][0])

if __name__=='__main__': unittest.main()

