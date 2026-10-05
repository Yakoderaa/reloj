import io, json, os, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v167 as v167
import app_v166 as v166
import app_v145 as v145

base.APP_VERSION='1.68.0'

TARGET_CLASSES=(
    'Lcom/wtwd/cocousa/ble/ZKBleOtaManager;',
    'Lcom/wtwd/cocousa/ble/BleConnectService;',
    'Lcom/bluetrum/fota/bluetooth/h;',
)
ANCHORS=(
    'PREF_KEY_ZK_OTA','中科OTA','OTA写通道','0000b003-0000-1000-8000-00805f9b34fb',
    '0000e91a-0000-1000-8000-00805f9b34fb','f000ffc0-0451-4000-b000-000000000000',
    'f000ffc1-0451-4000-b000-000000000000','f000ffc2-0451-4000-b000-000000000000'
)

class AppV168(v167.AppV167):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.68')
        self._clean_v168(); self._install_v168()
        self.status.set('V1.68 lista · corrige el parser DEX y vuelve a trazar ZKBleOtaManager/BleConnectService sin falsos method_idx. Actualizador restaurado por release+manifest.')

    def _clean_v168(self):
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

    def _install_v168(self):
        top=self.root.winfo_children()[0]
        self.v168_button=ttk.Button(top,text='RECONSTRUIR OTA EXACTO',command=self.trace_exact_ota)
        sib=top.winfo_children()
        try:self.v168_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v168_button.place(x=8,y=8)

    @staticmethod
    def _dex_model(b):
        # DEX fix: method_idx_diff restarts separately for direct_methods and virtual_methods.
        if len(b)<112 or not b.startswith(b'dex\n'): raise ValueError('DEX inválido')
        ssz,soff=v166.u32(b,56),v166.u32(b,60); tsz,toff=v166.u32(b,64),v166.u32(b,68)
        msz,moff=v166.u32(b,88),v166.u32(b,92); csz,coff=v166.u32(b,96),v166.u32(b,100)
        strings=[]
        for i in range(ssz):
            p=v166.u32(b,soff+i*4); _,p=v166.uleb(b,p); q=b.find(b'\0',p,min(len(b),p+20000)); q=len(b) if q<0 else q
            strings.append(b[p:q].decode('utf-8','replace'))
        types=[strings[v166.u32(b,toff+i*4)] for i in range(tsz)]
        methods=[]
        for i in range(msz):
            ci=v166.u16(b,moff+i*8); ni=v166.u32(b,moff+i*8+4)
            methods.append({'idx':i,'class':types[ci] if ci<len(types) else str(ci),'name':strings[ni] if ni<len(strings) else str(ni)})
        classes=[]; encoded=[]
        for i in range(csz):
            o=coff+i*32; ci=v166.u32(b,o); cdo=v166.u32(b,o+24); desc=types[ci] if ci<len(types) else str(ci); classes.append(desc)
            if not cdo: continue
            try:
                p=cdo; sf,p=v166.uleb(b,p); inf,p=v166.uleb(b,p); dm,p=v166.uleb(b,p); vm,p=v166.uleb(b,p)
                # encoded_fields: each list has its own diff base; only advance safely.
                for count in (sf,inf):
                    fid=-1
                    for _ in range(count):
                        d,p=v166.uleb(b,p); fid+=d; _,p=v166.uleb(b,p)
                # direct methods and virtual methods each restart method_idx_diff at zero.
                for count,kind in ((dm,'direct'),(vm,'virtual')):
                    mid=-1
                    for _ in range(count):
                        d,p=v166.uleb(b,p); mid+=d; acc,p=v166.uleb(b,p); code,p=v166.uleb(b,p)
                        if 0<=mid<len(methods): encoded.append((desc,mid,code,kind,acc))
            except Exception: pass
        return strings,types,methods,classes,encoded

    def trace_exact_ota(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.68 · falta validación BK3288.'); return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.68 · reparando mapeo DEX y reconstruyendo flujo OTA exacto…')

        def work():
            rep={'app_version':'1.68.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'correct_dex_method_mapping_and_reconstruct_exact_zk_ota_flow',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'parser_fix':'method_idx_diff resets independently for direct_methods and virtual_methods',
                 'dex':[],'target_methods':[],'anchor_methods':[],'callers_into_targets':[],'uuid_strings':[],
                 'protocol_strings':[],'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}

            def inspect(label,b):
                try: strings,types,methods,classes,enc=self._dex_model(b)
                except Exception as ex: rep['dex'].append({'name':label,'error':repr(ex)}); return
                code_by_mid={mid:code for _,mid,code,_,_ in enc}
                kind_by_mid={mid:kind for _,mid,_,kind,_ in enc}
                rep['dex'].append({'name':label,'classes':len(classes),'methods':len(methods),'encoded_methods':len(enc)})
                target_ids={m['idx'] for m in methods if m['class'] in TARGET_CLASSES}

                for desc,mid,code,kind,acc in enc:
                    me=methods[mid]; ss,mm=self._refs_in_code(b,code,strings,methods)
                    sshort=[x for x in ss if len(x)<2400][:300]
                    calls=[{'idx':x['idx'],'class':x['class'],'method':x['name']} for x in mm[:300]]
                    if mid in target_ids:
                        rep['target_methods'].append({'dex':label,'class':me['class'],'method':me['name'],'method_idx':mid,'kind':kind,'access_flags':acc,'code_off':code,'strings':sshort,'calls':calls})
                    hits_anchor=[a for a in ANCHORS if any(a.lower() in s.lower() for s in sshort)]
                    if hits_anchor:
                        rep['anchor_methods'].append({'dex':label,'class':me['class'],'method':me['name'],'method_idx':mid,'kind':kind,'code_off':code,'anchors':hits_anchor,'strings':sshort,'calls':calls})
                    hits_target=[x for x in mm if x['idx'] in target_ids]
                    if mid not in target_ids and hits_target:
                        rep['callers_into_targets'].append({'dex':label,'caller_class':me['class'],'caller_method':me['name'],'caller_idx':mid,'kind':kind,'code_off':code,'strings':sshort,'calls_target':[{'idx':x['idx'],'class':x['class'],'method':x['name']} for x in hits_target]})
                    for s in sshort:
                        sl=s.lower()
                        if ('0000' in sl or 'f000ffc' in sl or 'uuid' in sl) and s not in rep['uuid_strings']: rep['uuid_strings'].append(s)
                        if any(k in sl for k in ('ota','fota','firmware','upgrade','write','notify','packet','crc','offset','progress','mtu','zk_ota')) and s not in rep['protocol_strings']: rep['protocol_strings'].append(s)

            def inspect_apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(name+'!'+n,z.read(n))
                except Exception:pass

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
            for k,limit in [('target_methods',2500),('anchor_methods',2500),('callers_into_targets',3500),('uuid_strings',1200),('protocol_strings',1800)]: rep[k]=rep[k][:limit]
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v168'); os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-exact-zk-ota-v168.json'); rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f: json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep

        def done(rep,err):
            if err:self.status.set('V1.68 · falló: '+repr(err));return
            self.report={'exact_zk_ota_v168':rep}; self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2); self.root.clipboard_clear(); self.root.clipboard_append(t); self.root.update_idletasks()
            except Exception:pass
            self.status.set(f"V1.68 LISTO · targets={len(rep['target_methods'])} · anchors={len(rep['anchor_methods'])} · callers={len(rep['callers_into_targets'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk(); AppV168(root); root.mainloop()
