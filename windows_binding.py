"""Best-effort repair of one user-confirmed Windows BLE bond; no firmware commands."""
import asyncio
import sys
from connection import advertisement_metadata


async def remove_bond(address, address_type=None):
    from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothAddressType
    from winrt.windows.devices.enumeration import DeviceInformation, DeviceUnpairingResultStatus
    numeric = int(address.replace(':', '').replace('-', ''), 16)
    if address_type:
        device = await BluetoothLEDevice.from_bluetooth_address_with_bluetooth_address_type_async(
            numeric, BluetoothAddressType.PUBLIC if address_type == 'public' else BluetoothAddressType.RANDOM)
    else:
        device = await BluetoothLEDevice.from_bluetooth_address_async(numeric)
    if device is None:
        raise LookupError('Windows no resolvió el reloj por su dirección exacta.')
    try:
        info = await DeviceInformation.create_from_id_async(device.device_information.id)
        before = bool(info.pairing.is_paired)
        result = {'paired_before': before, 'removed': False, 'device_id': info.id,
                  'address_type': address_type}
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
    selected = app.selected or {}
    if not confirmed_address or selected.get('address') != confirmed_address:
        raise RuntimeError('Cambió el reloj seleccionado. No se modificó ningún vínculo.')
    kind, _ = advertisement_metadata(selected.get('device'))
    kind = kind or selected.get('address_type')
    report = app.binding_repair = {
        'address': confirmed_address, 'address_type': kind, 'phase': 'remove_windows_bond',
        'user_confirmed': True, 'removed': False, 'scan_required': False
    }
    progress('REPARACIÓN · usando la dirección confirmada; no depende de que el reloj vuelva a anunciar.')
    try:
        progress('REPARACIÓN · consultando y quitando sólo su vínculo BLE de Windows, si existe…')
        report.update(await asyncio.wait_for(remove_bond(confirmed_address, kind), timeout=30))
    except asyncio.CancelledError:
        report['phase'] = 'cancelled'
        raise
    except Exception as error:
        report['bond_repair_warning'] = type(error).__name__ + ': ' + str(error)
        report['phase'] = 'awaiting_new_connection'
        progress('REPARACIÓN WINDOWS NO COMPLETADA · se continúa con emparejamiento directo a la dirección exacta.')
        return report
    report['phase'] = 'awaiting_new_connection'
    progress('VÍNCULO ANTERIOR QUITADO · se intentará un nuevo emparejamiento.'
             if report['removed']
             else 'SIN VÍNCULO PREVIO · se intentará emparejar directamente por dirección.')
    await asyncio.sleep(2)
    return report
