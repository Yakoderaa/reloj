from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

if 'APP_VERSION="0.82.0"' not in s:
    raise SystemExit("V0.83 requiere la base V0.82 aplicada")
s=s.replace('APP_VERSION="0.82.0"','APP_VERSION="0.83.0"',1)
s=s.replace('V0.82','V0.83')

old_compress='''            def oem_dial_compress(raw):
                import zlib
                co=zlib.compressobj(level=6,method=zlib.DEFLATED,wbits=9)
                comp=co.compress(raw)+co.flush()
                hdr=bytearray(20)
                total=len(comp)+20
                hdr[0:4]=total.to_bytes(4,"little")
                hdr[4:6]=crc16_8005(comp).to_bytes(2,"little")
                hdr[6:8]=bytes([0xFE,0xFE])
                hdr[8]=1
                if len(raw)>26 and raw[9]==255:
                    hdr[9]=raw[25]
                    hdr[10]=raw[26]
                elif len(raw)>9:
                    hdr[9]=raw[9]
                    hdr[10]=0
                hdr[11]=0
                return bytes(hdr)+comp,comp

            def read_candidate():
                path=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v062","single-face-proof-v062.bin")
                if not os.path.exists(path):raise RuntimeError("Falta single-face-proof-v062.bin")
                with open(path,"rb") as fh:raw=fh.read()
                if len(raw)<54 or raw[:2]!=b"WF":raise RuntimeError("WF inválido")
                expected="2d055de32cdf31712bffac39a8147f0af30848ffb3e51fece2e6085462551276"
                got=hashlib.sha256(raw).hexdigest()
                if got!=expected:raise RuntimeError("El WF candidato cambió: "+got)
                return path,raw
'''
new_compress='''            def oem_dial_compress(raw):
                # Exact GZipUtils.zlib(..., false) parameters from the UtraWatch SDK:
                # deflater.init(level=6, windowBits=9, memLevel=3, W_ZLIB).
                import zlib
                co=zlib.compressobj(level=6,method=zlib.DEFLATED,wbits=9,memLevel=3,zdict=None)
                comp=co.compress(raw)+co.flush()
                hdr=bytearray(20)
                total=len(comp)+20
                hdr[0:4]=total.to_bytes(4,"little")
                hdr[4:6]=crc16_8005(comp).to_bytes(2,"little")
                hdr[6:8]=bytes([0xFE,0xFE])
                hdr[8]=1
                if len(raw)>26 and raw[9]==255:
                    hdr[9]=raw[25]
                    hdr[10]=raw[26]
                elif len(raw)>9:
                    hdr[9]=raw[9]
                    hdr[10]=0
                hdr[11]=0
                return bytes(hdr)+comp,comp

            def build_customize_candidate():
                # UtraWatch CUSTOMIZE/cmd=2 does NOT send a WF package.
                # V2ModifyClockdialVM.cBinFile(width,height) emits:
                # [time_pos,time_up,time_down,color_le16,picture=2,width_le16,height_le16]
                # followed by width*height pixels in BGR565, big-endian per pixel.
                w=h=240
                header=bytearray(10)
                header[0]=0       # time position
                header[1]=0       # no upper complication
                header[2]=0       # no lower complication
                header[3:5]=(0xFFFF).to_bytes(2,"little")  # white clock text
                header[5]=2       # custom picture
                header[6:8]=w.to_bytes(2,"little")
                header[8:10]=h.to_bytes(2,"little")

                pixels=bytearray(w*h*2)

                # Tiny 5x7 font for a visible proof face. The watch itself renders the time.
                font={
                    "0":["01110","10001","10011","10101","11001","10001","01110"],
                    "1":["00100","01100","00100","00100","00100","00100","01110"],
                    "2":["01110","10001","00001","00010","00100","01000","11111"],
                    "3":["11110","00001","00001","01110","00001","00001","11110"],
                    "4":["00010","00110","01010","10010","11111","00010","00010"],
                    "5":["11111","10000","10000","11110","00001","00001","11110"],
                    "6":["01110","10000","10000","11110","10001","10001","01110"],
                    "7":["11111","00001","00010","00100","01000","01000","01000"],
                    "8":["01110","10001","10001","01110","10001","10001","01110"],
                    "9":["01110","10001","10001","01111","00001","00001","01110"],
                    "A":["01110","10001","10001","11111","10001","10001","10001"],
                    "B":["11110","10001","10001","11110","10001","10001","11110"],
                    "E":["11111","10000","10000","11110","10000","10000","11111"],
                    "J":["00111","00010","00010","00010","10010","10010","01100"],
                    "L":["10000","10000","10000","10000","10000","10000","11111"],
                    "O":["01110","10001","10001","10001","10001","10001","01110"],
                    "R":["11110","10001","10001","11110","10100","10010","10001"],
                    "V":["10001","10001","10001","10001","10001","01010","00100"],
                    " ":["00000"]*7,
                }

                def bgr565(r,g,b):
                    return ((b>>3)<<11)|((g>>2)<<5)|(r>>3)

                def put(x,y,r,g,b):
                    if x<0 or y<0 or x>=w or y>=h:return
                    v=bgr565(r,g,b)
                    off=(y*w+x)*2
                    pixels[off]=(v>>8)&255
                    pixels[off+1]=v&255

                # Dark background with a high-contrast cyan/red ring.
                cx=cy=120
                for y in range(h):
                    for x in range(w):
                        dx=x-cx;dy=y-cy;d2=dx*dx+dy*dy
                        if d2>111*111:
                            col=(3,5,9)
                        elif 100*100<=d2<=108*108:
                            col=(0,220,255) if ((x+y)//12)%2==0 else (255,42,80)
                        elif d2<42*42:
                            col=(7,10,17)
                        else:
                            # Subtle radial/grid texture that compresses well but is visibly custom.
                            v=10+((x//24+y//24)&1)*5
                            col=(v,v+2,v+6)
                        put(x,y,*col)

                # Four strong markers.
                for yy in range(20,40):
                    for xx in range(112,128): put(xx,yy,255,42,80)
                for yy in range(200,220):
                    for xx in range(112,128): put(xx,yy,0,220,255)
                for yy in range(112,128):
                    for xx in range(20,40): put(xx,yy,0,220,255)
                for yy in range(112,128):
                    for xx in range(200,220): put(xx,yy,255,42,80)

                def text5(s,x,y,scale,color):
                    ox=x
                    for ch in s:
                        pat=font.get(ch,font[" "])
                        for ry,row in enumerate(pat):
                            for rx,on in enumerate(row):
                                if on=="1":
                                    for sy in range(scale):
                                        for sx in range(scale):
                                            put(x+rx*scale+sx,y+ry*scale+sy,*color)
                        x += 6*scale
                    return x-ox

                # Top/bottom labels stay away from the firmware-rendered central clock.
                text5("RELOJ LAB",36,49,2,(245,245,245))
                text5("V83",87,177,3,(255,42,80))

                raw=bytes(header)+bytes(pixels)
                base=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v083")
                os.makedirs(base,exist_ok=True)
                path=os.path.join(base,"customize-face-v083.bin")
                with open(path,"wb") as fh:fh.write(raw)
                return path,raw,w,h
'''
if old_compress not in s:
    raise SystemExit("V0.83: generador/compresor V0.82 no encontrado")
