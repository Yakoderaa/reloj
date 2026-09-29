"""User-confirmed removal of one Windows BLE bond; no firmware commands."""
import asyncio
import sys
from bleak import BleakScanner
from connection import advertisement_metadata, signature


async def remove_bond(target):
    from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothAddressType
    from winrt.windows.devices.enumeration import DeviceInformation, DeviceUnpairingResultStatus
    kind, _ = advertisement_metadata(target)
    address = int(target.address.replace(':', '').replace('-', ''), 16)
    if kind:
        device = await BluetoothLEDevice.from_bluetooth_address_with_bluetooth_address_type_async(
            address, BluetoothAddressType.PUBLIC if kind == 'public' else BluetoothAddressType.RANDOM)
    else:
        device = await BluetoothLEDevice.from_bluetooth_address_async(address)
    if device is None:
        raise RuntimeError('Windows no resolvió el reloj seleccionado; no se modificó ningún vínculo.')
    try:
        info = await DeviceInformation.create_from_id_async(device.device_information.id)
        before = bool(info.pairing.is_paired)
        result = {'paired_before': before, 'removed': False, 'device_id': info.id}
        if before:
            outcome = await info.pairing.unpair_async()
            result['unpair_status'] = str(outcome.status)
            if outcome.status not in (DeviceUnpairingResultStatus.UNPAIRED,
                                      DeviceUnpairingResultStatus.ALREADY_UNPAIRED):
                raise RuntimeError('Windows no pudo quitar el vínculo: ' + str(outcome.status))
            result['removed'] = True
        return result
    finally:
        device.close()


async def repair_selected(app, confirmed_address, progress):
    if sys.platform != 'win32':
        raise RuntimeError('Esta reparación requiere Windows.')
    if not confirmed_address or (app.selected or {}).get('address') != confirmed_address:
        raise RuntimeError('Cambió el reloj seleccionado. No se modificó ningún vínculo.')
    report = app.binding_repair = {'address': confirmed_address, 'phase': 'scan',
                                  'user_confirmed': True, 'removed': False}
    try:
        progress('REPARACIÓN · verificando el reloj que confirmaste…')
        found = await asyncio.wait_for(BleakScanner.discover(timeout=8, return_adv=True), timeout=12)
        hits = [(d, a) for d, a in found.values()
                if d.address.lower() == confirmed_address.lower() and signature(a)]
        if len(hits) != 1:
            raise RuntimeError('No se verificó el anuncio del reloj confirmado; no se quitó ningún vínculo.')
        target, _ = hits[0]
        report['phase'] = 'remove_windows_bond'
        progress('REPARACIÓN · consultando y quitando sólo su vínculo BLE de Windows…')
        report.update(await asyncio.wait_for(remove_bond(target), timeout=30))
        report['phase'] = 'awaiting_new_connection'
        progress('VÍNCULO ANTERIOR QUITADO · se intentará un nuevo emparejamiento.' if report['removed']
                 else 'SIN VÍNCULO PREVIO · se intentará emparejar antes de consultar E91A.')
        await asyncio.sleep(3)
        return report
    except BaseException as error:
        report.update(phase='failed', error=type(error).__name__ + ': ' + str(error))
        raise
