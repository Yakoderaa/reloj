import importlib.util
import sys
import unittest
from types import SimpleNamespace as NS, ModuleType
from unittest.mock import AsyncMock, patch

if 'bleak' not in sys.modules and importlib.util.find_spec('bleak') is None:
    stub=ModuleType('bleak');stub.BleakClient=stub.BleakScanner=None;sys.modules['bleak']=stub
    backends=ModuleType('bleak.backends');device_mod=ModuleType('bleak.backends.device')
    class BLEDevice:
        def __init__(self,address,name=None,details=None):
            self.address=address;self.name=name;self.details=details
    device_mod.BLEDevice=BLEDevice
    sys.modules['bleak.backends']=backends;sys.modules['bleak.backends.device']=device_mod

import windows_binding as w


def device(address='AA',kind=1):
    return NS(address=address,details=NS(adv=NS(bluetooth_address_type=kind,is_connectable=True)))


class RepairTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app=NS(selected={'address':'AA','device':device()})
        self.remove=AsyncMock(return_value={'paired_before':True,'removed':True})
        self.patches=[patch.object(w.sys,'platform','win32'),
                      patch.object(w,'remove_bond',self.remove),
                      patch.object(w.asyncio,'sleep',AsyncMock())]
        for p in self.patches:p.start()
        self.addCleanup(lambda:[p.stop() for p in reversed(self.patches)])

    async def test_repair_uses_confirmed_address_without_fresh_scan(self):
        report=await w.repair_selected(self.app,'AA',lambda x:None)
        self.remove.assert_awaited_once_with('AA','random')
        self.assertTrue(report['removed'])
        self.assertFalse(report['scan_required'])
        self.assertEqual(report['phase'],'awaiting_new_connection')

    async def test_changed_selection_cannot_remove_bond(self):
        with self.assertRaises(RuntimeError):await w.repair_selected(self.app,'BB',lambda x:None)
        self.remove.assert_not_awaited()

    async def test_failed_windows_repair_no_longer_blocks_install_path(self):
        self.remove.side_effect=RuntimeError('access denied')
        report=await w.repair_selected(self.app,'AA',lambda x:None)
        self.assertEqual(report['phase'],'awaiting_new_connection')
        self.assertFalse(report['removed'])
        self.assertIn('access denied',report['bond_repair_warning'])

    async def test_no_previous_bond_does_not_claim_removal(self):
        self.remove.return_value={'paired_before':False,'removed':False}
        report=await w.repair_selected(self.app,'AA',lambda x:None)
        self.assertFalse(report['removed'])

    async def test_native_device_closed_on_unpair_rejection(self):
        native=NS(device_information=NS(id='id'),close=unittest.mock.Mock())
        info=NS(id='id',pairing=NS(is_paired=True,unpair_async=AsyncMock(return_value=NS(status=9))))
        bluetooth=ModuleType('winrt.windows.devices.bluetooth')
        bluetooth.BluetoothLEDevice=NS(
            from_bluetooth_address_async=AsyncMock(return_value=native),
            from_bluetooth_address_with_bluetooth_address_type_async=AsyncMock(return_value=native))
        bluetooth.BluetoothAddressType=NS(PUBLIC=0,RANDOM=1)
        enum=ModuleType('winrt.windows.devices.enumeration')
        enum.DeviceInformation=NS(create_from_id_async=AsyncMock(return_value=info))
        enum.DeviceUnpairingResultStatus=NS(UNPAIRED=0,ALREADY_UNPAIRED=1)
        self.patches[1].stop()
        with patch.dict(sys.modules,{'winrt.windows.devices.bluetooth':bluetooth,
                                     'winrt.windows.devices.enumeration':enum}):
            with self.assertRaisesRegex(RuntimeError,'quitar el vínculo'):
                await w.remove_bond('AA:BB:CC:DD:EE:FF','public')
        native.close.assert_called_once()
        self.patches[1].start()


class ConfirmationTests(unittest.TestCase):
    def test_declining_confirmation_never_schedules_repair(self):
        import ast
        from pathlib import Path
        from unittest.mock import Mock
        tree=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8'))
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='repair_binding')
        app=NS(ble_busy=False,selected={'address':'AA','name':'Watch'},run_async=Mock())
        dialogs=NS(askyesno=Mock(return_value=False))
        namespace={'self':app,'messagebox':dialogs,'w':None,'append':Mock()}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'repair-ui','exec'),namespace)
        namespace['repair_binding']()
        dialogs.askyesno.assert_called_once()
        app.run_async.assert_not_called()


if __name__=='__main__':unittest.main()