s=s.replace(old_compress,new_compress,1)

old_prepare='''                emit("1/9 · Validando WF y construyendo paquete OEM…")
                path,raw=await asyncio.to_thread(read_candidate)
                oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                rep["single_face_install"]["candidate"]={
                    "path":path,"raw_size":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "oem_stream_size":len(oem_stream),"deflate_size":len(deflated),
                    "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                    "oem_crc16":f"0x{crc16_8005(deflated):04X}",
                    "oem_header_hex":oem_stream[:20].hex()
                }

                c=None;events=[];messages=[];pid=0
'''
new_prepare='''                emit("1/9 · Generando CUSTOMIZE real 240×240 + paquete OEM…")
                path,raw,custom_w,custom_h=await asyncio.to_thread(build_customize_candidate)
                oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                rep["single_face_install"]["candidate"]={
                    "path":path,"format":"UtraWatch CUSTOMIZE cBinFile","width":custom_w,"height":custom_h,
                    "picture_mode":2,"raw_size":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "raw_header_hex":raw[:10].hex(),
                    "oem_stream_size":len(oem_stream),"deflate_size":len(deflated),
                    "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                    "oem_crc16":f"0x{crc16_8005(deflated):04X}",
                    "oem_header_hex":oem_stream[:20].hex()
                }

                c=None;events=[];messages=[];tx_n=1;wire_dev_type=1
'''
if old_prepare not in s:
    raise SystemExit("V0.83: preparación V0.82 no encontrada")
