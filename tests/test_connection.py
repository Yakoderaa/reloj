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
            async def find_device_by_address(address,**kw):return wanted
        class Client:
            def __init__(self,target,**kw):self.target=target; self.is_connected=False; self.services=[]
            async def connect(self):self.is_connected=True
        namespace.update(BleakScanner=Scanner,BleakClient=Client)
        app=App.__new__(App); app.selected={'address':'AA','device':wrong}
        progress=[]
        client,attempt=await app.connect_retry(1,progress.append)
        self.assertIs(client.target,wanted)
        self.assertEqual(attempt,1)
        self.assertTrue(any("detectado nuevamente" in x for x in progress))

    async def test_error_is_reported_and_client_disconnected(self):
        disconnected=[]
        class Scanner:
            @staticmethod
            async def find_device_by_address(address,**kw):return SimpleNamespace(address=address)
        class Client:
            def __init__(self,*args,**kw):pass
            async def connect(self):raise TimeoutError('GATT timeout')
            async def disconnect(self):disconnected.append(True)
        namespace.update(BleakScanner=Scanner,BleakClient=Client)
        app=App.__new__(App); app.selected={'address':'AA','device':None}
        progress=[]
        with self.assertRaisesRegex(RuntimeError,'TIEMPO DE CONEXIÓN AGOTADO'):
            await app.connect_retry(1,progress.append)
        self.assertEqual(disconnected,[True])
        self.assertTrue(any('TIEMPO DE CONEXIÓN AGOTADO' in x for x in progress))
        self.assertEqual(app.connection_state['attempts'],1)

    async def test_saved_ble_device_connects_without_another_scan(self):
        wanted=SimpleNamespace(address='AA',name='Apple Watch Ultra')
        class Scanner:
            @staticmethod
            async def find_device_by_address(*args,**kw):raise AssertionError('implicit rescan')
        class Client:
            def __init__(self,target,**kw):
                if isinstance(target,str):raise AssertionError('address string triggers implicit scan')
                self.target=target; self.is_connected=False; self.services=[]
            async def connect(self):self.is_connected=True
        namespace.update(BleakScanner=Scanner,BleakClient=Client)
        app=App.__new__(App);app.selected={'address':'AA','device':wanted}
        client,n=await app.connect_retry(1)
        self.assertIs(client.target,wanted)
        self.assertTrue(app.connection_state['connected'])

    async def test_missing_advertisement_does_not_attempt_gatt(self):
        class Scanner:
            @staticmethod
            async def find_device_by_address(*args,**kw):return None
        class Client:
            def __init__(self,*args,**kw):raise AssertionError('must not connect')
        namespace.update(BleakScanner=Scanner,BleakClient=Client)
        app=App.__new__(App);app.selected={'address':'AA','device':None}
        with self.assertRaisesRegex(RuntimeError,'RELOJ NO VISIBLE'):
            await app.connect_retry(1)
        self.assertEqual(app.connection_state['phase'],'scanning')

    async def test_failed_direct_connection_recovers_with_fresh_device(self):
        old=SimpleNamespace(address='AA');fresh=SimpleNamespace(address='AA')
        targets=[];disconnected=[]
        class Scanner:
            @staticmethod
            async def find_device_by_address(*args,**kw):return fresh
        class Client:
            def __init__(self,target,**kw):
                targets.append(target);self.target=target;self.is_connected=False;self.services=[]
            async def connect(self):
                if self.target is old:raise RuntimeError('old device failed')
                self.is_connected=True
            async def disconnect(self):disconnected.append(self.target)
        namespace.update(BleakScanner=Scanner,BleakClient=Client)
        app=App.__new__(App);app.selected={'address':'AA','device':old}
        client,n=await app.connect_retry(2)
        self.assertEqual(targets,[old,fresh]);self.assertEqual(disconnected,[old])
        self.assertEqual(n,2);self.assertIs(app.selected['device'],fresh)

    async def test_cancelled_connect_disconnects_client(self):
        started=asyncio.Event();disconnected=[]
        class Client:
            def __init__(self,*args,**kw):pass
            async def connect(self):started.set();await asyncio.Event().wait()
            async def disconnect(self):disconnected.append(True)
        namespace['BleakClient']=Client
        app=App.__new__(App);app.selected={'address':'AA','device':SimpleNamespace(address='AA')}
        task=asyncio.create_task(app.connect_retry(1))
        await started.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(disconnected,[True])

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
