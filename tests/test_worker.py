import ast
import asyncio
import queue
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
source=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8'))
cls=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='App')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run_async')
namespace={'asyncio':asyncio}
exec(compile(ast.Module(body=[method],type_ignores=[]),'worker','exec'),namespace)
App=type('App',(),{'run_async':namespace['run_async']})

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