s=s.replace(old_prepare,new_prepare,1)

old_build='''            def build(pid,op,payload=b"",send_type=1):
                payload=bytes(payload);n=len(payload)
                if n>4855:raise RuntimeError("payload WTWD demasiado grande")
                h=bytearray(20)
                if n<=10:
                    h[1]=pid&255;h[4]=send_type;h[5]=op;h[8]=n&255;h[9]=(n>>8)&255;h[10:10+n]=payload
                    return [bytes(h)]
                frags=((n-10)+18)//19
                h[1]=pid&255;h[2]=frags;h[4]=send_type;h[5]=op;h[8]=n&255;h[9]=(n>>8)&255;h[10:20]=payload[:10]
                out=[bytes(h)];pos=10
'''
new_build='''            def build(dev_type,n_seq,op,payload=b"",send_type=1):
                # CEProtocolB wire header: byte1=device type, byte3=N sequence.
                # V0.82 incorrectly incremented byte1 and left byte3 at zero.
                payload=bytes(payload);n=len(payload)
                if n>4855:raise RuntimeError("payload WTWD demasiado grande")
                h=bytearray(20)
                if n<=10:
                    h[1]=dev_type&255;h[3]=n_seq&255;h[4]=send_type;h[5]=op
                    h[8]=n&255;h[9]=(n>>8)&255;h[10:10+n]=payload
                    return [bytes(h)]
                frags=((n-10)+18)//19
                h[1]=dev_type&255;h[2]=frags;h[3]=n_seq&255;h[4]=send_type;h[5]=op
                h[8]=n&255;h[9]=(n>>8)&255;h[10:20]=payload[:10]
                out=[bytes(h)];pos=10
'''
if old_build not in s:
    raise SystemExit("V0.83: build CEProtocolB V0.82 no encontrado")
s=s.replace(old_build,new_build,1)

old_rx_head='''                    def rx(sender,data):
                        nonlocal current
                        b=bytes(data);events.append(b)
                        if len(b)<1:return
                        if b[0]==0:
                            if len(b)<10:return
                            plen=b[8]|(b[9]<<8)
'''
new_rx_head='''                    def rx(sender,data):
                        nonlocal current,wire_dev_type
                        b=bytes(data);events.append(b)
                        if len(b)<1:return
                        if b[0]==0:
                            if len(b)<10:return
                            # CEProtocolB learns the real device type from device traffic.
                            # This watch reports 0xFF; all following app packets must use it.
                            wire_dev_type=b[1]&255
                            plen=b[8]|(b[9]<<8)
'''
if old_rx_head not in s:
    raise SystemExit("V0.83: rx head V0.82 no encontrado")
s=s.replace(old_rx_head,new_rx_head,1)

old_tx='''                    async def tx(op,payload=b"",send_type=1,wait=.5):
                        nonlocal pid
                        start=len(messages);frames=build(pid,op,payload,send_type)
                        this_pid=pid
                        for fr in frames:
                            await asyncio.wait_for(c.write_gatt_char(b002,fr,response=False),timeout=5)
                            await asyncio.sleep(.045)
                        pid=(pid+1)&255
                        if wait:await asyncio.sleep(wait)
                        return this_pid,messages[start:],frames
'''
new_tx='''                    async def tx(op,payload=b"",send_type=1,wait=.5):
                        nonlocal tx_n,wire_dev_type
                        start=len(messages)
                        this_n=tx_n&255
                        this_dev_type=wire_dev_type&255
                        frames=build(this_dev_type,this_n,op,payload,send_type)
                        for fr in frames:
                            await asyncio.wait_for(c.write_gatt_char(b002,fr,response=False),timeout=5)
                            await asyncio.sleep(.045)
                        tx_n=(tx_n+1)&255
                        if wait:await asyncio.sleep(wait)
                        return {"n":this_n,"dev_type":this_dev_type},messages[start:],frames
'''
if old_tx not in s:
    raise SystemExit("V0.83: tx V0.82 no encontrado")
