import io, json, os, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v169 as v169
import app_v166 as v166
import app_v145 as v145

base.APP_VERSION='1.70.0'

BASE_API='Lcom/wtwd/cocousa/api/BaseApi;'
UPDATE_PREFIX='Lcom/wtwd/cocousa/ui/module/main/device/update/'
FOCUS_NAMES=('i','y')

class AppV170(v169.AppV169):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.70')
        self._clean_v170(); self._install_v170()
        self.status.set('V1.70 lista · extrae anotaciones Retrofit exactas del API de firmware y enlaza check/download con el flujo ZK OTA. Sin red ni escrituras.')

    def _clean_v170(self):
        keep=('buscar relojes','buscar dispositivos','buscar disp','buscar actualización','buscar actualizacion','buscar actualizaciones')
        def walk(w):
            for c in list(w.winfo_children()):
                try:
                    if isinstance(c,(ttk.Button,tk.Button)):
                        t=str(c.cget('text') or '').lower()
                        if not any(x in t for x in keep):
                            try:c.pack_forget()
                            except Exception:pass
                            try:c.grid_remove()
                            except Exception:pass
                            try:c.place_forget()
                            except Exception:pass
                    else: walk(c)
                except Exception: pass
        walk(self.root)

    def _install_v170(self):
        top=self.root.winfo_children()[0]
        self.v170_button=ttk.Button(top,text='EXTRAER API FIRMWARE EXACTA',command=self.extract_api)
        sib=top.winfo_children()
        try:self.v170_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v170_button.place(x=8,y=8)

    @staticmethod
    def _sval(b,p,n,signed=False):
        if p+n>len(b): raise ValueError('valor fuera de DEX')
        v=int.from_bytes(b[p:p+n],'little',signed=False)
        if signed and n and (b[p+n-1]&0x80): v-=1<<(n*8)
        return v,p+n

    @classmethod
    def _encoded_value(cls,b,p,strings,types,depth=0):
        if depth>10 or p>=len(b): return {'error':'depth/bounds'},p
        head=b[p]; p+=1; typ=head&0x1f; arg=head>>5; n=arg+1
        try:
            if typ==0x00:
                v,p=cls._sval(b,p,n,True); return {'kind':'byte','value':v},p
            if typ==0x02:
                v,p=cls._sval(b,p,n,True); return {'kind':'short','value':v},p
            if typ==0x03:
                v,p=cls._sval(b,p,n,False); return {'kind':'char','value':v},p
            if typ==0x04:
                v,p=cls._sval(b,p,n,True); return {'kind':'int','value':v},p
            if typ==0x06:
                v,p=cls._sval(b,p,n,True); return {'kind':'long','value':v},p
            if typ in (0x10,0x11):
                raw,p=cls._sval(b,p,n,False); return {'kind':'float_or_double_bits','value':raw,'value_type':hex(typ)},p
            if typ==0x17:
                idx,p=cls._sval(b,p,n,False); return {'kind':'string','idx':idx,'value':strings[idx] if idx<len(strings) else str(idx)},p
            if typ==0x18:
                idx,p=cls._sval(b,p,n,False); return {'kind':'type','idx':idx,'value':types[idx] if idx<len(types) else str(idx)},p
            if typ in (0x19,0x1a,0x1b):
                idx,p=cls._sval(b,p,n,False); return {'kind':{0x19:'field',0x1a:'method',0x1b:'enum'}[typ],'idx':idx},p
            if typ==0x1c:
                sz,p=v166.uleb(b,p); arr=[]
                for _ in range(min(sz,500)):
                    x,p=cls._encoded_value(b,p,strings,types,depth+1); arr.append(x)
                return {'kind':'array','values':arr,'size':sz},p
            if typ==0x1d:
                x,p=cls._encoded_annotation(b,p,strings,types,depth+1); return {'kind':'annotation','value':x},p
            if typ==0x1e: return {'kind':'null','value':None},p
            if typ==0x1f: return {'kind':'boolean','value':bool(arg)},p
            v,p=cls._sval(b,p,n,False); return {'kind':'unknown','type':hex(typ),'value':v},p
        except Exception as ex:
            return {'error':repr(ex),'type':hex(typ)},p

    @classmethod
    def _encoded_annotation(cls,b,p,strings,types,depth=0):
        ti,p=v166.uleb(b,p); sz,p=v166.uleb(b,p); els=[]
        for _ in range(min(sz,500)):
            ni,p=v166.uleb(b,p); val,p=cls._encoded_value(b,p,strings,types,depth+1)
            els.append({'name_idx':ni,'name':strings[ni] if ni<len(strings) else str(ni),'value':val})
        return {'type_idx':ti,'type':types[ti] if ti<len(types) else str(ti),'elements':els,'size':sz},p

    @classmethod
    def _annotation_set(cls,b,off,strings,types):
        out=[]
        if not off or off+4>len(b): return out
        try:
            sz=v166.u32(b,off)
            for i in range(min(sz,200)):
                ao=v166.u32(b,off+4+i*4)
                if not ao or ao>=len(b): continue
                vis=b[ao]; ann,_=cls._encoded_annotation(b,ao+1,strings,types)
                ann['visibility']=vis; out.append(ann)
        except Exception as ex: out.append({'error':repr(ex),'offset':off})
        return out

    @classmethod
    def _method_annotations(cls,b,strings,types,classes,methods):
        result={}
        csz,coff=v166.u32(b,96),v166.u32(b,100)
        for i in range(csz):
            o=coff+i*32
            try: anno_dir=v166.u32(b,o+20)
            except Exception: continue
            if not anno_dir or anno_dir+16>len(b): continue
            try:
                _,fs,ms,ps=(v166.u32(b,anno_dir+j*4) for j in range(4))
                p=anno_dir+16+fs*8
                for _ in range(ms):
                    mid=v166.u32(b,p); aset=v166.u32(b,p+4); p+=8
                    if mid<len(methods): result[mid]=cls._annotation_set(b,aset,strings,types)
            except Exception: continue
        return result

    def extract_api(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.70 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.70 · leyendo anotaciones Retrofit y contrato de descarga…')
        def work():
            rep={'app_version':'1.70.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'extract_exact_firmware_check_and_download_api_annotations_without_network_or_ota_writes',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'base_api_methods':[],'hardware_update_methods':[],'hardware_version_fields':[],
                 'retrofit_annotations':[],'endpoint_strings':[],'contract_summary':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            def inspect(label,b):
                try: strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex: rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                anns=self._method_annotations(b,strings,types,classes,methods)
                encmap={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for f in fields:
                    if f['class']=='Lcom/wtwd/cocousa/entity/device/HardwareVersion;': rep['hardware_version_fields'].append(f)
                for m in methods:
                    cl=m['class']; mid=m['idx']
                    if cl==BASE_API or cl.startswith(UPDATE_PREFIX):
                        code,kind,acc=encmap.get(mid,(0,None,None)); d=self._details(b,code,strings,methods,fields)
                        row={'dex':label,'class':cl,'method':m['name'],'method_idx':mid,'proto':m.get('proto'),'kind':kind,'access_flags':acc,'code_off':code,
                             'annotations':anns.get(mid,[]),**d}
                        if cl==BASE_API: rep['base_api_methods'].append(row)
                        else: rep['hardware_update_methods'].append(row)
                        for a in anns.get(mid,[]):
                            at=str(a.get('type',''))
                            if any(k in at.lower() for k in ('retrofit','http','streaming','headers')):
                                rep['retrofit_annotations'].append({'dex':label,'class':cl,'method':m['name'],'method_idx':mid,'annotation':a,'proto':m.get('proto')})
                            for e in a.get('elements',[]):
                                val=e.get('value',{})
                                vals=[]
                                if val.get('kind')=='string': vals=[val.get('value')]
                                elif val.get('kind')=='array': vals=[x.get('value') for x in val.get('values',[]) if x.get('kind')=='string']
                                for s in vals:
                                    if isinstance(s,str) and (s.startswith('/') or 'http' in s.lower() or 'firm' in s.lower() or 'upgrade' in s.lower() or 'ota' in s.lower()):
                                        rep['endpoint_strings'].append({'class':cl,'method':m['name'],'annotation_type':at,'name':e.get('name'),'value':s})
            def inspect_apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(name+'!'+n,z.read(n))
                except Exception as ex: rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        for n in apks:
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower(): inspect_apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f: inspect_apk(os.path.basename(chosen),f.read())
            # focused summary: the exact methods already proven by V1.69 callers
            for r in rep['base_api_methods']:
                if r['method'] in FOCUS_NAMES:
                    rep['contract_summary'].append({'class':r['class'],'method':r['method'],'proto':r.get('proto'),'annotations':r.get('annotations',[]),'strings':r.get('strings',[]),'calls':r.get('calls',[])})
            # evidence from presenter/model that links response body -> file and check request fields
            for r in rep['hardware_update_methods']:
                ss=set(r.get('strings',[])); calls=r.get('calls',[])
                if {'currentFirmware','language','macAddress','watchId'} & ss or any(c.get('class')=='Lokhttp3/ResponseBody;' and c.get('method')=='byteStream' for c in calls):
                    rep['contract_summary'].append({'class':r['class'],'method':r['method'],'proto':r.get('proto'),'strings':r.get('strings',[]),'calls':calls,'fields':r.get('fields',[]),'consts':r.get('consts',[])})
            # de-dup endpoint strings
            seen=set(); eps=[]
            for x in rep['endpoint_strings']:
                k=(x['class'],x['method'],x['annotation_type'],x['name'],x['value'])
                if k not in seen: seen.add(k);eps.append(x)
            rep['endpoint_strings']=eps[:500]
            for k,lim in [('base_api_methods',600),('hardware_update_methods',1800),('hardware_version_fields',500),('retrofit_annotations',1000),('contract_summary',300)]: rep[k]=rep[k][:lim]
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v170');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-firmware-api-v170.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.70 · falló: '+repr(err));return
            self.report={'firmware_api_v170':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except Exception:pass
            self.status.set(f"V1.70 LISTO · endpoints={len(rep['endpoint_strings'])} · retrofit={len(rep['retrofit_annotations'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV170(root);root.mainloop()
