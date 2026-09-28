"""Bounded connections to one watch; no radio resets or OEM writes."""
import asyncio
import logging
import sys
import time
from bleak import BleakClient, BleakScanner

B1 = '0000b001-0000-1000-8000-00805f9b34fb'
B2 = '0000b002-0000-1000-8000-00805f9b34fb'
CCCD = '00002902-0000-1000-8000-00805f9b34fb'
E91A = '0000e91a-0000-1000-8000-00805f9b34fb'
S3802 = '00003802-0000-1000-8000-00805f9b34fb'


def signature(adv):
    services = {str(v).lower() for v in adv.service_uuids or []}
    return E91A in services or S3802 in services


def advertisement_metadata(device):
    # Read the advertisement, not SCAN_RESPONSE (which is not connectable).
    event = getattr(getattr(device, 'details', None), 'adv', None)
    if event is None:
        return None, None
    kind = getattr(event, 'bluetooth_address_type', None)
    try:
        address_type = {0: 'public', 1: 'random'}.get(int(kind))
    except (TypeError, ValueError):
        address_type = None
    return address_type, getattr(event, 'is_connectable', None)


async def connect_watch(app, attempts=2, progress=None, *, services=None):
    progress = progress or (lambda message: None)
    limit = min(2, max(1, attempts))
    selected = app.selected or {}
    address = selected.get('address') or getattr(selected.get('device'), 'address', None)
    state = app.connection_state = dict(connected=False, attempts=0, phase='scan', history=[], native=[])
    requested = list(services) if services else None
    state['requested_services'] = requested
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
            row = dict(attempt=index + 1, phase='scan', native=[])
            active_row = row
            state['history'].append(row)
            state.update(attempts=index + 1, phase='scan')
            try:
                progress(f'CONEXIÓN {index + 1}/{limit} · buscando el mismo reloj…')
                found = await asyncio.wait_for(BleakScanner.discover(timeout=6, return_adv=True), timeout=10)
                if address:
                    candidates = [(d, a) for d, a in found.values() if d.address.lower() == address.lower()]
                else:
                    candidates = [(d, a) for d, a in found.values() if signature(a)]
                    if len(candidates) > 1:
                        raise ValueError('Hay varios relojes compatibles. Seleccioná el tuyo en Buscar relojes.')
                if not candidates:
                    raise RuntimeError('El reloj seleccionado no anunció en esta ronda. No se conectará a otro dispositivo.')
                target, adv = candidates[0]
                address = target.address  # Pin subsequent attempts even if the first connect fails.
                kind, connectable = advertisement_metadata(target)
                row.update(address=address, address_type=kind, connectable=connectable, rssi=adv.rssi)
                progress(f'ANUNCIO · RSSI={adv.rssi} · dirección={kind or "automática"} · conectable={connectable}')
                if connectable is False:
                    raise RuntimeError('El reloj anuncia que no acepta conexiones BLE en este momento.')
                cache = index == 1
                kwargs = {'timeout': 30}
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
                progress('ABRIENDO GATT · ' + ('catálogo en caché; se validará con lectura real' if cache else 'servicios leídos del reloj'))
                client = BleakClient(target, **kwargs)
                await asyncio.wait_for(client.connect(), timeout=35)
                if not client.is_connected:
                    raise RuntimeError('Windows no confirmó la conexión')
                b1 = client.services.get_characteristic(B1)
                b2 = client.services.get_characteristic(B2)
                if b1 is None or b2 is None:
                    raise RuntimeError('El servicio solicitado no contiene B001/B002' if requested else 'El catálogo GATT no contiene B001/B002')
                cccd = next((d for d in b1.descriptors if str(d.uuid).lower() == CCCD), None)
                if cccd is None:
                    raise RuntimeError('B001 no contiene CCCD')
                row['phase'] = state['phase'] = 'att_read'
                # Require actual ATT regardless of the service-catalog cache policy.
                await asyncio.wait_for(client.read_gatt_descriptor(cccd.handle, use_cached=False), timeout=8)
                if not client.is_connected:
                    raise RuntimeError('Se perdió la conexión durante la lectura ATT')
                keep = True
                app.selected = dict(selected, device=target, address=address, name=adv.local_name or target.name)
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
                    # Also dispose partially opened WinRT sessions with is_connected=False.
                    try:
                        await asyncio.wait_for(client.disconnect(), timeout=5)
                    except Exception as error:
                        row['cleanup_error'] = repr(error)
            if index + 1 < limit:
                await asyncio.sleep(3)
        state['phase'] = 'failed'
        raise RuntimeError('No se pudo abrir una conexión BLE utilizable. La esfera no se transfirió. '
                           'Apagá temporalmente Bluetooth en el teléfono, acercá y reiniciá el reloj; '
                           'después reintentá. Último error: ' + (str(last) or type(last).__name__))
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