s=s.replace(old_tx,new_tx,1)

old_tx83='''                    async def tx83_wait(payload,timeout=4.0):
                        before=len(ack83_statuses);ack83_event.clear()
                        this_pid,_,frames=await tx(0x83,payload,1,0)
                        if len(ack83_statuses)==before:
                            try:await asyncio.wait_for(ack83_event.wait(),timeout=timeout)
                            except asyncio.TimeoutError:pass
                        status=ack83_statuses[-1] if len(ack83_statuses)>before else None
                        return this_pid,status,frames
'''
new_tx83='''                    async def tx83_wait(payload,timeout=4.0):
                        before=len(ack83_statuses);ack83_event.clear()
                        wire,_,frames=await tx(0x83,payload,1,0)
                        if len(ack83_statuses)==before:
                            try:await asyncio.wait_for(ack83_event.wait(),timeout=timeout)
                            except asyncio.TimeoutError:pass
                        status=ack83_statuses[-1] if len(ack83_statuses)>before else None
                        return wire,status,frames
'''
if old_tx83 not in s:
    raise SystemExit("V0.83: tx83_wait V0.82 no encontrado")
s=s.replace(old_tx83,new_tx83,1)

old_block='''                            this_pid,status,frames=await tx83_wait(app_payload)
                            connected=bool(getattr(c,"is_connected",False))
                            rep["single_face_install"]["blocks"].append({
                                "slot_cmd":command,"slot":label,"index":idx,"pid":this_pid,"offset":offset,
                                "data_length":len(chunk),"wtwd_payload_length":len(app_payload),
                                "frame_count":len(frames),"status":status,"connected":connected
                            })
'''
new_block='''                            wire,status,frames=await tx83_wait(app_payload)
                            connected=bool(getattr(c,"is_connected",False))
                            rep["single_face_install"]["blocks"].append({
                                "slot_cmd":command,"slot":label,"index":idx,
                                "wire_dev_type":wire.get("dev_type"),"wire_n":wire.get("n"),"offset":offset,
                                "data_length":len(chunk),"wtwd_payload_length":len(app_payload),
                                "frame_count":len(frames),"status":status,"connected":connected
                            })
'''
if old_block not in s:
    raise SystemExit("V0.83: block diagnostics V0.82 no encontrado")
s=s.replace(old_block,new_block,1)

# tx83_wait callers outside transfer_slot ignore the first return value, so dict metadata is compatible.
# Record wire state in the final diagnostic.
old_protocol='''                    rep["single_face_install"]["protocol_acks_sent"]=protocol_acks_sent
                    rep["single_face_install"]["classification"]=(
'''
new_protocol='''                    rep["single_face_install"]["protocol_acks_sent"]=protocol_acks_sent
                    rep["single_face_install"]["wire_protocol"]={
                        "final_dev_type":wire_dev_type,"next_n":tx_n,
                        "note":"CEProtocolB byte1=device_type; byte3=N"
                    }
                    rep["single_face_install"]["classification"]=(
'''
if old_protocol not in s:
    raise SystemExit("V0.83: final protocol diagnostics no encontrado")
s=s.replace(old_protocol,new_protocol,1)

s=s.replace(
    'V0.83 LISTA · 1º INSTALAR ESFERA REAL V0.83; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Replica el estado de transferencia OEM y no envía el archivo hasta recibir WATCH_FACE_INFO.',
    'V0.83 LISTA · 1º INSTALAR ESFERA RELOJ LAB V0.83; 2º MIRAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Genera el CUSTOMIZE real 240×240 y usa la cabecera CEProtocolB exacta.'
)
s=s.replace('INSTALAR ESFERA REAL V0.83','INSTALAR ESFERA RELOJ LAB V0.83')
s=s.replace(
    'V0.83 · APLICAR ESFERA ÚNICA · resuelve el slot editable real de UtraWatch, instala la esfera CUSTOMIZE y la selecciona con showOrder-1.',
    'V0.83 · CUSTOMIZE REAL · genera el mismo formato cBinFile de UtraWatch, corrige device_type/N en CEProtocolB y selecciona el slot editable.'
)

p.write_text(s,encoding="utf-8")
print("overlay V0.83 aplicado")
