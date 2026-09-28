from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
if 'APP_VERSION="1.02.0"' not in s: raise SystemExit('V1.03 requiere V1.02')
s=s.replace('APP_VERSION="1.02.0"','APP_VERSION="1.03.0"',1).replace('V1.02','V1.03')
start=s.index('    async def connect_retry(')
end=s.index('\n    def diagnose(',start)
conn='''    async def connect_retry(self,attempts=5,progress=None):
        progress=progress or (lambda message:None)
        last=None
        self.connection_state={"connected":False,"attempts":0,"phase":"signature_scan","strategies":[]}

        def score(d,a):
            uu={str(x).lower() for x in (a.service_uuids or [])}
            sd={str(k).lower():v for k,v in (a.service_data or {}).items()}
            md=a.manufacturer_data or {}
            n=(a.local_name or d.name or '').strip().lower()
            v=0
            if '0000e91a-0000-1000-8000-00805f9b34fb' in uu:v+=120
            if '00003802-0000-1000-8000-00805f9b34fb' in uu:v+=110
            if any('3802' in k for k in sd):v+=110
            if n=='apple watch ultra':v+=60
            if md.get(255)==bytes.fromhex('00a6'):v+=40
            return v

        async def fresh_by_signature(timeout=12):
            found=await BleakScanner.discover(timeout=timeout,return_adv=True)
            candidates=[]
            for _,(d,a) in found.items():
                sc=score(d,a)
                if sc>=230:candidates.append((sc,a.rssi if a.rssi is not None else -999,d,a))
            candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
            return candidates[0] if candidates else None

        for i in range(max(1,attempts)):
            client=None;ok=False
            try:
                self.connection_state['attempts']=i+1
                progress(f"CONEXIÓN {i+1}/{attempts} · escaneo por firma UtraWatch E91A/3802...")
                hit=await fresh_by_signature(12)
                if hit is None: raise RuntimeError('sin anuncio UtraWatch por firma en esta ronda')
                sc,rssi,target,adv=hit
                progress(f"UTRAWATCH FRESCO · {adv.local_name or target.name or '(sin nombre)'} · {target.address} · RSSI={rssi} · score={sc}")
                # Do not reuse the address/device stored by a previous scan. The object
                # returned by this exact discovery round is the connection target.
                client=BleakClient(target,timeout=25)
                await asyncio.wait_for(client.connect(),timeout=30)
                if not client.is_connected: raise RuntimeError('Windows no confirmó is_connected')
                _=client.services
                b1=client.services.get_characteristic('0000b001-0000-1000-8000-00805f9b34fb')
                b2=client.services.get_characteristic('0000b002-0000-1000-8000-00805f9b34fb')
                if b1 is None or b2 is None: raise RuntimeError('sesión GATT sin B001/B002')
                ok=True
                if self.selected is None:self.selected={}
                self.selected['device']=target;self.selected['address']=target.address
                self.selected['name']=adv.local_name or target.name or 'Apple Watch Ultra'
                self.connection_state.update({'connected':True,'phase':'gatt_open','strategy':'fresh signature object','attempts':i+1,'score':sc,'rssi':rssi})
                progress(f"GATT UTRAWATCH OK · B001={getattr(b1,'handle',None)} · B002={getattr(b2,'handle',None)} · MTU={getattr(client,'mtu_size',None)}")
                return client,i+1
            except asyncio.CancelledError:raise
            except Exception as ex:
                last=ex;progress(f"INTENTO {i+1} FALLÓ · {type(ex).__name__}: {ex}")
            finally:
                if client is not None and not ok:
                    try:
                        if client.is_connected:await asyncio.wait_for(client.disconnect(),timeout=4)
                    except Exception:pass
            if i+1<attempts:
                wait=4+2*i
                progress(f"RECUPERACIÓN BLE · liberando sesión Windows {wait}s...")
                await asyncio.sleep(wait)
        self.connection_state.update({'connected':False,'phase':'failed'})
        raise RuntimeError('GATT UTRAWATCH NO DISPONIBLE por firma: '+str(last))
'''
s=s[:start]+conn+s[end:]
s=s.replace('V1.03 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.03; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Conexión original V0.83: anuncio fresco → sesión GATT limpia.','V1.03 LISTA · 1º INSTALAR ESFERA SINCRONIZADA V1.03; 2º REVISAR HORA/PASOS/PULSO; 3º COPIAR DIAGNÓSTICO. Busca cada intento por firma E91A/3802 y conecta al objeto BLE recién descubierto.')
s=s.replace('V1.03 · CONEXIÓN ORIGINAL V0.83 · elimina también el auto-ID V0.87 que V1.01 demostró problemático; conserva esfera aprobada V0.86 y bindings vivos V0.88.','V1.03 · RECUPERACIÓN BLE POR FIRMA · V1.02 falló porque find_device_by_address dejó de ver la dirección aunque el diagnóstico sí veía anuncios. Cada intento hace discovery completo, identifica E91A/3802 y conecta al objeto fresco; conserva transferencia y esfera aprobadas.')
p.write_text(s,encoding='utf-8')
print('overlay V1.03 aplicado')
