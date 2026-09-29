import asyncio
import importlib.util
import sys
import unittest
from types import SimpleNamespace as NS, ModuleType
from unittest.mock import patch, AsyncMock

if importlib.util.find_spec('bleak') is None:
    stub = ModuleType('bleak')
    stub.BleakClient = stub.BleakScanner = None
    sys.modules['bleak'] = stub
import connection as c


def device(address='AA', kind=1, connectable=True):
    return NS(address=address, name='Watch', details=NS(adv=NS(
        bluetooth_address_type=kind, is_connectable=connectable)))


def advert():
    return NS(service_uuids=[c.E91A], local_name='Watch', rssi=-60)


class ConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = NS(selected={'address': 'AA'})
        self.clients = []
        self.failures = []
        self.gate_failure = False
        self.discover = AsyncMock(return_value={'AA': (device(), advert())})
        self.patches = [patch.object(c, 'BleakScanner', NS(discover=self.discover)),
                        patch.object(c.sys, 'platform', 'win32'),
                        patch.object(c.asyncio, 'sleep', AsyncMock())]
        owner = self
        class Client:
            def __init__(self, target, **kw):
                self.target=target; self.kw=kw; self.closed=False; self.is_connected=False
                self.gate=[]
                self.services=NS(get_characteristic=lambda uuid: NS(descriptors=[NS(uuid=c.CCCD,handle=46)]))
                owner.clients.append(self)
            async def connect(self):
                if owner.failures:
                    error=owner.failures.pop(0)
                    if error: raise error
                self.is_connected=True
            async def read_gatt_descriptor(self, handle, **kwargs):
                self.gate.append(kwargs)
                if owner.gate_failure: raise RuntimeError('Unreachable')
                return b'\0\0'
            async def disconnect(self):
                self.closed=True; self.is_connected=False
        self.patches.append(patch.object(c, 'BleakClient', Client))
        for p in self.patches:p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    async def test_success_uses_observed_address_and_actual_att(self):
        client, n = await c.connect_watch(self.app)
        self.assertEqual(n,1)
        self.assertEqual(client.kw['winrt'],dict(use_cached_services=False,address_type='random'))
        self.assertEqual(client.gate,[{'use_cached':False}])
        self.assertFalse(client.closed)

    async def test_filtered_discovery_avoids_full_catalog_failure(self):
        original = c.BleakClient
        class ScopedClient(original):
            async def connect(inner):
                if inner.kw.get('services') != [c.E91A]:
                    raise TimeoutError('full catalog unavailable')
                await super().connect()
        with patch.object(c, 'BleakClient', ScopedClient):
            client, n = await c.connect_watch(self.app, services=[c.E91A])
        self.assertEqual(n, 1)
        self.assertEqual(client.kw['services'], [c.E91A])
        self.assertEqual(client.gate, [{'use_cached':False}])

    async def test_pairing_is_explicit_and_attempted_only_once(self):
        self.failures=[TimeoutError(),TimeoutError()]
        with self.assertRaises(RuntimeError):
            await c.connect_watch(self.app, services=[c.E91A], pair=True)
        self.assertEqual(len(self.clients),1)
        self.assertTrue(self.clients[0].kw['pair'])
        self.assertEqual(self.clients[0].kw['timeout'],60)
        self.assertTrue(self.clients[0].closed)

    async def test_normal_connection_does_not_request_pairing(self):
        client,_=await c.connect_watch(self.app)
        self.assertNotIn('pair',client.kw)

    async def test_general_diagnostics_keep_full_catalog(self):
        client, _ = await c.connect_watch(self.app)
        self.assertNotIn('services', client.kw)

    async def test_native_logs_are_attributed_to_each_attempt(self):
        import logging
        logger = logging.getLogger('bleak.backends.winrt.client')
        previous_level, previous_handlers = logger.level, list(logger.handlers)
        original = c.BleakClient
        count = 0
        class LoggedClient(original):
            async def connect(inner):
                nonlocal count
                count += 1
                logger.debug('native attempt %s', count)
                if count == 1: raise TimeoutError()
                await super().connect()
        with patch.object(c, 'BleakClient', LoggedClient):
            await c.connect_watch(self.app, services=[c.E91A])
        rows = self.app.connection_state['history']
        self.assertEqual(rows[0]['native'][0]['message'], 'native attempt 1')
        self.assertEqual(rows[1]['native'][0]['message'], 'native attempt 2')
        self.assertEqual(logger.level, previous_level)
        self.assertEqual(logger.handlers, previous_handlers)

    async def test_timeout_disposes_disconnected_client_then_recovers(self):
        self.failures=[TimeoutError()]
        client,n=await c.connect_watch(self.app,7)
        self.assertEqual(n,2)
        self.assertTrue(self.clients[0].closed)
        self.assertTrue(client.kw['winrt']['use_cached_services'])
        self.assertIn('connect_and_services',self.app.connection_state['history'][0]['error'])

    async def test_repeated_timeouts_stop_at_two_without_system_exit(self):
        self.failures=[TimeoutError(),TimeoutError()]
        with self.assertRaisesRegex(RuntimeError,'La esfera no se transfirió'):
            await c.connect_watch(self.app,7)
        self.assertEqual(len(self.clients),2)
        self.assertTrue(all(x.closed for x in self.clients))
        self.assertEqual(self.app.connection_state['phase'],'failed')

    async def test_cached_catalog_is_insufficient_when_att_fails(self):
        self.gate_failure=True
        with self.assertRaises(RuntimeError):await c.connect_watch(self.app)
        self.assertTrue(all(x.closed for x in self.clients))
        self.assertFalse(self.app.connection_state['connected'])
        self.assertTrue(all(x['phase']=='att_read' for x in self.app.connection_state['history']))

    async def test_other_watch_is_never_substituted(self):
        self.discover.return_value={'BB':(device('BB'),advert())}
        with self.assertRaises(RuntimeError):await c.connect_watch(self.app)
        self.assertEqual(self.clients,[])

    async def test_nonconnectable_advertisement_does_not_open_client(self):
        self.discover.return_value={'AA':(device(connectable=False),advert())}
        with self.assertRaises(RuntimeError):await c.connect_watch(self.app)
        self.assertEqual(self.clients,[])

    async def test_ambiguous_discovery_stops(self):
        self.app.selected=None
        self.discover.return_value={a:(device(a),advert()) for a in ['AA','BB']}
        with self.assertRaisesRegex(RuntimeError,'varios relojes'):await c.connect_watch(self.app)
        self.assertEqual(self.discover.await_count,1)
        self.assertEqual(self.clients,[])

    async def test_cancelled_connection_is_disposed(self):
        self.failures=[asyncio.CancelledError()]
        with self.assertRaises(asyncio.CancelledError):await c.connect_watch(self.app)
        self.assertTrue(self.clients[0].closed)
        self.assertEqual(self.app.connection_state['phase'],'cancelled')

    async def test_unselected_unique_watch_pinned_across_attempts(self):
        self.app.selected=None
        self.failures=[TimeoutError()]
        self.discover.side_effect=[{'AA':(device(),advert())},{'BB':(device('BB'),advert())}]
        with self.assertRaises(RuntimeError):await c.connect_watch(self.app)
        self.assertEqual(len(self.clients),1)

    def test_missing_native_metadata_does_not_invent_address_type(self):
        self.assertEqual(c.advertisement_metadata(NS()),(None,None))
        self.assertEqual(c.advertisement_metadata(device(kind=0)),('public',True))

if __name__=='__main__':unittest.main()
