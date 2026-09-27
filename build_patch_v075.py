from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

s = s.replace('APP_VERSION="0.74.0"', 'APP_VERSION="0.75.0"', 1)
s = s.replace('root.title("Reloj Lab V0.74")', 'root.title("Reloj Lab V0.75")', 1)
s = s.replace('V0.74 · modo esfera única · protocolo ApWatch/WTWD', 'V0.75 · análisis de transferencia', 1)
s = s.replace('PROBAR 20 BLOQUES 300B V0.74', 'ANALIZAR TRANSFERENCIA V0.75', 1)

start = s.index("        def ota_lab():")
end = s.index("        # Bind the already-visible first button now that ota_lab exists.", start)

new_block = '''        def ota_lab():
            append("V0.75 · ANÁLISIS OFFLINE · calcula segmentación completa y verificaciones del archivo. No usa Bluetooth.")
            rep=self.base_report()
            rep["offline_transfer_plan"]={"phase":"build","device_writes":0}
            t0=time.monotonic()

            def emit(msg):
                line=f"+{time.monotonic()-t0:06.2f}s · {msg}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            async def work():
                import zlib,binascii
                emit("1/6 · Cargando candidato V0.62…")
                path=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v062","single-face-proof-v062.bin")
                if not os.path.exists(path):
                    raise RuntimeError("Falta single-face-proof-v062.bin")
                with open(path,"rb") as fh:
                    raw=fh.read()
                if len(raw)<54 or raw[:2]!=b"WF":
                    raise RuntimeError("Archivo WF inválido")

                packed=zlib.compress(raw,9)
                emit("2/6 · Segmentando flujo comprimido…")
                blocks=[packed[i:i+300] for i in range(0,len(packed),300)]
                frame_counts=[1 if len(b)<=10 else 1+((len(b)-10+18)//19) for b in blocks]

                emit("3/6 · Verificando reconstrucción exacta…")
                joined=b"".join(blocks)
                ok_stream=joined==packed
                ok_source=zlib.decompress(joined)==raw

                emit("4/6 · Calculando checksums y último bloque…")
                rep["offline_transfer_plan"]["candidate"]={
                    "path":path,
                    "raw_size":len(raw),
                    "raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "compressed_size":len(packed),
                    "compressed_sha256":hashlib.sha256(packed).hexdigest(),
                    "block_size":300,
                    "block_count":len(blocks),
                    "last_block_size":len(blocks[-1]),
                    "total_frames":sum(frame_counts),
                    "first_sequence_id":4,
                    "last_sequence_id":(3+len(blocks))&255,
                    "stream_exact":ok_stream,
                    "decompress_matches_source":ok_source,
                    "raw_crc32":f"0x{binascii.crc32(raw)&0xffffffff:08X}",
                    "compressed_crc32":f"0x{binascii.crc32(packed)&0xffffffff:08X}"
                }
                rep["offline_transfer_plan"]["last_block"]={
                    "offset":(len(blocks)-1)*300,
                    "length":len(blocks[-1]),
                    "sha256":hashlib.sha256(blocks[-1]).hexdigest(),
                    "hex":blocks[-1].hex()
                }

                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","wf-analysis-v075")
                os.makedirs(folder,exist_ok=True)
                report_path=os.path.join(folder,"offline-transfer-plan-v075.json")
                rep["offline_transfer_plan"]["report_file"]=report_path
                rep["offline_transfer_plan"]["phase"]="complete"
                with open(report_path,"w",encoding="utf-8") as fh:
                    json.dump(rep["offline_transfer_plan"],fh,ensure_ascii=False,indent=2)

                emit("5/6 · PLAN · bloques="+str(len(blocks))+" · último="+str(len(blocks[-1]))+" B · frames="+str(sum(frame_counts)))
                emit("6/6 · V0.75 FINALIZADA · análisis offline completo.")
                return rep

            def done(result,error):
                if error:
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["offline_transfer_plan"]["phase"]="error"
                    self.report=rep
                    self.show()
                    append("V0.75 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V0.75 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result
                self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                self.status.set("V0.75 finalizada. Ahora COPIAR DIAGNÓSTICO y mandármelo.")
            self.run_async(asyncio.wait_for(work(),timeout=60),done)
'''

s = s[:start] + new_block + s[end:]

s = s.replace(
    'V0.74 LISTA · 1º PREPARAR ESFERA ÚNICA V0.74; 2º COPIAR DIAGNÓSTICO. Prueba cinco bloques 0x83 consecutivos de 300 bytes: 6000 bytes totales, ACK individual y corte seguro.',
    'V0.75 LISTA · 1º ANALIZAR TRANSFERENCIA V0.75; 2º COPIAR DIAGNÓSTICO. Calcula el plan completo offline; no usa Bluetooth.',
    1
)

p.write_text(s, encoding="utf-8")
print("overlay V0.75 aplicado")
