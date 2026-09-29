import json, urllib.request, pathlib, hashlib
base='https://wr.watchhealth.com.cn/app-halfwit/app-dial/getDialList'
rows=[]
for page in range(1,26):
    url=f'{base}?currentPage={page}&pageSize=20&watchId=102'
    req=urllib.request.Request(url,headers={'User-Agent':'RelojLab/1.20-research','Accept':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            obj=json.loads(r.read().decode('utf-8','replace'))
    except Exception as e:
        print('PAGE_FAIL',page,repr(e)); continue
    data=obj.get('data') if isinstance(obj,dict) else None
    if not data: break
    rows.extend(x for x in data if isinstance(x,dict))
print('ROWS',len(rows))
root=pathlib.Path('evidence'); (root/'previews').mkdir(parents=True,exist_ok=True); (root/'bins').mkdir(exist_ok=True)
(root/'catalog.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
def get(url,dest):
    req=urllib.request.Request(url,headers={'User-Agent':'RelojLab/1.20-research','Accept':'*/*'})
    with urllib.request.urlopen(req,timeout=30) as r:data=r.read(5*1024*1024)
    pathlib.Path(dest).write_bytes(data); return data
def u16(b,o):return int.from_bytes(b[o:o+2],'little')
out=[]
for i,e in enumerate(rows):
    did=str(e.get('dialId') or '')
    file=e.get('dialFile')
    preview=e.get('previewImg') or e.get('preview') or e.get('dialPreview') or e.get('previewUrl') or e.get('imgUrl')
    rec={'i':i,'dialId':did,'file':file,'preview':preview}
    if isinstance(preview,str) and preview.startswith('http'):
        try:get(preview,root/'previews'/f'{did}.png')
        except Exception as ex:rec['preview_error']=repr(ex)
    if isinstance(file,str) and file.startswith('http'):
        try:
            b=get(file,root/'bins'/f'{did}.bin');rec['size']=len(b);rec['sha256']=hashlib.sha256(b).hexdigest()
            if len(b)>=54 and b[:2]==b'WF':
                n=u16(b,0x2e);rec.update(wf=True,version=u16(b,2),width=u16(b,0x2a),height=u16(b,0x2c))
                desc=[]
                for j in range(n):
                    off=54+j*20
                    if off+20>len(b):break
                    raw=b[off:off+20]
                    desc.append({'i':j,'type':f'0x{u16(raw,2):04X}','frames':u16(raw,4),'x':u16(raw,6),'y':u16(raw,8),'ptr':u16(raw,18)})
                rec['descriptors']=desc;rec['types']=[d['type'] for d in desc]
        except Exception as ex:rec['file_error']=repr(ex)
    out.append(rec)
(root/'index.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
freq={}
for r in out:
    for t in set(r.get('types') or []):freq[t]=freq.get(t,0)+1
(root/'type_frequency.json').write_text(json.dumps(sorted(freq.items(),key=lambda x:(-x[1],x[0])),indent=2),encoding='utf-8')
for r in out:
    ts=set(r.get('types') or [])
    if {'0x0501','0x0601','0x0701'}.issubset(ts):
        print('ANALOG',r['dialId'],r.get('size'),','.join(r.get('types') or []))
