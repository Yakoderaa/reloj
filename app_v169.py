import io, json, os, struct, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v168 as v168
import app_v166 as v166
import app_v145 as v145

base.APP_VERSION='1.69.0'

FOCUS_PREFIXES=(
    'Lcom/wtwd/cocousa/ui/module/main/device/update/HardwareUpdate',
    'Lcom/wtwd/cocousa/entity/device/HardwareVersion;',
    'Lcom/wtwd/cocousa/ble/ZKBleOtaManager;',
    'Lcom/wtwd/cocousa/ble/BleConnectService;',
    'Lcom/bluetrum/fota/bluetooth/h;',
)
KEYWORDS=('PREF_KEY_ZK_OTA','ota/','.fot','.img','writeZKData','0000b003-0000-1000-8000-00805f9b34fb','中科OTA','升级固件','固件版本','getOtaInfoVersion','startAddress','blockSize','packetSize','allowedUpdate')

class AppV169(v168.AppV168):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.69')
        self._clean_v169(); self._install_v169()
        self.status.set('V1.69 lista · extrae contrato OTA: descarga .fot/.img, HardwareVersion, ZKBleOtaManager, campos, constantes y métodos de escritura.')

    def _clean_v169(self):
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

    def _install_v169(self):
        top=self.root.winfo_children()[0]
        self.v169_button=ttk.Button(top,text='EXTRAER CONTRATO OTA FINAL',command=self.extract_contract)
        sib=top.winfo_children()
        try:self.v169_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v169_button.place(x=8,y=8)

    @staticmethod
    def _dex_full(b):
        strings,types,methods,classes,enc=v168.AppV168._dex_model(b)
        psz,poff=v166.u32(b,72),v166.u32(b,76)
        fsz,foff=v166.u32(b,80),v166.u32(b,84)
        protos=[]
        for i in range(psz):
            o=poff+i*12; shorty=v166.u32(b,o); ret=v166.u32(b,o+4); params=v166.u32(b,o+8)
            args=[]
            if params and params+4<=len(b):
                try:
                    n=v166.u32(b,params)
                    for j in range(n):
                        ti=v166.u16(b,params+4+j*2); args.append(types[ti] if ti<len(types) else str(ti))
                except Exception: pass
            protos.append({'shorty':strings[shorty] if shorty<len(strings) else str(shorty),'return':types[ret] if ret<len(types) else str(ret),'args':args})
        # attach proto index from method_ids
        for i,m in enumerate(methods):
            try:
                pi=v166.u16(b,v166.u32(b,92)+i*8+2); m['proto_idx']=pi; m['proto']=protos[pi] if pi<len(protos) else None
            except Exception:m['proto_idx']=None;m['proto']=None
        fields=[]
        for i in range(fsz):
            o=foff+i*8; ci=v166.u16(b,o); ti=v166.u16(b,o+2); ni=v166.u32(b,o+4)
            fields.append({'idx':i,'class':types[ci] if ci<len(types) else str(ci),'type':types[ti] if ti<len(types) else str(ti),'name':strings[ni] if ni<len(strings) else str(ni)})
        return strings,types,methods,classes,enc,fields

    @staticmethod
    def _details(b,code_off,strings,methods,fields):
        out={'strings':[],'calls':[],'fields':[],'consts':[],'raw_code_hex':''}
        if not code_off or code_off+16>len(b):return out
        try:
            n=v166.u32(b,code_off+12); p=code_off+16; maxu=min(n,(len(b)-p)//2); units=[v166.u16(b,p+i*2) for i in range(maxu)]
            raw=b[p:p+min(maxu*2,1024)]; out['raw_code_hex']=raw.hex()
        except Exception:return out
        ss,mm=v166.AppV166._refs_in_code(b,code_off,strings,methods)
        out['strings']=[x for x in ss if len(x)<3000][:400]
        out['calls']=[{'idx':x['idx'],'class':x['class'],'method':x['name'],'proto':x.get('proto')} for x in mm[:400]]
        fseen=set(); cseen=set()
        for i,w in enumerate(units):
            op=w&0xff
            # field instructions iget/iput/sget/sput families use field@BBBB in next code unit
            if op in tuple(range(0x52,0x6e)) and i+1<len(units):
                fi=units[i+1]
                if fi<len(fields) and fi not in fseen:
                    fseen.add(fi); out['fields'].append(fields[fi])
            # common const opcodes
            try:
                if op==0x12: # const/4 signed nibble
                    v=(w>>12)&0xf; v=v-16 if v&8 else v
                    key=(i,v)
                elif op==0x13 and i+1<len(units):
                    v=units[i+1]; v=v-65536 if v&0x8000 else v; key=(i,v)
                elif op==0x14 and i+2<len(units):
                    v=units[i+1]|(units[i+2]<<16); v=v-0x100000000 if v&0x80000000 else v; key=(i,v)
                elif op==0x15 and i+1<len(units):
                    v=units[i+1]<<16; v=v-0x100000000 if v&0x80000000 else v; key=(i,v)
                else: continue
                if key not in cseen:cseen.add(key);out['consts'].append({'unit':i,'value':v,'hex':hex(v & 0xffffffff)})
            except Exception:pass
        out['consts']=out['consts'][:300]
        return out

    def extract_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.69 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.69 · extrayendo contrato OTA de firmware…')
        def work():
            rep={'app_version':'1.69.0','generated_utc':datetime.now(timezone.utc).isoformat(),'goal':'extract_exact_hardware_update_download_file_and_zk_fota_start_contract','validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,'focus_methods':[],'keyword_methods':[],'hardware_version_fields':[],'ota_write_methods':[],'summary_evidence':[],'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                for f in fields:
                    if f['class']=='Lcom/wtwd/cocousa/entity/device/HardwareVersion;': rep['hardware_version_fields'].append(f)
                for desc,mid,code,kind,acc in enc:
                    m=methods[mid]; focus=any(m['class'].startswith(x) for x in FOCUS_PREFIXES)
                    if not focus and not code:continue
                    d=self._details(b,code,strings,methods,fields)
                    hits=[k for k in KEYWORDS if any(k.lower() in s.lower() for s in d['strings'])]
                    if not focus and not hits:continue
                    row={'dex':label,'class':m['class'],'method':m['name'],'method_idx':mid,'proto':m.get('proto'),'kind':kind,'access_flags':acc,'code_off':code,**d}
                    if focus:rep['focus_methods'].append(row)
                    if hits:
                        row2=dict(row);row2['keyword_hits']=hits;rep['keyword_methods'].append(row2)
                    if m['class']=='Lcom/wtwd/cocousa/ble/BleConnectService;' and (m['name'] in ('a','a0') or any('writezkdata' in s.lower() for s in d['strings'])):
                        rep['ota_write_methods'].append(row)
            def inspect_apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        for n in apks:
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower():inspect_apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:inspect_apk(os.path.basename(chosen),f.read())
            # compact evidence for next version
            for r in rep['keyword_methods']:
                if any(k in r.get('keyword_hits',[]) for k in ('ota/','.fot','.img','writeZKData','0000b003-0000-1000-8000-00805f9b34fb','startAddress','blockSize','packetSize','allowedUpdate')):
                    rep['summary_evidence'].append({'class':r['class'],'method':r['method'],'proto':r.get('proto'),'hits':r.get('keyword_hits'),'strings':r.get('strings',[])[:80],'fields':r.get('fields',[])[:80],'consts':r.get('consts',[])[:80],'calls':r.get('calls',[])[:120]})
            for k,lim in [('focus_methods',3500),('keyword_methods',1500),('hardware_version_fields',500),('ota_write_methods',100),('summary_evidence',500)]:rep[k]=rep[k][:lim]
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v169');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-ota-contract-v169.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.69 · falló: '+repr(err));return
            self.report={'ota_contract_v169':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except Exception:pass
            self.status.set(f"V1.69 LISTO · foco={len(rep['focus_methods'])} · evidencias={len(rep['summary_evidence'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV169(root);root.mainloop()
