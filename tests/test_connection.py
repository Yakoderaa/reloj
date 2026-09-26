"""Exercise actual connection and worker methods without a Bluetooth adapter or GUI."""
import ast
import asyncio
import queue
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

source=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8'))
app_node=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='App')
namespace={'asyncio':asyncio, 'threading':threading}
exec(compile(ast.Module(body=[app_node],type_ignores=[]),'app.py','exec'),namespace)
App=namespace['App']

class ConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_name_does_not_select_another_watch(self):
        wanted=SimpleNamespace(address='AA',name='Apple Watch Ultra')
        wrong=SimpleNamespace(address='BB',name='Apple Watch Ultra')
        class Scanner:
            @staticmethod
            async def discover(**kw):return [wrong,wanted]
        class Client:
            def __init__(self,target,**kw):self.target=target; self.is_connected=False; self.services=[]
            async def connect(self):self.is_connected=True
        namespace.update(BleakScanner=Scanner,BleakClient=Client)
        app=App.__new__(App); app.selected={'address':'AA','device':wanted}
        progress=[]
        client,attempt=await app.connect_retry(1,progress.append)
        self.assertIs(client.target,wanted)
        self.assertEqual(attempt,1)
        self.assertEqual(len(progress),2)

    async def test_error_is_reported_and_client_disconnected(self):
        disconnected=[]
        class Scanner:
            @staticmethod
            async def discover(**kw):return []
        class Client:
            def __init__(self,*args,**kw):pass
            async def connect(self):raise TimeoutError('GATT timeout')
            async def disconnect(self):disconnected.append(True)
        namespace.update(BleakScanner=Scanner,BleakClient=Client)
        app=App.__new__(App); app.selected={'address':'AA','device':None}
        progress=[]
        with self.assertRaisesRegex(RuntimeError,'GATT timeout'):
            await app.connect_retry(1,progress.append)
        self.assertEqual(disconnected,[True])
        self.assertTrue(any('TimeoutError' in x for x in progress))

    async def test_second_operation_is_rejected(self):
        app=App.__new__(App); app.ble_busy=True
        async def job():raise AssertionError('must not execute')
        task=job(); errors=[]
        app.run_async(task,lambda result,error:errors.append(error))
        self.assertIsInstance(errors[0],RuntimeError)
        self.assertIsNone(task.cr_frame)

class WorkerTests(unittest.TestCase):
    def test_success_and_failure_share_loop_and_release_busy_state(self):
        app=App.__new__(App); app.ble_busy=False
        app.tree=SimpleNamespace(state=lambda x:None)
        app.ui_queue=queue.Queue(); app.ble_loop=asyncio.new_event_loop()
        thread=threading.Thread(target=app.ble_loop.run_forever)
        thread.start()
        results=[]
        try:
            async def success():return asyncio.get_running_loop()
            app.run_async(success(),lambda r,e:results.append((r,e)))
            app.ui_queue.get(timeout=3)()
            self.assertIs(results[-1][0],app.ble_loop)
            self.assertFalse(app.ble_busy)
            async def failure():raise ValueError('test')
            app.run_async(failure(),lambda r,e:results.append((r,e)))
            app.ui_queue.get(timeout=3)()
            self.assertIsInstance(results[-1][1],ValueError)
            self.assertFalse(app.ble_busy)
        finally:
            app.ble_loop.call_soon_threadsafe(app.ble_loop.stop)
            thread.join(timeout=3); app.ble_loop.close()

if __name__=='__main__':unittest.main()
