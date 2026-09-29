"""Bounded connections to one exact watch; no radio resets or OEM writes."""
import asyncio
import logging
import sys
import time
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

B1 = '0000b001-0000-1000-8000-00805f9b34fb'
B2 = '0000b002-0000-1000-8000-00805f9b34fb'
CCCD = '00002902-0000-1000-8000-00805f9b34fb'
E91A = '0000e91a-0000-1000-8000-00805f9b34fb'
S3802 = '00003802-0000-1000-8000-00805f9b34fb'


def signature(adv):
    services = {str(v).lower() for v in adv.service_uuids or []}
    return E91A in services or S3802 in services


def advertisement_metadata(device):
    event = getattr(getattr(device, 'details', None), 'adv', None)
    if event is None:
        return None, None
    kind = getattr(event, 'bluetooth_address_type', None)
    try:
        address_type = {0: 'public', 1: 'random'}.get(int(kind))
    except (TypeError, ValueError):
        address_type = None
    return address_type, getattr(event, 'is_connectable', None)


def _same_address(device, address):
    return bool(device and getattr(device, 'address', None)
                and device.address.lower() == address.lower())


def pinned_device(selected, address):
    """Return a BLEDevice pinned to the exact selected address without scanning."""
    device = selected.get('device')
    if _same_address(device, address):
        return device, 'selected_ble_device'
    return BLEDevice(address, selected.get('name'), None), 'synthetic_exact_address'


async def connect_watch(app, attempts=2, progress=None, *, services=None, pair=False):
    progress = progress or (lambda message: None)
    limit = min(2, max(1, attempts))
    selected = app.selected or {}
    address = selected.get('address') or getattr(selected.get('device'), 'address', None)
    state = app.connection_state = dict(connected=False, attempts=0, phase='resolve', history=[], native=[])
    requested = list(services) if services else None
    state['requested_services'] = requested
    state['pair_requested'] = pair
    state['exact_address'] = address
    started = time.monotonic()
    active_row = None
    logger = logging.getLogger('bleak.backends.winrt.client')
    old_level = logger.level

    class NativeLog(logging.Handler):
        def emit(self, record):
            message = record.getMessage()
            state['native'].append(message)
            del state['native'][:-80]
            if active_row is not None:
                active_row['native'].append({'elapsed_s': round(time.monotonic()-started, 3), 'message': message})
                del active_row['native'][:-60]

    handler = NativeLog()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    last = None
    try:
        for index in range(limit):
            client = None
            keep = False
            row = dict(attempt=index + 1, phase='resolve', native=[])
            active_row = row
            state['history'].append(row)
            state.update(attempts=index + 1, phase='resolve')
            try:
                adv = None
                if address:
                    target, source = pinned_device(selected, address)
                    kind, connectable = advertisement_metadata(target)
                    kind = kind or selected.get('address_type')
                    if connectable is None:
                        connectable = selected.get('connectable')
                    row.update(address=address, address_type=kind, connectable=connectable,
                               target_source=source, scan_bypassed=True)
                    progress(f'CONEXIÓN {index + 1}/{limit} · identidad fijada {address}; sin exigir un nuevo anuncio.')
                else:
                    progress(f'CONEXIÓN {index + 1}/{limit} · buscando un único reloj compatible…')
                    found = await asyncio.wait_for(BleakScanner.discover(timeout=8, return_adv=True), timeout=12)
                    candidates = [(d, a) for d, a in found.values() if signature(a)]
                    if len(candidates) > 1:
                        raise ValueError('Hay varios relojes compatibles. Seleccioná el tuyo en Buscar relojes.')
                    if not candidates:
                        raise RuntimeError('No apareció ningún reloj compatible en esta ronda.')
                    target, adv = candidates[0]
                    address = target.address
                    state['exact_address'] = address
                    kind, connectable = advertisement_metadata(target)
                    row.update(address=address, address_type=kind, connectable=connectable,
                               rssi=adv.rssi, target_source='fresh_scan', scan_bypassed=False)
                    progress(f'ANUNCIO · RSSI={adv.rssi} · dirección={kind or "automática"} · conectable={connectable}')
                    if connectable is False:
                        raise RuntimeError('El reloj anuncia que no acepta conexiones BLE en este momento.')

                cache = index == 1
                kwargs = {'timeout': 60 if pair else 30}
                if pair:
                    kwargs['pair'] = True
                    progress('EMPAREJAMIENTO WINDOWS · solicitando vínculo sobre la dirección exacta antes de GATT…')
                if requested is not None:
                    kwargs['services'] = requested
                if sys.platform == 'win32':
                    kwargs['winrt'] = {'use_cached_services': cache}
                    if kind:
                        kwargs['winrt']['address_type'] = kind
                row.update(phase='connect_and_services', cached_services=cache, requested_services=requested)
                state['phase'] = row['phase']
                if requested:
                    progress('GATT DIRECTO · consultando sólo ' + ', '.join(requested))
                progress('ABRIENDO GATT · ' + ('catálogo en caché; se validará con lectura real'
                                               if cache else 'servicios leídos del reloj'))
                client = BleakClient(target, **kwargs)
                await asyncio.wait_for(client.connect(), timeout=65 if pair else 35)
                if not client.is_connected:
                    raise RuntimeError('Windows no confirmó la conexión')
                b1 = client.services.get_characteristic(B1)
                b2 = client.services.get_characteristic(B2)
                if b1 is None or b2 is None:
                    raise RuntimeError('El servicio solicitado no contiene B001/B002'
                                       if requested else 'El catálogo GATT no contiene B001/B002')
                cccd = next((d for d in b1.descriptors if str(d.uuid).lower() == CCCD), None)
                if cccd is None:
                    raise RuntimeError('B001 no contiene CCCD')
                row['phase'] = state['phase'] = 'att_read'
                await asyncio.wait_for(client.read_gatt_descriptor(cccd.handle, use_cached=False), timeout=8)
                if not client.is_connected:
                    raise RuntimeError('Se perdió la conexión durante la lectura ATT')
                keep = True
                name = ((adv.local_name if adv is not None else None)
                        or getattr(target, 'name', None) or selected.get('name'))
                app.selected = dict(selected, device=target, address=address, name=name,
                                    address_type=kind, connectable=connectable)
                row['phase'] = 'ready'
                state.update(connected=True, phase='ready')
                progress('GATT Y LECTURA ATT OK · continúa la instalación de la esfera')
                return client, index + 1
            except asyncio.CancelledError:
                state['phase'] = 'cancelled'
                raise
            except Exception as error:
                last = error
                row['error'] = type(error).__name__ + ': ' + (str(error) or 'tiempo agotado en ' + row['phase'])
                progress('CONEXIÓN FALLÓ · ' + row['error'])
                if isinstance(error, ValueError):
                    break
            finally:
                if client is not None and not keep:
                    try:
                        await asyncio.wait_for(client.disconnect(), timeout=5)
                    except Exception as error:
                        row['cleanup_error'] = repr(error)
            if index + 1 < limit:
                progress('RECUPERACIÓN · segundo intento sobre la misma dirección exacta; no se buscará otro reloj.')
                await asyncio.sleep(3)
        state['phase'] = 'failed'
        raise RuntimeError('No se pudo abrir una conexión BLE utilizable. La esfera no se transfirió. '
                           'El diagnóstico conserva los errores de cada intento. Último error: '
                           + (str(last) or type(last).__name__))
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
